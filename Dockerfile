FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && \
    uv sync --no-dev --frozen

COPY main.py handlers.py ./

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "main.py"]
