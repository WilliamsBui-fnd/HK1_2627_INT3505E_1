import os
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

import yaml
from flask import Flask, jsonify, render_template, request
from jsonschema import Draft4Validator, FormatChecker
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
with Path(__file__).with_name('openapi.yaml').open(encoding='utf-8') as file:
    spec = yaml.safe_load(file)

# shortcut: dữ liệu chỉ ở một process; dùng database khi cần lưu lâu dài hoặc nhiều worker.
tasks = {}
lock = Lock()
TOKEN = os.environ.get('TASKS_API_TOKEN', 'demo-token')


def problem(status, detail):
    response = jsonify(type='about:blank', title={400: 'Bad Request', 401: 'Unauthorized',
                       404: 'Not Found', 422: 'Unprocessable Entity'}.get(status, 'HTTP Error'),
                       status=status, detail=detail)
    response.status_code = status
    response.content_type = 'application/problem+json'
    if status == 401:
        response.headers['WWW-Authenticate'] = 'Bearer'
    return response


@app.errorhandler(HTTPException)
def http_error(error):
    return problem(error.code, error.description)


@app.before_request
def authorize():
    if request.path == '/tasks' or request.path.startswith('/tasks/'):
        if request.headers.get('Authorization') != f'Bearer {TOKEN}':
            return problem(401, 'Thiếu hoặc sai Bearer token.')


def read_input(schema_name):
    if request.mimetype != 'application/json':
        return None, problem(400, 'Cần Content-Type: application/json.')
    data = request.get_json(silent=True)
    schema = {'$ref': f'#/components/schemas/{schema_name}', 'components': spec['components']}
    error = next(Draft4Validator(schema, format_checker=FormatChecker()).iter_errors(data), None)
    if error:
        return None, problem(422 if data is not None else 400, error.message)
    return data, None


@app.get('/openapi.json')
def openapi():
    return jsonify(spec)


@app.get('/docs')
def docs():
    return render_template('docs.html')


@app.route('/tasks', methods=['GET', 'POST'])
def collection():
    if request.method == 'GET':
        status = request.args.get('status')
        try:
            limit = int(request.args.get('limit', '10'))
        except ValueError:
            return problem(400, 'limit phải là số nguyên từ 1 đến 100.')
        if not 1 <= limit <= 100 or status not in (None, 'open', 'done'):
            return problem(400, 'limit từ 1 đến 100; status là open hoặc done.')
        with lock:
            matches = [task.copy() for task in tasks.values() if status is None or task['status'] == status]
        return jsonify(items=matches[:limit], total=len(matches))
    data, error = read_input('CreateTaskInput')
    if error is not None:
        return error
    task = {'id': str(uuid4()), 'status': 'open', 'priority': 'normal', **data}
    with lock:
        tasks[task['id']] = task
    return jsonify(task), 201, {'Location': '/tasks/' + task['id']}


@app.route('/tasks/<taskId>', methods=['GET', 'PATCH', 'DELETE'])
def item(taskId):
    try:
        taskId = str(UUID(taskId))
    except ValueError:
        return problem(400, 'taskId phải là UUID.')
    if request.method == 'PATCH':
        data, error = read_input('UpdateTaskInput')
        if error is not None:
            return error
    with lock:
        if taskId not in tasks:
            return problem(404, 'Không tìm thấy task.')
        if request.method == 'DELETE':
            del tasks[taskId]
            return '', 204
        if request.method == 'PATCH':
            tasks[taskId].update(data)
        result = tasks[taskId].copy()
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
