.PHONY: install install-dev lint format test clean docker-build docker-run

install:
	pip install -r ingestion/requirements.txt
	pip install -r ml/requirements.txt
	pip install -r flask_app/requirements.txt

install-dev: install
	pip install -e ".[dev]"

lint:
	flake8 ingestion/ ml/ dataflow/ streaming/ flask_app/ --max-line-length=100
	black --check --line-length 100 ingestion/ ml/ dataflow/ streaming/ flask_app/
	isort --check-only ingestion/ ml/ dataflow/ streaming/ flask_app/

format:
	black --line-length 100 ingestion/ ml/ dataflow/ streaming/ flask_app/
	isort ingestion/ ml/ dataflow/ streaming/ flask_app/

test:
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

docker-build:
	docker build -t stock-intelligence:latest ./flask_app

docker-run:
	docker run -p 8080:8080 \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/creds.json \
		-e BIGQUERY_PROJECT_ID=${BIGQUERY_PROJECT_ID} \
		-e BIGQUERY_DATASET=${BIGQUERY_DATASET} \
		stock-intelligence:latest

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .mypy_cache/ .pytest_cache/
