# AI-USAGE.md — Squad Conselhos Vivos

Registro de uso de assistentes e agentes de IA no Projeto Integrado.

Este arquivo cumpre a [Política de Uso de IA](https://unb-bd2.github.io/PlanoEnsino/uso-de-ia/)
da disciplina. Ele não é confissão nem formalidade: é o mesmo tipo de registro
que um ADR faz para decisões de arquitetura.

**Duas regras de forma.** Escreva **no momento do uso**, não na véspera da
Entrega — registro reconstruído de memória sai impreciso, e imprecisão aqui é o
que a política pune. E versione junto com o código: uma entrada por commit
relevante é melhor que um resumo mensal.

**Não precisa registrar** autocompletar de editor, correção ortográfica ou
tradução. Registre o que produziu artefato ou mudou uma decisão.

## Princípios da squad

- Toda saída de IA é **verificada em fonte primária** antes de entrar no repositório.
- Decisões de arquitetura são da equipe. IA ajuda a levantar alternativas; quem escolhe e assina o ADR somos nós.
- Código gerado com auxílio de IA passa pela mesma revisão que qualquer outro.

---

## Entradas

### 2026-09-25 — Levantamento do domínio

- **Ferramenta:** Claude Code
- **Onde:** `docs/diario/2026-09-25.md`
- **O que foi pedido:** transcrever o áudio de briefing, ler as planilhas da pesquisadora e pesquisar a estrutura do DOU/INLABS.
- **O que foi aproveitado:** não registrado na época. _Convertido do formato antigo de tabela em 26/09._
- **Como foi verificado:** segundo o diário, todo número citado foi conferido em fonte primária (arquivo aberto, requisição executada ou código-fonte lido).
- **Quem revisou:** não registrado na época.

### 2026-09-25 — Briefing da squad e README

- **Ferramenta:** Claude Code
- **Onde:** `README.md`, briefing da squad
- **O que foi pedido:** redigir o briefing da squad e o README.
- **O que foi aproveitado:** não registrado na época. _Convertido do formato antigo de tabela em 26/09._
- **Como foi verificado:** não registrado na época.
- **Quem revisou:** não registrado na época.

### 2026-09-26 — Planejamento da issue #1 (Postgres com docker compose)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** plano de implementação da #1 (fora do repositório)
- **O que foi pedido:** ler o plano de ensino e o checklist da E1, e planejar a #1 incluindo o registro em diário e neste arquivo.
- **O que foi aproveitado:** o plano inteiro. Descartamos o contorno proposto para o conflito de porta (usar `5433` no `.env` local) depois de parar o Postgres do Homebrew que ocupava a `5432`.
- **Como foi verificado:** as tags `postgres:16.15` e `adminer:5.4.2` foram conferidas no Docker Hub; o conflito de porta foi confirmado com `lsof`.
- **Quem revisou:** Luiza (@LuizaMaluf)

### 2026-09-26 — Implementação da issue #1 (PR #7)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docker-compose.yml`, `Makefile`, `tests/infra/test_compose.sh`, seção "Como rodar" do `README.md`, `docs/diario/2026-09-26.md`
- **O que foi pedido:** executar o plano da #1, um `make setup` que sobe tudo num comando, e depois trocar o admin web por pgAdmin.
- **O que foi aproveitado:** tudo, exceto o adminer: a primeira versão usava adminer, que trocamos por pgAdmin pré-configurado depois que o login falhou com `localhost` no campo servidor.
- **Como foi verificado:** teste de fumaça (sobe healthy, grava, `down` + `up`, confere a linha); `psql` do host respondendo `linux` (container) e não `darwin`; pgAdmin conectando sem senha no navegador; clone limpo do `main` no GitHub com `make setup` + `make test`.
- **Quem revisou:** Luiza (@LuizaMaluf), que abriu e mergeou o PR #7.

### 2026-09-26 — Revisão pós-merge do PR #7 e correções

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docker-compose.yml`, `tests/infra/test_compose.sh`, `Makefile` (`make pgadmin-reset`), `README.md`, `docs/diario/2026-09-26.md`
- **O que foi pedido:** revisar o PR #7 procurando bugs e corrigir o que fosse encontrado.
- **O que foi aproveitado:** os 6 achados. Os dois graves eram de segurança e foram introduzidos pela própria IA na implementação: pgAdmin sem login e Postgres publicados em `0.0.0.0`. Também: `source .env` frágil no teste, `servers.json` que não acompanha o `.env` e mensagem de falha inalcançável no teste.
- **Como foi verificado:** medido antes e depois pelo IP da rede — antes, HTTP 200 no pgAdmin e login no `psql` com a senha do README; depois, os dois recusados. O teste de fumaça agora falha se alguma porta sair de `127.0.0.1`; ele foi visto falhando antes da correção e passando depois. Uma senha com espaço, `;` e `$` no `.env` não quebra mais o teste.
- **Quem revisou:** Moura (@thegm445), que aprovou o PR #8.

### 2026-09-26 — Revisão e correções do esquema da #2

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `sql/001_schema.sql`, `sql/002_seeds.sql`, `scripts/migrate.sh`, `tests/db/test_schema.sh`, `Makefile`, `docker-compose.yml`, `README.md`, `docs/diario/2026-09-26.md`
- **O que foi pedido:** revisar a branch da #2 (DDL e teste), montar um plano de correções e implementá-lo na própria branch.
- **O que foi aproveitado:** todas as correções da revisão. As decisões D1 (insert-only), D2 (classificar a versão) e D3 (`ref_legal` como chave da planilha) foram adotadas como proposta e ainda precisam ser confirmadas pela squad no ADR (#5).
- **Como foi verificado:** o teste reescrito falhou nos 16 casos no banco local (sem tabelas, pelo bug do `initdb`) e em 13 num banco zerado; passou nos 16 depois das correções. `make migrate` rodado duas vezes; `make test` completo; clone limpo com `make setup` + `make test`; conferido que o teste não deixa linhas no banco.
- **Quem revisou:** pendente — Moura (@thegm445), dono da branch, e mais uma pessoa, como pede a issue.

### 2026-09-26 — Rascunho do ADR 0001 e medição insert-only × CRUD

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md`, `docs/adr/medicoes/0001-classificacao-vigente.sql`, `docs/adr/README.md`
- **O que foi pedido:** montar o rascunho do ADR 0001 a partir do roteiro do Moura e da issue #5.
- **O que foi aproveitado:** a estrutura do roteiro do Moura (contexto, ganhos e perdas, gatilho). Foram trocadas a opção nula e a alternativa B do roteiro, que eram espantalhos, pelas alternativas da issue #5 (planilhas como opção nula, espelho do DOU, Brasil Participativo). O gatilho de 200 ms virou limiares sobre uma linha de base medida.
- **Como foi verificado:** o script de medição roda numa transação desfeita (conferido: 0 atos no banco depois); 5 execuções por volume, com a mediana no ADR. Dados sintéticos no volume do domínio, declarados como tais no ADR.
- **Quem revisou:** pendente — a squad, no PR.

### 2026-09-26 — ADR 0002 e benchmark de motores

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/adr/0002-manter-postgresql-como-motor-do-oltp.md`, `docs/adr/medicoes/0002-motor/bench.py`, `docs/adr/medicoes/0002-motor/resultados.json`, `docs/adr/README.md`
- **O que foi pedido:** explicar por que PostgreSQL e não outro banco, e montar um benchmark com PostgreSQL, MySQL, MariaDB, SQLite e Cassandra.
- **O que foi aproveitado:** o benchmark e o rascunho do ADR inteiros. Descartamos como argumento o "CDC do Postgres" contra MySQL/MariaDB: o Debezium lê o binlog deles igualmente bem, e isso ficou escrito no ADR.
- **Como foi verificado:** C1 a C5 executadas em cada motor, não lidas na documentação; o benchmark rodou duas vezes com resultados estáveis; a diferença de 1 classificação no indicador do Cassandra foi rastreada até o `UPDATE` aceito no C5. Conferido que nenhum container de teste sobrou e que o `make test` do projeto continua passando.
- **Quem revisou:** pendente — a squad, no PR.
