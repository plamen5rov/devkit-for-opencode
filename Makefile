.PHONY: start format lint test

start:
	./start.sh

format:
	cd web && npx prettier --write src/
	ruff format .
	ruff check --fix .

lint:
	cd web && npx tsc --noEmit
	ruff check .

test:
	.venv/bin/python -m pytest tests/ -q
