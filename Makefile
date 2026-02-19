PYTHONPATH ?= .
UV_CACHE_DIR ?= .uv-cache

.PHONY: test lint typecheck coverage build format

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=$(PYTHONPATH) uv run pytest -q

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=$(PYTHONPATH) uv run ruff check .

typecheck:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=$(PYTHONPATH) uv run mypy kookie

coverage:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=$(PYTHONPATH) uv run pytest -q --cov=kookie --cov-report=term-missing

build:
	scripts/build_app.sh

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=$(PYTHONPATH) uv run ruff format .
