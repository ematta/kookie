FROM python:3.12-slim

WORKDIR /workspace

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY kookie ./kookie
COPY tests ./tests
COPY main.py ./

RUN uv sync --extra dev

CMD ["uv", "run", "pytest", "-q"]
