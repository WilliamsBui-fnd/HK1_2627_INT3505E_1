FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir /app/instance && chown app:app /app/instance
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app product_api ./product_api
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app wsgi.py ./wsgi.py
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 FLASK_APP=wsgi:app
USER app
EXPOSE 5000
CMD ["sh", "-c", "flask db upgrade && exec gunicorn --bind 0.0.0.0:5000 --workers 1 wsgi:app"]
