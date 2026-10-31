FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install -r requirements.txt

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH=/venv/bin:$PATH

WORKDIR /app

COPY --from=builder /venv /venv
COPY src ./src
COPY dashboard ./dashboard
COPY wsgi.py .

RUN mkdir -p /app/data

EXPOSE 8000

CMD python -c "from bi_dashboard import secret_store; secret_store.get_session_secret()" \
    && exec gunicorn wsgi:app \
       --worker-class uvicorn.workers.UvicornWorker \
       --workers 2 \
       --bind 0.0.0.0:8000 \
       --timeout 120
