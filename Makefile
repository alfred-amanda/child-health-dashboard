SHELL := /bin/bash
PYTHON := /opt/homebrew/bin/python3
PY := ./.venv/bin/python
PIP := ./.venv/bin/pip

.PHONY: install dev check ci backend-test frontend-test seed clean smoke-dev

install: .venv apps/web/node_modules

.venv:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e 'apps/api[dev]'

apps/web/node_modules: apps/web/package.json
	cd apps/web && npm install --include=dev

tseed: seed

seed: install
	$(PY) -m app.seed

dev: install seed
	./scripts/dev.sh

smoke-dev: install seed
	./scripts/smoke_dev.sh

backend-test: install seed
	$(PY) -m pytest apps/api/tests -q

frontend-test: install
	cd apps/web && npm run test -- --run

check: install seed
	$(PY) -m ruff check apps/api
	$(PY) -m mypy apps/api/app apps/api/tests
	cd apps/web && npm run lint
	cd apps/web && npm run typecheck
	cd apps/web && npm run test -- --run
	cd apps/web && npm run test:a11y

ci: check
	$(PY) -m pytest apps/api/tests -q
	cd apps/web && npm run build

clean:
	rm -rf .venv apps/web/node_modules apps/web/dist .pytest_cache apps/api/.pytest_cache apps/api/app.egg-info
