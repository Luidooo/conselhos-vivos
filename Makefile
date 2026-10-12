.DEFAULT_GOAL := help
.PHONY: help docs setup up down migrate carga siorg fetch extract persist ingest test test-go test-db-go vet-go reset pgadmin-reset psql logs

help: ## lista os comandos
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

# O dia que o make fetch baixa. O comando Go exige -date e não adivinha: quem
# quer "hoje" diz de qual fuso, e aqui é o de Brasília, onde a edição sai.
DATA ?= $(shell TZ=America/Sao_Paulo date +%F)
# As edições do dia que o make extract e o make persist leem: as que existem, DO1 e DO1E.
EDICOES = $(wildcard data/bronze/inlabs/$(DATA)-DO1.zip data/bronze/inlabs/$(DATA)-DO1E.zip)
# Os marcadores que o fetch deixa no lugar do ZIP, das duas seções: o INLABS disse
# que a edição não houve, ou a busca dela falhou.
SEM_EDICAO = $(wildcard data/bronze/inlabs/$(DATA)-DO1.sem-edicao data/bronze/inlabs/$(DATA)-DO1E.sem-edicao)
FALHOU = $(wildcard data/bronze/inlabs/$(DATA)-DO1.falhou data/bronze/inlabs/$(DATA)-DO1E.falhou)
# Sem ZIP, um dia sem edição não é erro; um que falhou ou que ninguém buscou é. A
# falha de qualquer seção é avisada mesmo com o ZIP da outra (e o alvo sai com
# erro no fim, pelo ZIPS_FALHOU); a falha vence o "sem edição" da outra seção.
TEM_EDICAO = if [ -n "$(FALHOU)" ]; then echo "a busca de $(notdir $(FALHOU:.falhou=)) falhou (marcador em data/bronze/inlabs/) — rode make fetch DATA=$(DATA) de novo" >&2; fi; \
	if [ -n "$(EDICOES)" ]; then :; \
	elif [ -n "$(FALHOU)" ]; then exit 1; \
	elif [ -n "$(SEM_EDICAO)" ]; then echo "$(DATA) não teve edição do DOU (marcador em data/bronze/inlabs/)" >&2; \
	else echo "nenhum ZIP de $(DATA) em data/bronze/inlabs/ — rode make fetch DATA=$(DATA)"; exit 1; fi
# O valor inicial do "falhou" dos laços do extract e do persist: com uma seção
# falha, o alvo processa o ZIP da outra e sai com erro no fim.
ZIPS_FALHOU = $(if $(FALHOU),1,0)

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

fetch: .env ## baixa DO1 e DO1E do DOU (DATA=AAAA-MM-DD; sem DATA, hoje em Brasília). Sem retomada: rebaixa o que já existe; edição que não houve ou que falhou fica marcada
	mkdir -p data/bronze/inlabs
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T ingestor -date $(DATA)

extract: ## lê as matérias dos ZIPs de DATA já baixados e imprime uma por linha, em JSON (HTML=1 inclui o HTML do texto)
	@$(TEM_EDICAO)
	@# Uma execução por edição: o comando lê um ZIP só. A segunda roda mesmo se a
	@# primeira falhar, e o make sai com erro se qualquer uma falhou.
	@falhou=$(ZIPS_FALHOU); for zip in $(EDICOES:data/%=/data/%); do \
		docker compose --progress quiet run --rm -T extract $(if $(HTML),-html) $$zip || falhou=1; \
	done; exit $$falhou

persist: .env ## grava no banco as matérias dos ZIPs de DATA já baixados; pode rodar de novo, não duplica
	@$(TEM_EDICAO)
	@# Como no extract: uma execução por edição, e a segunda roda mesmo se a primeira falhar.
	@falhou=$(ZIPS_FALHOU); for zip in $(EDICOES:data/%=/data/%); do \
		docker compose --progress quiet run --rm -T persist $$zip || falhou=1; \
	done; exit $$falhou

ingest: .env ## baixa as edições de DATA e grava as matérias de conselho no banco, de ponta a ponta; pode rodar de novo, não duplica
	@# O persist vai num make à parte: a lista de ZIPs e de marcadores dele tem de
	@# ser montada depois do fetch. Ele roda mesmo se o fetch falhou numa seção: o
	@# que foi baixado é gravado, e o make sai com erro no fim. Dia sem edição, dia
	@# que falhou e dia não buscado quem decide é o TEM_EDICAO, dentro do persist.
	@falhou=0; $(MAKE) --no-print-directory fetch DATA=$(DATA) || falhou=1; \
	$(MAKE) --no-print-directory persist DATA=$(DATA) || falhou=1; \
	exit $$falhou

test-go: ## testes do ingestor em Go, em container (sem rede no código de teste, sem credencial)
	docker compose --progress quiet run --rm -T ingestor-test go test -count=1 ./...

test-db-go: .env ## testes do ingestor que gravam no banco, em transação desfeita (precisa do banco no ar e migrado)
	docker compose --progress quiet run --rm -T ingestor-db-test go test -count=1 ./internal/oltp/ ./cmd/persist/

vet-go: ## gofmt e go vet do ingestor, em container
	docker compose --progress quiet run --rm -T ingestor-test sh -c 'test -z "$$(gofmt -l .)" || { gofmt -l .; echo "FALHOU: arquivos fora do gofmt"; exit 1; }; go vet ./...'

test: .env test-go ## testes: Go do ingestor, infra, esquema do OLTP, leitura da planilha, identidade dos conselhos, carga e persistência do DOU
	bash tests/infra/test_compose.sh
	bash scripts/migrate.sh
	bash tests/db/test_schema.sh
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/planilha
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/conselhos
	bash tests/db/test_carga.sh
	$(MAKE) --no-print-directory test-db-go

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
