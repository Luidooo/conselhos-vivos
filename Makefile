.DEFAULT_GOAL := help
.PHONY: help docs setup up down migrate carga siorg fetch test test-go vet-go reset pgadmin-reset psql logs

help: ## lista os comandos
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

# O dia que o make fetch baixa. O comando Go exige -date e não adivinha: quem
# quer "hoje" diz de qual fuso, e aqui é o de Brasília, onde a edição sai.
DATA ?= $(shell TZ=America/Sao_Paulo date +%F)

.env:
	cp .env.example .env
	@echo "→ .env criado a partir do .env.example — preencha as credenciais do INLABS"

setup: .env up migrate carga ## primeira vez: cria o .env (se faltar), sobe tudo, migra e carrega a planilha
	@echo "→ banco em localhost:$$(grep ^POSTGRES_PORT= .env | cut -d= -f2) · pgAdmin em http://localhost:5050"

up: .env ## sobe os serviços e espera o banco ficar healthy
	docker compose up -d --wait

down: ## para os serviços, mantém os dados
	docker compose down

migrate: ## aplica as migrações de sql/ que ainda não rodaram, em ordem
	bash scripts/migrate.sh

carga: ## carrega os conselhos e a planilha da pesquisadora no banco (idempotente) e atualiza os relatórios
	bash scripts/carga.sh

siorg: ## baixa o SIORG (com rede) e atualiza o recorte em data/referencia/; rode make carga depois
	docker compose --progress quiet run --rm -T siorg > data/referencia/siorg-conselhos.csv.novo
	mv data/referencia/siorg-conselhos.csv.novo data/referencia/siorg-conselhos.csv

fetch: .env ## baixa DO1 e DO1E do DOU (DATA=AAAA-MM-DD; sem DATA, hoje em Brasília). Sem retomada: rebaixa o que já existe
	mkdir -p data/bronze/inlabs
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T ingestor -date $(DATA)

test-go: ## testes do ingestor em Go, em container (sem rede no código de teste, sem credencial)
	docker compose --progress quiet run --rm -T ingestor-test go test -count=1 ./...

vet-go: ## gofmt e go vet do ingestor, em container
	docker compose --progress quiet run --rm -T ingestor-test sh -c 'test -z "$$(gofmt -l .)" || { gofmt -l .; echo "FALHOU: arquivos fora do gofmt"; exit 1; }; go vet ./...'

test: .env test-go ## testes: Go do ingestor, infra, esquema do OLTP, leitura da planilha, identidade dos conselhos e carga
	bash tests/infra/test_compose.sh
	bash scripts/migrate.sh
	bash tests/db/test_schema.sh
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/planilha
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/conselhos
	bash tests/db/test_carga.sh

reset: ## APAGA o banco, sobe do zero, migra e carrega a planilha
	docker compose down -v
	docker compose up -d --wait
	bash scripts/migrate.sh
	bash scripts/carga.sh

pgadmin-reset: ## recria o pgAdmin do zero (use se mudar POSTGRES_USER ou POSTGRES_DB)
	docker compose rm -sf pgadmin
	docker volume ls -q --filter label=com.docker.compose.volume=pgadmin \
	  --filter label=com.docker.compose.project=$$(docker compose config | awk '/^name:/{print $$2}') \
	  | xargs docker volume rm
	docker compose up -d --wait pgadmin

docs: ## sobe o site de documentação em http://localhost:5173/conselhos-vivos/ (precisa de Node)
	npm --prefix site ci --no-audit --no-fund
	npm --prefix site run dev -- --port 5173

psql: ## abre o psql dentro do container
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

logs: ## acompanha os logs do banco
	docker compose logs -f db
