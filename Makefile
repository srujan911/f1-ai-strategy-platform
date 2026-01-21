.PHONY: help install install-dev test test-cov lint format type-check clean run-dashboard docs

help:
	@echo "F1 AI Strategy Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install dev + production dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo "  make lint             Check code style (flake8)"
	@echo "  make format           Auto-format code (black, isort)"
	@echo "  make type-check       Type checking (mypy)"
	@echo "  make quality          Run all quality checks"
	@echo ""
	@echo "Running:"
	@echo "  make run-dashboard    Start Streamlit dashboard"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove cache/build files"
	@echo "  make docs             Generate documentation"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

lint:
	flake8 src/ tests/ app/

format:
	black src/ tests/ app/
	isort src/ tests/ app/

type-check:
	mypy src/

quality: format lint type-check test

run-dashboard:
	streamlit run app/dashboard.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name .coverage -delete
	find . -type d -name *.egg-info -exec rm -rf {} +
	find . -type d -name build -exec rm -rf {} +
	find . -type d -name dist -exec rm -rf {} +

docs:
	@echo "Documentation generation placeholder"
	@echo "To generate Sphinx docs: cd docs && make html"
