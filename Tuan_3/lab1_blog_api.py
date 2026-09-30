from flask import Flask, jsonify, request, make_response

app = Flask(__name__)

POSTS = []
_next_post_id = 1

@app.get("/api/v1/posts")
def list_posts():
    limit = int(request.args.get("limit", 10))
    return jsonify(POSTS[:limit]), 200

@app.post("/api/v1/posts")
def create_post():
    global _next_post_id
    if not request.is_json:
        return jsonify(error="Expected JSON"), 415
        
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    content = body.get("content")
    author_id = body.get("author_id")
    
    if not title or not content or not author_id:
        return jsonify(error="title, content, and author_id are required"), 422
        
    post = {
        "id": _next_post_id,
        "title": title.strip(),
        "content": content.strip(),
        "author_id": author_id
    }
    POSTS.append(post)
    _next_post_id += 1
    
    resp = make_response(jsonify(post), 201)
    resp.headers["Location"] = f"/api/v1/posts/{post['id']}"
    return resp

if __name__ == "__main__":
    app.run(debug=True)
