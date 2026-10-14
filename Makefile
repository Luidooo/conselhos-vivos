.DEFAULT_GOAL := help
.PHONY: help docs setup up down migrate carga siorg fetch extract persist ingest ingest-dia janela fetch-mensal persist-mensal ingest-mensal test test-go test-py-dou test-db-go test-db-py vet-go reset pgadmin-reset psql logs lake cdc cdc-demo cdc-drop cdc-chaos

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

# O mês que o make fetch-mensal baixa dos dados abertos, AAAA-MM. Sem padrão: o mês
# corrente nunca está publicado, e o anterior só sai por volta do dia 15.
MES ?=
# O ZIP da Seção 1 do MES, com o nome que a Imprensa Nacional dá: 2026-08 é S01082026.zip.
ZIP_MENSAL = data/bronze/dados-abertos/S01$(word 2,$(subst -, ,$(MES)))$(word 1,$(subst -, ,$(MES))).zip
TEM_MES = if [ -z "$(MES)" ]; then echo "diga o mês: MES=AAAA-MM, como MES=2026-08" >&2; exit 2; fi

# Quantos dias o make ingest reprocessa, contando DATA: o DOU chega atrasado
# (edição extra à tarde, edição republicada), e a janela é o que busca de novo.
JANELA ?= 7
# Os dias da janela. A conta de datas roda em Python, num container sem rede,
# porque o date do Linux e o do macOS não fazem aritmética do mesmo jeito.
DIAS = docker --log-level error compose --progress quiet run --rm -T --entrypoint python carga -c \
	'import sys, datetime as d; fim = d.date.fromisoformat(sys.argv[1]); n = int(sys.argv[2]); n >= 1 or sys.exit("JANELA tem de ser 1 ou mais"); print(*[fim - d.timedelta(days=i) for i in range(n - 1, -1, -1)])' \
	$(DATA) $(JANELA)

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
		docker compose --progress quiet run --rm -T dou extract $(if $(HTML),--html) $$zip || falhou=1; \
	done; exit $$falhou

persist: .env ## grava no banco as matérias dos ZIPs de DATA já baixados; pode rodar de novo, não duplica
	@$(TEM_EDICAO)
	@# Como no extract: uma execução por edição, e a segunda roda mesmo se a primeira falhar.
	@falhou=$(ZIPS_FALHOU); for zip in $(EDICOES:data/%=/data/%); do \
		docker compose --progress quiet run --rm -T persist $$zip || falhou=1; \
	done; exit $$falhou

ingest: .env ## baixa e grava no banco os JANELA dias que terminam em DATA (padrão: 7); pode rodar de novo, não duplica
	@# Do dia mais antigo para o mais novo. Um dia que falha não impede os
	@# seguintes, e o make sai com erro se qualquer um falhou.
	@dias=$$($(DIAS)) || exit 1; falhou=0; for dia in $$dias; do \
		$(MAKE) --no-print-directory ingest-dia DATA=$$dia || { echo "FALHOU: ingestão de $$dia" >&2; falhou=1; }; \
	done; exit $$falhou

ingest-dia: .env ## baixa as edições de DATA e grava as matérias de conselho no banco: um dia só, sem janela
	@# O persist vai num make à parte: a lista de ZIPs e de marcadores dele tem de
	@# ser montada depois do fetch. Ele roda mesmo se o fetch falhou numa seção: o
	@# que foi baixado é gravado, e o make sai com erro no fim. Dia sem edição, dia
	@# que falhou e dia não buscado quem decide é o TEM_EDICAO, dentro do persist.
	@falhou=0; $(MAKE) --no-print-directory fetch DATA=$(DATA) || falhou=1; \
	$(MAKE) --no-print-directory persist DATA=$(DATA) || falhou=1; \
	exit $$falhou

fetch-mensal: ## baixa a Seção 1 do DOU de um mês inteiro dos dados abertos, sem login (MES=AAAA-MM); mês já em disco não baixa de novo
	@$(TEM_MES)
	mkdir -p data/bronze/dados-abertos
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T fetch-mensal -month $(MES)

persist-mensal: .env ## grava no banco as matérias do ZIP mensal de MES já baixado; pode rodar de novo, não duplica
	@$(TEM_MES)
	@if [ ! -f "$(ZIP_MENSAL)" ]; then echo "nenhum $(notdir $(ZIP_MENSAL)) em data/bronze/dados-abertos/ — rode make fetch-mensal MES=$(MES)" >&2; exit 1; fi
	docker compose --progress quiet run --rm -T persist /$(ZIP_MENSAL)

ingest-mensal: .env ## baixa o mês MES dos dados abertos e grava as matérias de conselho no banco; pode rodar de novo, não duplica
	@# Sem o ZIP não há o que gravar: se o fetch falha, o persist nem roda.
	@$(MAKE) --no-print-directory fetch-mensal MES=$(MES) && \
	$(MAKE) --no-print-directory persist-mensal MES=$(MES)

janela: ## lista os dias que o make ingest reprocessa, do mais antigo para o mais novo
	@$(DIAS)

test-py-dou: ## testes do ingestor em Python que não usam banco, no serviço carga (sem rede)
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/dou

test-db-py: .env ## testes do ingestor em Python que gravam no banco, em transação desfeita (banco no ar e migrado)
	docker compose --progress quiet run --rm -T dou-db-test

test-go: ## testes do ingestor em Go, em container (sem rede no código de teste, sem credencial)
	docker compose --progress quiet run --rm -T ingestor-test go test -count=1 ./...

test-db-go: .env ## testes do ingestor que gravam no banco, em transação desfeita (precisa do banco no ar e migrado)
	docker compose --progress quiet run --rm -T ingestor-db-test go test -count=1 ./internal/oltp/ ./cmd/persist/

vet-go: ## gofmt e go vet do ingestor, em container
	docker compose --progress quiet run --rm -T ingestor-test sh -c 'test -z "$$(gofmt -l .)" || { gofmt -l .; echo "FALHOU: arquivos fora do gofmt"; exit 1; }; go vet ./...'

test: .env test-go test-py-dou ## testes: Go e Python do ingestor, infra, esquema do OLTP, leitura da planilha, identidade dos conselhos, carga e persistência do DOU
	bash tests/infra/test_compose.sh
	bash scripts/migrate.sh
	bash tests/db/test_schema.sh
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/planilha
	docker compose --progress quiet run --rm -T --entrypoint python carga -m unittest discover -s tests/conselhos
	bash tests/db/test_carga.sh
	bash tests/ingest/test_janela.sh
	bash tests/lake/test_lake.sh
	bash tests/lake/test_cdc.sh
	$(MAKE) --no-print-directory test-db-go
	$(MAKE) --no-print-directory test-db-py

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

lake: .env ## extrai do OLTP e atualiza a tabela Delta Lake em data/silver/atos/
	mkdir -p data/silver/atos
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T lake

cdc: .env ## aplica no Delta as mudanças de classificacao pendentes no slot lógico (rode make lake antes)
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T cdc

cdc-demo: .env ## demonstração: reclassifica um ato (insert-only) e mostra a mudança chegando ao Delta
	bash scripts/cdc_demo.sh

cdc-chaos: .env ## demonstração de tolerância a falhas: interrompe o consumidor após gravar no Delta e reprocessa
	bash scripts/cdc_chaos_demo.sh

cdc-drop: .env ## remove o slot de replicação (slot parado retém WAL)
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T cdc --drop-slot