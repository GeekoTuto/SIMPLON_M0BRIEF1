DC := docker compose

.PHONY: up down logs test migrate register-models

up:
	$(DC) up -d --build

down:
	$(DC) down

logs:
	$(DC) logs -f --tail=200

test:
	$(DC) run --rm api pytest -v

migrate:
	$(DC) run --rm api alembic upgrade head

register-models:
	$(DC) run --rm api python scripts/register_models.py
