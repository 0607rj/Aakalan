# Thin wrappers around scripts/tasks.py (which also works on Windows without make).
PY ?= python
TASKS = $(PY) scripts/tasks.py

.PHONY: install dev migrate migration seed test test-backend test-frontend lint format openapi golden worker

install:       ; $(TASKS) install
dev:           ; $(TASKS) dev
migrate:       ; $(TASKS) migrate
migration:     ; $(TASKS) migration -m "$(m)"
seed:          ; $(TASKS) seed
test:          ; $(TASKS) test
test-backend:  ; $(TASKS) test-backend
test-frontend: ; $(TASKS) test-frontend
lint:          ; $(TASKS) lint
format:        ; $(TASKS) format
openapi:       ; $(TASKS) openapi
golden:        ; $(TASKS) golden
worker:        ; $(TASKS) worker
