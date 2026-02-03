FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --no-cache-dir .

CMD ["blog-watcher", "-c", "/app/config.toml", "--db-path", "/data/blog_states.sqlite"]
