.DEFAULT_GOAL := help
.PHONY: help setup up down test reset psql logs

help: ## lista os comandos
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-7s %s\n", $$1, $$2}'

.env:
	cp .env.example .env
	@echo "→ .env criado a partir do .env.example — preencha as credenciais do INLABS"

setup: .env up ## primeira vez: cria o .env (se faltar) e sobe tudo
	@echo "→ banco em localhost:$$(grep ^POSTGRES_PORT= .env | cut -d= -f2) · pgAdmin em http://localhost:5050"

up: .env ## sobe os serviços e espera o banco ficar healthy
	docker compose up -d --wait

down: ## para os serviços, mantém os dados
	docker compose down

test: .env ## teste de fumaça: sobe healthy e persiste entre down/up
	bash tests/infra/test_compose.sh
	bash tests/db/test_schema.sh

reset: ## APAGA o banco e sobe do zero
	docker compose down -v
	docker compose up -d --wait

psql: ## abre o psql dentro do container
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

logs: ## acompanha os logs do banco
	docker compose logs -f db
