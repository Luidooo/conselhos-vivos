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

### 2026-09-26 — Levantamento da #3 e recontagem da planilha

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `README.md`, `docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md`, `docs/adr/0002-manter-postgresql-como-motor-do-oltp.md`, `docs/adr/README.md`, `docs/adr/medicoes/0001-classificacao-vigente.sql`, `docs/diario/2026-09-25.md` (errata), `docs/diario/2026-09-26.md`
- **O que foi pedido:** ler a issue #3 e a planilha, apontar as decisões que precisavam de ADR antes do código e sugerir onde ficam os arquivos da extração.
- **O que foi aproveitado:** a recontagem (215 atos, não 2.638) e a correção dela nos documentos; a proposta do ADR 0003 (ferramenta e forma de execução), com a lista de candidatos reduzida pela squad (o polars saiu); a chave conselho + `ID_VERSAO` no lugar da D3.
- **Como foi verificado:** a contagem foi refeita por três leitores independentes (XML do `.xlsx` lido direto, `openpyxl` 3.1.5 e `pandas` 2.2.3 num container descartável); a planilha de `data/raw` foi comparada byte a byte com a do repositório antigo; a leitura do `DIS_LEG` do CNPIR foi conferida contra o texto do `TEMA` nas 11 linhas.
- **Quem revisou:** Bruno (@BrunoBReis), que escolheu os candidatos e pediu a verificação na planilha original. Revisão do PR: pendente.

### 2026-09-26 — Benchmark de leitores da planilha (#3)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/diario/medicoes/2026-09-26-extracao/resultados.json`, `docs/diario/2026-09-26.md` (o `bench.py`, os `candidatos/` e as `sondas/` ficaram no commit `e4f87eb` e saíram na revisão do PR)
- **O que foi pedido:** testar ferramentas diferentes para a extração da planilha e para a forma de execução, e montar a evidência para a squad decidir.
- **O que foi aproveitado:** o benchmark inteiro, depois de duas mudanças da squad. A recomendação da IA foi DuckDB; a squad escolheu a biblioteca padrão do Python, e o que pesou foi não ter dependência nem comportamento padrão escondido. A IA tinha proposto um ADR 0003; a squad avaliou que uma leitura isolada de `.xlsx` é uma decisão reversível e não justifica um ADR, e o benchmark virou anexo do diário.
- **Como foi verificado:** os três candidatos produzem os mesmos 215 registros, campo a campo; o gabarito dos pontos fixos foi conferido contra o XML e contra o texto do `TEMA`; o benchmark rodou três vezes com resultados estáveis; conferido que nenhuma imagem nem volume de teste sobrou no Docker.
- **Quem revisou:** Bruno (@BrunoBReis), que decidiu a ferramenta e a forma de execução. Revisão do PR: pendente.

### 2026-09-26 — Implementação da carga da planilha (#3)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/planilha/`, `sql/003_chave_da_planilha.sql`, `sql/004_conselhos_da_planilha.sql`, `sql/005_tipologia_99.sql`, `scripts/carga.sh`, `docker-compose.yml` (serviço `carga`), `Makefile`, `tests/planilha/test_planilha.py`, `tests/db/test_carga.sh`, `tests/db/test_schema.sh`, `docs/carga/relatorio-planilha.md`, `README.md`, `.gitignore`, `docs/diario/2026-09-26.md`
- **O que foi pedido:** implementar a #3 com as decisões da squad (biblioteca padrão em container; chave conselho + `ID_VERSAO`; planilha versionada; os 5 conselhos por migração; resumo em `ementa` e texto em `conteudo`; tipologia `99` como sigla).
- **O que foi aproveitado:** tudo. A IA tinha recomendado que os 6 atos `99` entrassem sem classificação; a squad preferiu cadastrar o `99` como sigla. O teste da carga saiu errado na primeira versão (booleano comparado como `t` e um `ORDER BY` ambíguo que o `grep` escondia); foi corrigido, e o teste passou a mostrar a saída inteira do psql quando falha.
- **Como foi verificado:** nomes e datas dos 5 conselhos lidos no texto das leis e decretos no planalto.gov.br; `make setup` + `make test` num clone limpo da branch, com o `git status` vazio no fim; duas cargas seguidas sem mudar o banco nem o relatório; 5 defeitos plantados no código de leitura, todos pegos pelos testes; o caso "não sobrepõe a curadoria" rodado com o `NOT EXISTS` removido, dentro de uma transação desfeita, e ele pegou; conferido que o banco ficou com as mesmas 215 classificações depois disso.
- **Quem revisou:** Bruno (@BrunoBReis), que tomou as decisões de mapeamento. Revisão do PR: pendente — Márcio Henrique e mais uma pessoa da squad.

### 2026-09-26 — ADR 0003 da carga da planilha (#3)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria.md`, `docs/adr/README.md`, `docs/diario/2026-09-26.md`
- **O que foi pedido:** registrar como ADR 0003 as decisões da carga da planilha, já tomadas e implementadas na #3.
- **O que foi aproveitado:** o ADR inteiro. Ele junta a chave conselho + `ID_VERSAO`, a classificação da planilha que não sobrepõe a curadoria, o `99` como sigla e a leitura com a biblioteca padrão; não traz decisão nova.
- **Como foi verificado:** cada número do ADR foi conferido contra o diário de 26/09, o `resultados.json` do benchmark e o relatório da carga; conferido que o commit `e4f87eb` citado para reproduzir o benchmark contém o `bench.py`.
- **Quem revisou:** pendente — a squad, no PR #10.

### 2026-09-26 — ADR 0004: identidade dos conselhos (#4)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md`, `docs/adr/medicoes/0004-identidade/` (`bench.py`, `gabarito.csv`, `resultados.json`), `docs/adr/README.md`
- **O que foi pedido:** entender o contexto da issue #4 e escrever o ADR 0004 antes de qualquer execução; a implementação espera a validação do ADR.
- **O que foi aproveitado:** o ADR inteiro, validado antes da execução da issue. O gabarito das 125 linhas é proposta da IA e precisa ser conferido pela squad e pela pesquisadora.
- **Como foi verificado:** as renomeações foram lidas no texto das leis e decretos no planalto.gov.br (Lei 12.986/2014, Decreto 9.893/2019, Lei 7.353/1985, Decreto 11.351/2023, Decreto 10.991/2022); o SIORG foi consultado pela API pública e o sha256 do arquivo ficou registrado; o benchmark foi rodado e os números do ADR foram copiados do `resultados.json`; os pares mais parecidos de conselhos diferentes foram listados para achar o limiar de similaridade.
- **Quem revisou:** pendente — a squad, no PR.

### 2026-09-26 — Implementação da identidade dos conselhos (#4)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/conselhos/`, `sql/006_identidade_dos_conselhos.sql`, `data/referencia/conselhos-decisoes.csv`, `data/referencia/siorg-conselhos.csv`, `scripts/carga.sh`, `docker-compose.yml` (serviço `siorg` e montagens do `carga`), `Makefile`, `tests/conselhos/test_conselhos.py`, `tests/db/test_carga.sh`, `tests/db/test_schema.sh`, `docs/carga/relatorio-conselhos.md`, `README.md`, `docs/diario/2026-09-26.md`
- **O que foi pedido:** executar a #4 conforme o ADR 0004 validado, trazendo as opções de cada decisão de implementação para escolha antes do código.
- **O que foi aproveitado:** tudo, com as opções escolhidas em cada decisão (formato do CSV, recorte do SIORG, comando, modelo do alias, origem do nome vigente, colunas do SIORG e da sigla, ambíguos sem órgão, data das renomeações sem "passa a denominar-se"). Dois erros da IA apareceram nos testes e foram corrigidos: uma vírgula sem aspas no CSV, que deslocava as colunas sem erro, e uma variável PL/pgSQL com o nome de uma coluna.
- **Como foi verificado:** a partição da carga foi comparada linha a linha com o gabarito do ADR; `make setup` + `make test` num diretório limpo, com volume novo; duas cargas seguidas sem mudar o banco nem os relatórios; 5 defeitos plantados na identidade, todos pegos; os relatórios do diretório limpo são idênticos aos versionados.
- **Quem revisou:** pendente — a squad, no PR. O CSV de decisões precisa da revisão da pesquisadora.

### 2026-09-28 — Site de documentação (GitHub Pages)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `site/` (VitePress: configuração, tema, página inicial e página "Entrega E1"), `.github/workflows/docs.yml`, `Makefile` (`make docs`), `README.md`
- **O que foi pedido:** um site de documentação no GitHub Pages para a professora e a monitoria, no ar junto com a E1, com visual no estilo da Apple.
- **O que foi aproveitado:** o site inteiro. As páginas são os `.md` do próprio repositório; só a página inicial e a "Entrega E1" foram escritas para o site, a partir do `main` (números conferidos nos relatórios de carga). Links para `.csv`, `.py`, `.sql` e pastas são reescritos para o GitHub.
- **Como foi verificado:** `npm run build` sem link quebrado (14 páginas); links reescritos conferidos no HTML gerado; navegação conferida no navegador, em claro e escuro; YAML do workflow validado.
- **Quem revisou:** pendente — a squad, no PR.
