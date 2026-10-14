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
- **Quem revisou:** ninguém além da autora: o PR #13 foi mergeado pela Luiza sem revisão de outra pessoa da squad.

### 2026-09-28 — Página "Jornada do dado" no site

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `site/jornada-do-dado.md`, `site/.vitepress/config.mts`, `site/.vitepress/theme/custom.css`, `site/index.md`
- **O que foi pedido:** uma página sobre a jornada do dado: replicar a planilha feita hoje à mão e depois enriquecê-la com a tipologia da pesquisadora, usando IA classificatória.
- **O que foi aproveitado:** a página inteira. O limite de validação (só 4 dos 215 atos são de 2020 em diante, quando o INLABS começa) foi medido no banco e entrou na página como decisão pendente da E2.
- **Como foi verificado:** consulta ao banco para o período dos atos por conselho; distribuição da tipologia conferida no relatório da carga; build sem link quebrado; página conferida no navegador.
- **Quem revisou:** Luiza

### 2026-09-28 — Diagrama da jornada do dado (Mermaid) e etapa do RAG

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `site/jornada-do-dado.md`, `site/.vitepress/config.mts`, `site/.vitepress/theme/custom.css`, `site/package.json`, `.gitignore`
- **O que foi pedido:** um diagrama Mermaid vertical e grande da jornada do dado, com nomes compreensíveis para leigos, terminando num assistente de perguntas (RAG); e tirar do fluxo a etapa em que a pesquisadora valida a classificação da IA.
- **O que foi aproveitado:** o diagrama e a seção do RAG. A primeira versão (horizontal, com termos técnicos como "Bronze · Parquet" e "artCategory × aliases") foi descartada a pedido. O plugin `vitepress-plugin-mermaid` exigiu declarar dependências CommonJS e um link `node_modules` na raiz para o modo dev.
- **Como foi verificado:** build sem link quebrado; no navegador, em claro e escuro, conferido que nenhum rótulo do diagrama fica cortado e que o Mermaid não acusa erro.
- **Observação:** tirar a validação da classificação pela pesquisadora deixa a página em desacordo com o ADR 0001, que justifica o OLTP pelo julgamento humano da curadoria. A squad precisa decidir entre manter a validação como opcional ou revisar o ADR 0001.
- **Quem revisou:** pendente — a squad, no PR.

### 2026-09-28 — Frase de abertura do site (PR #14)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `site/index.md`
- **O que foi pedido:** reescrever a frase da página inicial, que estava estranha.
- **O que foi aproveitado:** uma das três opções propostas, escolhida pela Luiza.
- **Como foi verificado:** build sem link quebrado; frase conferida no navegador.
- **Quem revisou:** ninguém além da autora: o PR #14 foi mergeado pela Luiza sem revisão de outra pessoa da squad.

### 2026-09-28 — Diagnóstico do deploy do site

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** GitHub Actions, workflow `docs.yml` (nenhum arquivo alterado)
- **O que foi pedido:** descobrir por que o deploy quebrou depois do merge do PR #13.
- **O que foi aproveitado:** o diagnóstico. O build passou e o deploy falhou com HTTP 404, porque o GitHub Pages não estava ligado no repositório (confirmado pela API: `has_pages: false`). Só o dono do repositório consegue ligar.
- **Como foi verificado:** log da execução que falhou (`gh run view --log-failed`) e consulta à API do repositório.
- **Quem revisou:** não se aplica: não houve mudança de código.

### 2026-09-28 — Teste do esquema no macOS (PR #15)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `tests/db/test_schema.sh`
- **O que foi pedido:** entender a falha do `make test` no Mac da Luiza.
- **O que foi aproveitado:** a correção inteira, de um caractere: `paste -sd,` virou `paste -sd, -`, porque o `paste` do macOS exige o `-` para ler da entrada. Antes disso, um erro de `codigo_siorg` foi descartado como bug: ele veio de dois `make reset` rodando ao mesmo tempo, um da Luiza e outro da IA.
- **Como foi verificado:** `make test` completo no Mac depois da correção: infra 5/5, esquema 26/26, planilha 21/21, conselhos 27/27, carga 15/15.
- **Quem revisou:** ninguém além da autora: o PR #15 foi mergeado pela Luiza sem revisão de outra pessoa da squad.

### 2026-09-28 — Guia e roteiro da apresentação da E1

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** fora do repositório (roteiro em PDF, guia de preparação e textos dos PRs #13, #14 e #15)
- **O que foi pedido:** um guia de preparação, um roteiro falado de cerca de 10 minutos com as perguntas prováveis, e o roteiro em PDF.
- **O que foi aproveitado:** o roteiro e a lista de perguntas. Os números citados (215 atos, 82 conselhos, 16,4 ms contra 4,1 ms, 94 verificações) foram conferidos nos ADRs, nos relatórios de carga e na saída do `make test`.
- **Como foi verificado:** cada número conferido na fonte; o PDF foi renderizado e revisado página por página.
- **Quem revisou:** Luiza. A apresentação e a arguição são individuais e sem IA, como pede a política da disciplina.

### 2026-10-02 — Configuração do comando fetch por ambiente

- **Ferramenta:** Claude Code (Claude Opus 5)
- **Onde:** `src/ingestor/internal/config/`, `src/ingestor/cmd/fetch/main.go`, `src/ingestor/go.mod`, `src/ingestor/justfile`, `.env.example`
- **O que foi pedido:** ler as credenciais do INLABS do ambiente, com um arquivo `.env` opcional para o uso local e o ambiente ganhando dele. Registro em retrospecto: o pedido foi feito em sessão anterior e não foi anotado na hora.
- **O que foi aproveitado:** o pacote `internal/config` e o esqueleto do comando `fetch` (commit `7917176`). Somar `caarlos0/env` e `joho/godotenv` em vez de escrever o parser de `.env` à mão foi decisão do Iago, que rejeitou o parser que a IA havia escrito. A mensagem do commit foi redigida pela IA nesta sessão.
- **Como foi verificado:** `go test ./...` no dev shell do `flake.nix` (Go 1.26.8): 7 testes em `internal/config` passando, sem rede e sem credenciais.
- **Quem revisou:** Iago, que escolheu as bibliotecas e fez o commit.

### 2026-10-02 — Cliente de login do INLABS e seus testes

- **Ferramenta:** Claude Code (Claude Opus 5)
- **Onde:** `src/ingestor/internal/inlabs/inlabsclient.go`, `src/ingestor/internal/inlabs/inlabsclient_test.go`, `src/ingestor/cmd/fetch/main.go`
- **O que foi pedido:** explicar o `script.sh` de referência do INLABS (o `curl` do login, o que é header de requisição, o que é cookie e por que o jar entra no `http.Client`), traduzir o login para Go, revisar a implementação escrita pelo Iago e escrever os testes.
- **O que foi aproveitado:** a explicação do protocolo — o header `origem: 736372697074` é a palavra "script" em hexadecimal, e o cookie `inlabs_session_cookie` é a única prova de login, porque o `logar.php` responde 200 com HTML quando a credencial é recusada. O cliente foi escrito pelo Iago a partir dessa tradução; da IA são os cinco testes com `httptest`, o `baseURL` como campo do `Client` (sem isso não há como exercitar o 200-com-HTML) e o wiring no `main`. Na revisão a IA apontou dois bugs reais — URL sem a barra antes de `logar.php` e o header escrito `origin` em vez de `origem` —, mas afirmou que ainda estavam no arquivo quando já tinham sido corrigidos; o erro só apareceu porque o Iago pediu confirmação. A IA também apontou que `script.sh` e `cookies.iakim` estavam no diretório fora do `.gitignore`, com senha e sessão ativa em texto puro: o `cookies.iakim` foi removido, o `script.sh` segue pendente.
- **Como foi verificado:** `gofmt -l` sem saída, `go vet ./...` limpo e `go test -race -count=1 ./...` verde no dev shell do `flake.nix` (Go 1.26.8): `internal/config` 7/7 e `internal/inlabs` 5/5. Os testes rodam contra `httptest.NewServer`, sem rede e sem credenciais. Rodar foi o que pegou dois deadlocks no teste de cancelamento, ambos escritos pela IA: esperar em `r.Context().Done()` dentro do handler, quando o servidor só detecta a desconexão depois que o corpo da requisição é lido, e liberar o handler em `t.Cleanup`, que roda LIFO e portanto depois do `server.Close`.
- **Quem revisou:** Iago, que escreveu o cliente e acompanhou cada passo da sessão.

### 2026-10-02 — Baixador de ZIPs do INLABS: plano, revisão e implementação

- **Ferramenta:** Claude Code (Claude Opus 5)
- **Onde:** `docs/plans/2026-10-02-1227-feat-baixador-zip-inlabs-plan.md`, `docs/adr/0005-...md`, `pr.md`, `src/ingestor/internal/inlabs/`, `src/ingestor/internal/store/`, `src/ingestor/cmd/fetch/`, `docker-compose.yml`, `Makefile`, `tests/infra/test_compose.sh`, `README.md`
- **O que foi pedido:** planejar o baixador de ponta a ponta com perguntas sobre os detalhes, preferindo bibliotecas a código próprio; depois implementar o plano, sem commit nem publicação.
- **O que foi aproveitado:** o plano inteiro (25 requisitos, 12 decisões no ADR 0005, 6 unidades) e a implementação. Decisões de produto foram do Iago, contra as opções apresentadas: idempotência fora de escopo (porque a edição do próprio dia pode ser republicada, o que invalida "pular se já existe"), `DO1E` dentro, uma data por execução em vez de intervalo, documentação em português. A revisão do plano por cinco revisores em paralelo rendeu 16 correções, das quais as que mais valeram foram fatos que não se sustentavam: o teste de mount gravável nunca veria o serviço novo (serviço com `profiles` não aparece em `docker compose config`), o `.gitkeep` seguiria ignorado (a exceção do `.gitignore` alcança um nível só), e o `go run` apagaria o código de saída 2. Um probe sem credencial contra o INLABS substituiu por evidência uma afirmação que a IA havia herdado de um plano apagado e repetido como verificada — o `302` para `acessar.php` existe, mas o header `origem` não é o gate que ela dizia ser.
- **Como foi verificado:** `go test -count=1 -race ./...` no dev shell do `flake.nix` (Go 1.26.8) — 42 testes, 69 casos com subtestes, quatro pacotes em `ok`; `go vet ./...` limpo e `gofmt -l` sem saída. A consulta do teste de mount foi conferida contra o JSON real do `docker compose --profile '*' config`. **Não** foram exercitados nesta máquina: `make test-go`, `make vet-go` e `make fetch`, que precisam baixar a imagem `golang:1.26.8`, nem o caso novo do `tests/infra`, que precisa de `jq` (ausente). Fica registrado no `pr.md`.
- **Quem revisou:** Iago, que acompanhou cada passo, cortou escopo três vezes (seções, intervalo de datas, e o pacote de data inteiro, reconstruído depois pela unidade U1) e removeu wrappers que a IA havia escrito em volta de funções de biblioteca.

### 2026-10-03 — Mover o trabalho do baixador para dentro do pacote `inlabs`

- **Ferramenta:** Claude Code (Claude Opus 5)
- **Onde:** `src/ingestor/internal/inlabs/` (`workflow.go` novo, `date.go`, `inlabsclient.go` e testes), `src/ingestor/cmd/fetch/main.go`, `src/ingestor/internal/store/store.go`, `docker-compose.yml`, `Makefile`, `README.md`, `issues/*.json` (corpos das issues novas, fora do versionamento)
- **O que foi pedido:** tirar do `main` o que é domínio do INLABS — a janela de datas servidas, o login e o laço pelas seções —, deixando o comando como orquestrador; tornar o `-date` obrigatório; enxugar os comentários; impedir que o programa crie o diretório de saída; e, no fim, redigir as issues que faltam para fechar a #6.
- **O que foi aproveitado:** as movimentações e os testes novos. O `main` ficou com flag, configuração, log e código de saída; o `FetchDay` passou a ser a única porta do pacote, com `Outcome`, `Summary` e o `Saver`. Decisões foram do Iago, contra o que a IA havia escrito: a validação de data virou **erro de domínio** (sai com 1, dentro do fluxo) em vez do erro de uso que a IA mantinha no `main`; a lista de erros fatais foi **invertida** em lista do que é seguro continuar (`survivable`), porque o conjunto de jeitos de um disco falhar é aberto e a IA havia herdado um blocklist que não cobria `EDQUOT` nem `EIO`; o `Sections()` virou `var sections` sem acessor, junto com `Section` e `ZipName`, que não tinham o que fazer no `date.go`. O Iago também cortou comentários por conta e **rejeitou uma mudança que a IA fez sem pedido** — defaults de `POSTGRES_*` no compose, revertidos; o volume `pgdata` desta worktree ficou inicializado com os valores default, o que precisa de `docker compose down -v` para voltar ao estado anterior. **As issues também foram escritas com a ferramenta.** No fim da sessão, a quebra da #6 em quatro — extrair as matérias dos XMLs, persistir uma matéria no OLTP, idempotência, e vários dias numa execução — saiu como quatro JSONs para o Iago submeter pelo `gh`, com o escopo e a ordem decididos por ele (1 e 2 são módulos que funcionam sozinhos, 3 é limpeza, 4 é otimização opcional). A IA deixou de propósito como decisão em aberto, e não escolheu, o que fazer com o HTML do `Texto`, se o `id_dou` vem do `id` ou do `idMateria`, o que fazer com matéria de órgão fora dos 82 conhecidos, e onde mora o registro de estado. O conteúdo das issues anteriores do repositório também foi redigido com a ferramenta. _Registro em retrospecto quanto às issues anteriores: não foi anotado na hora._
- **Como foi verificado:** `gofmt -l` sem saída, `go vet ./...` limpo e `go test -race -count=1 ./...` verde no dev shell do `flake.nix` (Go 1.26.8) — 58 testes, 100 casos com subtestes, quatro pacotes em `ok`. O binário foi construído e exercitado à mão nos caminhos de recusa: sem `-date` (código 2), data malformada (2), data futura e anterior a 2020 (1, sem nenhuma requisição), diretório de saída inexistente e caminho que é arquivo (1). O erro de mount do `make fetch` foi reproduzido e corrigido movendo o único bind gravável para fora do `/app` (`:ro`): `./data/bronze:/data/bronze`. Os binds da config renderizada foram listados para conferir que o gravável continua sendo só `./data/bronze`, como exige o D11 — com Python, porque `jq` não existe nesta máquina e o caso 6/6 do `tests/infra` segue sem rodar. **Não** foi exercitado o download real: o `make fetch` para no `go: updating go.mod: open /app/go.mod: read-only file system`, porque `cloud.google.com/go` e `go-retryablehttp` estão marcados `// indirect` sendo diretos (visto com `go mod tidy -diff`); o `go mod tidy` ficou pendente, a pedido. Os corpos das issues foram ancorados no que já existe no repositório, não no que a IA supôs: a #6 foi lida inteira, e as colunas citadas (`ato.origem`, `id_dou`, `versao`, `uq_ato_dou_versao`, `ck_ato_dou_completo`) foram conferidas no `sql/001_schema.sql`; as labels existentes foram listadas com `gh label list`. Os quatro JSONs foram validados por parsing.
- **Quem revisou:** Iago, que acompanhou cada passo, tomou as decisões acima, mandou reverter o que não havia pedido e é quem submete as issues.

### 2026-10-05 — Revisão e merge do PR #17 (baixador do INLABS)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `Makefile` (alvo `fetch`), issue #21, PR #17
- **O que foi pedido:** um panorama das issues e PRs do projeto, e depois revisar o PR #17 do Iago para mergeá-lo.
- **O que foi aproveitado:** dois achados da revisão. O primeiro foi corrigido antes do merge: num clone novo o `make fetch` falhava, porque o `store.New` exige o diretório de saída e nada criava `data/bronze/inlabs` — o Docker criava `./data/bronze` como root e o comando abortava. A correção é um `mkdir -p` no alvo. O segundo virou a issue #21: uma conexão que cai no meio do corpo do ZIP não é tratada como recuperável pelo `survivable` e aborta o dia inteiro. A escolha entre corrigir na branch e mergear ou pedir a correção ao autor foi do Luis.
- **Como foi verificado:** os dois achados foram conferidos no código da branch (o alvo `fetch` sem `mkdir`, o `.gitignore` com `data/bronze/**`, o `survivable` sem erro de rede de leitura). `go vet ./...`, `gofmt -l` e `go test -race ./...` verdes na branch, `go mod tidy -diff` sem diferença e o histórico dos 17 commits varrido atrás de credencial. A correção foi conferida com `make -n fetch`; o download real não foi exercitado, por falta de credencial do INLABS nesta máquina. O CI do PR passou depois do commit.
- **Quem revisou:** Luis, que decidiu o merge. Depois do merge, o Iago apontou que os 17 commits da branch deveriam ter entrado com squash; a IA recomendou não reescrever a `main` com force-push, e o repositório passou a aceitar só squash merge.

### 2026-10-05 — Extração das matérias dos ZIPs do INLABS (#18)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/article/`, `src/ingestor/cmd/extract/`, `docker-compose.yml` (serviço `extract`), `Makefile` (alvo `extract`), `README.md`
- **O que foi pedido:** pegar uma issue aberta e implementá-la; a IA sugeriu a #18 por não depender de nada e destravar a #20.
- **O que foi aproveitado:** a implementação inteira. Decisões tomadas pela IA, a revisar pela squad: (1) o HTML do `<Texto>` é guardado **cru e também como texto puro** — o cru é a fonte da verdade, porque as marcas `assina` e `identifica` só existem nele; a recomendação para a #19 é gravar o cru em `ato.conteudo`; (2) `id`, `idMateria`, `numberPage` e `editionNumber` ficam como texto, porque `ato.id_dou` é `VARCHAR` e edição extra tem número como `187-A`; (3) entrada que não é XML é ignorada e logada, não é falha, porque o INLABS manda as imagens no mesmo ZIP; (4) XML sem `id`, `pubDate` ou `artCategory` é recusado, porque a persistência não teria como chaveá-lo nem atribuí-lo. A leitura de XML em qualquer profundidade do ZIP segue o Ro-dou (`glob **/*.xml`), lido no código-fonte dele.
- **Como foi verificado:** duas matérias reais versionadas como amostra, sem alteração (BOM UTF-8 e CRLF incluídos), de `viniciusrpb/xml2csv_diariooficialdauniao`; o teste confere campo a campo contra o arquivo. Como nenhuma amostra pública é de conselho, uma terceira foi **construída** no mesmo formato e está marcada como tal em `testdata/README.md`. `gofmt -l` sem saída, `go vet ./...` limpo e `go test -race -count=1 ./...` verde (Go 1.26.8, seis pacotes). O `make extract` foi rodado no Docker sobre um ZIP montado com as amostras, um XML malformado e uma imagem: imprimiu as duas matérias, logou o nome do arquivo malformado e o da imagem, e saiu com 1. **Não** foi exercitado contra um ZIP real do INLABS, por falta de credencial nesta máquina — é o primeiro critério de aceite da #18 e fica para quem tiver acesso.
- **Quem revisou:** Luis, que pediu o commit e o PR; a revisão da squad fica no PR.

### 2026-10-08 — Revisão do Iago no PR #22 (#18)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/cmd/extract/`, `src/ingestor/internal/article/`, `Makefile`, `README.md`, respostas no PR #22
- **O que foi pedido:** aplicar os comentários de revisão do Iago no PR #22 e respondê-los.
- **O que foi aproveitado:** três dos quatro comentários viraram mudança, todos propostos pelo Iago: o `extract` passou a ler **um ZIP por execução** (o `make extract` roda uma vez por edição); uma pasta dentro do ZIP deixou de ser pulada em silêncio e passou a sair como `ErrNotXML`, que o comando loga — o que atende ao pedido de logar sem pôr um logger dentro do pacote; e o `Parse` virou privado. O quarto, centralizar a criação do logger, a IA recomendou não fazer agora (uma linha repetida em dois comandos), e a resposta deixou a decisão em aberto para o Iago.
- **Como foi verificado:** teste novo para a pasta dentro do ZIP; `gofmt -l` sem saída, `go vet ./...` limpo e `go test -race -count=1 ./...` verde nos seis pacotes. O `make extract` foi rodado no Docker com dois ZIPs montados das amostras (um DO1 com XML malformado e uma pasta, um DO1E com uma matéria): o DO1E rodou apesar da falha do DO1, a pasta saiu logada como ignorada, e o make terminou com erro.
- **Quem revisou:** Luis, que pediu a aplicação; a revisão final é do Iago, no PR.

### 2026-10-10 — Persistência de uma matéria do DOU no OLTP (#19)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/oltp/`, `src/ingestor/go.mod`, `docker-compose.yml` (serviço `ingestor-db-test`), `Makefile` (alvo `test-db-go`), `README.md`; merge do PR #22
- **O que foi pedido:** conferir a revisão do PR #22, fazer o merge e implementar a #19, já combinada com o Iago, que é o responsável pela issue.
- **O que foi aproveitado:** a implementação inteira. As duas decisões que a issue deixava em aberto foram **recomendadas pela IA e aceitas pelo Luis**, a revisar pela squad: (1) o `id_dou` é o `id` do `<article>`, e não o `idMateria`, porque a extração já recusa XML sem `id` e não valida o `idMateria`; (2) matéria de órgão fora dos conhecidos não entra em `ato`, e o nome do órgão entra uma vez em `orgao_alias` com `fonte = 'DOU'` e `status = 'INDEFINIDO'`, como a fila de decisão do ADR 0004. **Decididas pela IA sem consulta prévia**, também a revisar: chave que casa com mais de um órgão não escolhe nenhum e entra na fila como `AMBIGUO`; matéria com `<Texto>` vazio é recusada; só o último nível do `artCategory` é casado; o órgão é procurado em `orgao_nome` (nomes vigentes e antigos) e nos aliases resolvidos, com a chave recalculada em Go a partir do nome; e o pacote ficou **sem comando** que o chame, porque gravar um ZIP inteiro esbarra na #20. O merge do PR #22 saiu como squash, o único método que o repositório aceita.
- **Como foi verificado:** `make test` inteiro verde a partir de um clone sem `.env` e sem volume do banco, e `make vet-go` limpo. Os testes do pacote rodam contra o Postgres do compose, cada um numa transação desfeita; as contagens de `ato`, `orgao`, `orgao_nome` e `orgao_alias` foram lidas antes e depois e ficaram iguais (215, 82, 85, 125), e a saída com `-v` foi conferida para garantir que nenhum teste foi pulado. O porte da chave para Go foi conferido contra os 125 aliases que a carga em Python gravou, e bateu em todos. **Não** foi verificado em dado real: não há ZIP do INLABS nesta máquina, então a escolha do `id` não foi medida — o PR #22 já anotava que o Ro-dou faz `drop_duplicates` por `id`, o que sugere que o mesmo `id` pode se repetir num dia. O tamanho da fila de órgãos desconhecidos também não foi medido.
- **Quem revisou:** Luis, que aceitou as recomendações e pediu o commit e o PR; a revisão da squad fica no PR.

### 2026-10-11 — Revisão do PR #23 e ajustes na persistência (#19)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/oltp/oltp.go`, `src/ingestor/internal/oltp/oltp_test.go`, `Makefile` (alvo `test-db-go`); comentário de revisão no PR #23
- **O que foi pedido:** revisar o PR #23, montar o comentário de revisão e aplicar na própria branch os ajustes que cabiam neste PR, porque o autor não podia mexer agora.
- **O que foi aproveitado:** dois ajustes. (1) `test-db-go` passou a depender do `.env`, como o `up` e o `test`: sem ele, o serviço `ingestor-db-test` sobe com `PGUSER` vazio e o erro é de autenticação. (2) Uma `<Ementa>` só com espaços ou quebras de linha passou a ser gravada como `NULL`, com `strings.TrimSpace` no Go. A primeira tentativa, `btrim` no SQL, foi descartada: sem argumento, o `btrim` do Postgres só remove espaços, e o teste continuou falhando com `\n` e `\t`. O achado da ementa ficou **mais fraco do que a revisão disse**: a extração já faz `TrimSpace` na ementa (`article.go`), então o problema só aparece para quem montar um `Article` à mão. O terceiro achado, a transação abortada por uma matéria repetida, ficou para a #20, junto com a idempotência.
- **Como foi verificado:** teste novo (`TestSaveLeavesABlankEmentaNull`) visto falhando antes da correção e passando depois; `make test-db-go` com os 9 testes do pacote verdes; `make vet-go` e `make test-go` limpos.
- **Quem revisou:** pendente — o Luis (autor do PR) e o Iago, no PR.

### 2026-10-11 — Diários de bordo das semanas 8, 9 e 10 (#26)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/diario/2026-09-29.md`, `docs/diario/2026-10-06.md`, `docs/diario/2026-10-13.md`, `site/.vitepress/config.mts` (menu "Processo")
- **O que foi pedido:** escrever os diários que faltavam para o checklist da E2, no formato dos anteriores (medido, surpreendeu, decidido), a partir do histórico.
- **O que foi aproveitado:** os três textos, ainda sem revisão da squad. **Decidido pela IA**, a revisar: um arquivo por semana, com a data de referência da issue no nome; o cabeçalho traz "Quem trabalhou", tirado dos autores de PRs, revisões e issues, em vez de "Presentes", porque não há ata das reuniões; cada diário ganhou uma seção "O que ficou em aberto"; e o da semana 10 foi escrito em 11/10, antes de a semana fechar, e diz isso no cabeçalho.
- **Como foi verificado:** os números das tabelas foram conferidos na API do GitHub (arquivos, linhas e commits de cada PR; datas de criação, merge e fechamento; responsáveis das issues), no texto dos PRs #17, #22, #23 e #35 e nas entradas deste arquivo. A contagem de testes em Go (87, dos quais 11 só com banco) foi obtida rodando-os na branch do PR #35. `npm run build` do site sem link quebrado, com os três diários no menu. **Não** foi verificado: quem esteve em cada reunião, nem nada do que não deixou rastro em PR, issue ou neste arquivo — conversas da squad fora do GitHub não entraram.
- **Quem revisou:** pendente — cada pessoa citada deveria conferir a parte que é dela.

### 2026-10-11 — CI rodando `make test` em todo PR

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `.github/workflows/test.yml`, `README.md`
- **O que foi pedido:** o que mais dava para adiantar na E2; a IA apontou que o único CI era o build do site e que nenhum PR rodava os testes, e o Luis pediu para começar por aí.
- **O que foi aproveitado:** o workflow inteiro. **Decidido pela IA**, a revisar: roda em todo PR, inclusive os só de documentação, porque os testes em Python leem `docs/adr/medicoes`; roda `make test` antes do `make vet-go`, porque é o `make test` que cria o `.env`; e inclui um passo `git diff --exit-code`, que falha se a carga reescrever os relatórios versionados com conteúdo diferente. Não há cache de imagens nem de módulos Go: cada execução baixa tudo, como um clone limpo.
- **Como foi verificado:** YAML validado por parsing; os três passos (`make test`, `make vet-go`, `git diff --exit-code`) foram rodados nesta ordem na máquina local e passaram, mas **com** `.env`, volume e imagens já existentes. O que o workflow existe para provar — que passa num runner limpo — só é verificado pela primeira execução no próprio PR.
- **Quem revisou:** pendente.

### 2026-10-11 — `make ingest` de ponta a ponta e idempotência (#24, #27)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/cmd/persist/`, `src/ingestor/internal/oltp/oltp.go`, `src/ingestor/internal/dbtest/`, `docker-compose.yml` (serviço `persist`), `Makefile` (alvos `persist` e `ingest`), `README.md`
- **O que foi pedido:** fechar a #24 a partir do que já estava adiantado numa branch local da antiga #20: ligar `fetch` e a gravação num comando só, que possa rodar de novo sem duplicar.
- **O que foi aproveitado:** a implementação inteira. **Decidido pela IA**, a revisar pela squad: (1) em vez do `ON CONFLICT (id_dou, versao) DO NOTHING` sugerido na revisão do #23, a matéria é comparada com a **última** versão dela em tudo que é gravado (órgão, data, ementa e conteúdo) — igual, nada é gravado; diferente, entra a versão seguinte. Isso já entrega a #27 no mesmo código. (2) De duas entradas com o mesmo `id` no mesmo ZIP, **só a primeira é gravada** e a outra é contada como `repetida`: gravar as duas criava duas versões novas a cada execução. (3) O `make ingest` encadeia `fetch` e `persist`, sem passar pelo `make extract`, porque o `persist` já lê o ZIP com o mesmo pacote; e, se o `fetch` passa sem deixar ZIP, o dia é tratado como sem edição. (4) Um ZIP por execução e uma transação por ZIP. (5) O teste de "rodar duas vezes" é em Go, em transação desfeita, e não em shell como o `tests/db/test_carga.sh`, para não deixar no banco a matéria construída. Da revisão do #23 também entrou o conjunto de nomes já enfileirados, para não ir ao banco uma vez por matéria de órgão desconhecido.
- **Como foi verificado:** `make test` inteiro e `make vet-go`. Os testes gravam a mesma edição duas vezes e comparam `ato` e `orgao_alias` linha a linha, com `id` e `criado_em`; republicam a edição com o texto alterado e conferem a versão 2 ao lado da 1 intacta; e gravam um ZIP com o mesmo `id` em duas entradas de conteúdo diferente. Este último foi visto **falhando** com a deduplicação desligada (1 versão nova na primeira execução, 2 na segunda) e passando com ela. **Não** foi exercitado: o `make ingest` contra o INLABS nem o `persist` com commit de verdade sobre um ZIP real, por falta de credencial nesta máquina — o critério "três dias de DO1, duas vezes" continua aberto. Também não foi medido se um `id` se repete entre o DO1 e o DO1E do mesmo dia com conteúdo diferente; nesse caso a segunda execução ainda criaria versões.
- **Quem revisou:** pendente.

### 2026-10-11 — Revisão do PR #35 e ajustes no `make ingest` (#24, #27)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/oltp/oltp.go`, `src/ingestor/internal/oltp/oltp_test.go`, `src/ingestor/cmd/persist/main.go`, `Makefile` (alvos `persist` e `ingest`), `README.md`
- **O que foi pedido:** revisar o PR #35 e aplicar na própria branch os seis achados, porque o autor pediu ajuda para destravar a E2.
- **O que foi aproveitado:** os seis. (1) O `Save` passou a comparar a matéria com **todas** as versões, e não só com a última: o mesmo `id` vindo com dois textos (DO1 e DO1E, ou dois dias da janela de reprocessamento) gerava duas versões a cada execução. (2) O órgão saiu da comparação: ele vem da identidade (ADR 0004), e resolver um nome não é republicação. (3) `persist` depende do `.env`. (4) O código de saída `1` do `persist` com entrada ruim ficou documentado como "a edição foi gravada mesmo assim". (5) O `make ingest` grava o que o `fetch` baixou mesmo quando uma seção falha, e sai com erro no fim; sem falha e sem ZIP, o dia continua sendo "sem edição". (6) O README trocou "sem rede" por "sem acessar o INLABS", porque a primeira execução baixa os módulos Go.
- **Como foi verificado:** dois testes novos (`TestSaveDoesNotSwapBetweenTwoKnownVersions` e `TestSaveDoesNotVersionAChangeOfOrgan`) vistos falhando antes da correção (4 versões no lugar de 2; versão nova na troca de órgão) e passando depois; `make test-db-go`, `make test-go` e `make vet-go` verdes. O `make ingest` foi simulado nos dois caminhos com data futura, que o `fetch` recusa: sem ZIP, saiu com erro sem dizer "sem edição"; com um ZIP só com uma imagem no bronze, o `persist` rodou e o make saiu com erro no fim. Nada foi gravado no banco. **Não** foi rodado contra o INLABS, que estava em manutenção.
- **Quem revisou:** pendente — o Luis, no PR.

### 2026-10-11 — Registro do dia no bronze: sem edição, falhou, não buscado (#28)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/store/`, `src/ingestor/internal/inlabs/workflow.go` e testes, `src/ingestor/cmd/fetch/main.go` (texto de ajuda), `Makefile` (`extract`, `persist`, `ingest`), `README.md`
- **O que foi pedido:** registrar, por data e seção, o resultado de cada busca, para um dia sem edição deixar de ser igual a um dia que ninguém buscou. A primeira metade (o marcador de "sem edição") foi feita em 10/10, numa branch local da antiga #20; a segunda (o marcador de falha) em 11/10.
- **O que foi aproveitado:** a implementação inteira, ainda sem revisão da squad. **Decidido pelo Luis**, entre duas opções que a IA apresentou, e ainda a confirmar pela squad, como pede a issue: o registro é um **arquivo vazio no bronze** (`AAAA-MM-DD-DO1.sem-edicao`, `AAAA-MM-DD-DO1.falhou`), e não uma tabela no OLTP, para o `fetch` continuar sem falar com o banco; o custo aceito é que o registro não é consultável por SQL. **Decidido pela IA**, a revisar: há no máximo um arquivo por edição, e ele diz o que a última busca encontrou; o ZIP em disco vence os dois marcadores; a falha é registrada tanto quando o dia segue quanto quando ele é abortado; execução cancelada ou sem prazo não registra nada; falha ao gravar o marcador aborta o dia, como qualquer falha de disco; e "buscada de novo na próxima execução" quer dizer a próxima execução **daquele dia** — o `fetch` rebaixa o dia inteiro, e nada refaz sozinho um dia que falhou (isso fica para a janela de reprocessamento, #31). A mudança mexe no pacote `inlabs`, que é do Iago e também é o da #21.
- **Como foi verificado:** `make test` inteiro e `make vet-go`. Um teste roda o `FetchDay` contra um servidor de teste e um diretório de verdade nos três casos: seção que falha fica com `.falhou`, seção que não existe fica com `.sem-edicao`, dia não pedido não deixa nada; na execução seguinte a seção que falhava chega, e o `.falhou` dá lugar ao ZIP. O `make persist` e o `make extract` foram rodados à mão nos três estados (sai com 0 e avisa no dia sem edição; erro com mensagem própria no dia que falhou e no dia não buscado). Uma primeira versão da condição no `Makefile` saía com erro sem dizer o motivo no dia não buscado; foi reescrita antes de rodar. **Não** foi exercitado contra o INLABS: o `404` como "sem edição" continua sendo a classificação sem evidência que o PR #17 já apontava, e é dela que o marcador `.sem-edicao` depende.
- **Quem revisou:** pendente.


### 2026-10-11 — Revisão do PR #37 e ajustes no registro do dia (#28)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `Makefile` (`TEM_EDICAO`, `extract`, `persist`, `ingest`), `src/ingestor/internal/store/store.go`, `README.md`; merge da branch do #35 nesta
- **O que foi pedido:** revisar o PR #37 e aplicar na própria branch os achados.
- **O que foi aproveitado:** (1) A branch do #35 atualizada entrou nesta, e o conflito no `make ingest` foi resolvido mantendo a correção do #35: o que foi baixado é gravado mesmo com uma seção falha. A decisão de "sem edição", "falhou" e "não buscado" ficou com o `TEM_EDICAO`, dentro do `persist`. (2) O `TEM_EDICAO` passou a olhar os marcadores do DO1 **e** do DO1E: a falha de qualquer seção é avisada e vira erro, inclusive quando a outra seção foi baixada ou não teve edição. (4) O `store` apaga o marcador antigo antes de gravar o novo: uma queda no meio deixa nenhum marcador, nunca dois que se contradizem. (5) O README ganhou o exemplo que faltava depois de "Para vários dias:". **Não aplicado:** (3) conferir o que o INLABS devolve em manutenção e para uma data sem edição, porque o INLABS estava em manutenção e não havia credencial; no lugar, o README avisa que o `.sem-edicao` vem de um `404` ainda não conferido.
- **Como foi verificado:** `make vet-go`, `make test-go` (8 pacotes) e `make test-db-go` verdes. O `make persist` foi rodado com marcadores e ZIPs de teste em datas fictícias, em quatro casos: as duas seções sem edição (sai com 0), DO1 sem edição e DO1E falho (erro), DO1 baixado e DO1E falho (grava o DO1 e sai com erro) e dia não buscado (erro). Os arquivos de teste foram apagados, e o ZIP de teste só tinha uma imagem, então nada foi gravado no banco.
- **Quem revisou:** pendente — o Luis, no PR.

### 2026-10-12 — Ingestão mensal pelos dados abertos da Imprensa Nacional (#42)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/dadosabertos/` (pacote e testes), `src/ingestor/cmd/fetch-mensal/main.go`, `src/ingestor/internal/store/store.go` (`Has`) e teste, `src/ingestor/internal/config/config.go`, `src/ingestor/cmd/persist/main_test.go`, `docker-compose.yml` (serviço `fetch-mensal`), `Makefile` (`fetch-mensal`, `persist-mensal`, `ingest-mensal`), `README.md`
- **O que foi pedido:** uma fonte de ingestão automática para a E2 que não dependa do login do INLABS, que recusa clientes que não são navegador (502 no `logar.php`, inclusive com o script oficial e com a credencial correta). A IA investigou a alternativa, criou a issue #42 a pedido e implementou.
- **O que foi aproveitado:** a investigação e a implementação inteira, ainda sem revisão da squad. **Achados da investigação:** a Imprensa Nacional publica em dados abertos (CC0, sem login) um ZIP por mês e por seção; a API do dados.gov.br exige chave (401), mas a página `in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano=&mes=` lista os links de cada mês; o site responde 403 a pedido sem `Accept` e 200 com `Accept: */*`, mantendo o nosso User-Agent — não é imitação de navegador. **Decidido pela IA**, a revisar: só a Seção 1; o ZIP fica com o nome publicado (`S01MMAAAA.zip`) em `data/bronze/dados-abertos/`; mês já em disco não é pedido de novo (o arquivo de um mês fechado não muda); só aceita link para o próprio host da página; sem marcador de falha no bronze, porque o mês não tem o caso "sem edição" e uma falha não deixa nada sob o nome do ZIP.
- **Como foi verificado:** com a autorização da Luiza, a amostra `S01082026.zip` (52,6 MB) foi lida pelo `extract` atual sem nenhuma mudança: 8.590 matérias, 0 falhas, 120 imagens ignoradas, DO1 e DO1E, 24 dias de publicação, nenhum `id` repetido. Sete testes novos com `httptest` (link encontrado, mês em disco sem requisição, mês não publicado, download com erro, página no lugar do ZIP, link para outro host, formato do mês) e um no `store`; `make test-go` e `make vet-go` verdes. O `make fetch-mensal` foi rodado de verdade: `MES=2026-08` baixou o ZIP idêntico à amostra em ~9 s, a segunda execução não fez requisição, `MES=2026-09` saiu com "mês ainda não publicado" sem gravar nada, e `MES=2026-9` foi recusado. Num banco limpo (`make reset`), o `make ingest-mensal MES=2026-08` gravou 96 atos de conselho e pôs 8.494 matérias de órgão desconhecido na fila, com 0 falhas; a segunda gravação deu `gravadas=0 inalteradas=96`, e uma foto de `ato`, `orgao_alias` e `classificacao` (contagem e md5 das linhas: 96, 751 e 215) saiu idêntica antes e depois. O `make test` inteiro passou com o banco cheio de agosto, depois de uma correção: o `TestPersistSavesTheEdition` esperava que o órgão desconhecido do teste (uma coordenação da Polícia Federal) entrasse na fila, mas agosto já o tinha posto lá; o teste passou a esperar +1 ou +2 linhas conforme o órgão já esteja na fila.
- **Quem revisou:** pendente.

### 2026-10-12 — Diário da semana 10 completado e conflito do PR #36 (#26)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `docs/diario/2026-10-13.md`, `AI-USAGE.md` (conflito com o `main`)
- **O que foi pedido:** fechar o PR #36: resolver o conflito no `AI-USAGE.md` que o Iago apontou e acrescentar ao diário da semana 10, escrito em 11/10, o que aconteceu até 12/10.
- **O que foi aproveitado:** o conflito foi resolvido mantendo as entradas dos dois lados, em ordem de data. No diário entraram os PRs #35, #38, #41 e #43 com as datas de merge, o login automático do INLABS recusado, a troca da fonte automática para os dados abertos, os números de agosto e a prova de idempotência; o que estava "em revisão" passou para o que foi mergeado (a comparação com todas as versões, sem o órgão); e da lista "em aberto" saíram o registro do dia (decidido no #41) e o `id` repetido entre DO1 e DO1E (0 em agosto). O texto da semana 8 e da semana 9 não foi mexido.
- **Como foi verificado:** datas, tamanhos e estados dos PRs e issues tirados da API do GitHub em 12/10; os números de agosto são os das execuções registradas no PR #43; o histórico desde 2002 foi conferido na página da base de dados (janeiro de 2002, 2003, 2004 e 2020 listam os três ZIPs), sem baixar os arquivos; build do site sem link quebrado.
- **Quem revisou:** pendente — a Luiza, antes do push.

### 2026-10-11 — Pendências da revisão do PR #23: chave Go × Python e nomes à espera de decisão

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `src/ingestor/internal/oltp/` (`key.go`, `oltp.go`, testes, `testdata/chaves.tsv`), `tests/conselhos/test_conselhos.py`, `README.md`
- **O que foi pedido:** resolver os pontos que a revisão do PR #23 deixou "para registrar" e que não viraram issue.
- **O que foi aproveitado:** duas mudanças. (1) **Paridade da chave.** Um arquivo com 169 pares de nome e chave, gerado pela `chave()` do Python: os 153 nomes de `orgao_nome` e dos aliases da planilha que estão no banco, mais 16 feitos para separar as duas linguagens. O teste em Go e um teste novo em Python leem o mesmo arquivo. Nos 153 nomes reais as duas chaves já batiam; divergiam em 2 dos 16 construídos, exatamente a diferença que a revisão apontava: o Go removia a categoria `Mn` e o Python remove classe de combinação diferente de zero. O Go passou a usar a classe de combinação. (2) **Nome já à espera de decisão.** O `Writer` passa a ler também os aliases sem órgão, de qualquer fonte, e não enfileira de novo um nome cuja chave já está lá. **Decidido pela IA**, a revisar: nesse caso a matéria continua fora de `ato` e **nenhuma** linha nova é gravada, em vez de uma linha `DOU` copiando o status da planilha; e a comparação é pela chave, não pelo nome, então duas grafias do DOU com a mesma chave passam a dar uma linha só. O terceiro ponto da revisão, o ADR 0001 dizer que o DOU não entra no OLTP, é da #32 e não foi tocado.
- **Como foi verificado:** `make test` inteiro e `make vet-go`. O teste de paridade em Go foi visto **falhando** nos dois casos construídos antes da correção e passando depois; o teste do nome à espera foi visto falhando com a leitura dos pendentes desligada (2 linhas em vez de 1). **Não** foi verificado em dado real: não se sabe se algum dos 5 nomes pendentes da planilha aparece de fato no DOU, e os dois caracteres em que as chaves divergiam não ocorrem em nenhum nome do banco — a correção é de consistência, sem efeito nos dados de hoje.
- **Quem revisou:** pendente.

### 2026-10-12 — PR #40 trazido para o `main` (revisão do #23)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** merge do `main` na branch `fix/pendencias-revisao-23`; `AI-USAGE.md` (conflito)
- **O que foi pedido:** destravar o PR #40, que apontava para a branch do #35, já mergeada, e tinha conflito em sete arquivos.
- **O que foi aproveitado:** os conflitos vinham de o #40 estar empilhado sobre a versão do #35 anterior à revisão, que entrou no `main` modificada pelo squash. Em vez de resolver arquivo por arquivo, o que arriscava trazer de volta código já revisado, a árvore partiu do `main` e recebeu só o commit próprio do #40 (`50eb7d4`); o resultado entrou como merge, sem reescrever a branch. A diferença contra o `main` ficou nos mesmos 8 arquivos do PR. Só o `AI-USAGE.md` conflitou, e as entradas dos dois lados ficaram. O código do #40 não foi alterado.
- **Como foi verificado:** `make vet-go` e `make test` inteiro verdes, com o banco cheio de agosto de 2026. O `make persist-mensal MES=2026-08` rodado com o código do #40 deu `gravadas=0 inalteradas=96`, e `orgao_alias` saiu idêntico (751 linhas, mesmo md5): a mudança não altera o que já estava no banco.
- **Quem revisou:** pendente — a Luiza, no PR.

### 2026-10-11 — Janela de reprocessamento no `make ingest` (#31, metade do OLTP)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `Makefile` (`ingest`, `ingest-dia`, `janela`), `tests/ingest/test_janela.sh`, `src/ingestor/cmd/persist/main_test.go`, `README.md`
- **O que foi pedido:** adiantar a #31 no que não depende da tabela Delta (#25).
- **O que foi aproveitado:** a implementação inteira, ainda sem revisão da squad. **Decidido pela IA**, a revisar: a janela mora no `Makefile`, como um laço sobre o `fetch` e o `persist` de um dia, porque o comando Go baixa uma data por execução por decisão do PR #17; a conta de datas roda em Python, num container sem rede, porque o `date` do Linux e o do macOS não fazem aritmética do mesmo jeito; um dia que falha não impede os seguintes; e o `make ingest-dia` preserva o comportamento de um dia só. **O valor de N não foi decidido:** o padrão `JANELA=7` é provisório, escolhido pela IA sem medição (cobre fim de semana e feriado emendado), e a issue pede que a squad decida.
- **Como foi verificado:** `make test` inteiro e `make vet-go`. O teste novo em shell confere os dias da janela (padrão, um dia só, virada de mês, 29 de fevereiro) e a recusa de `JANELA=0`, de `JANELA` que não é número e de `DATA` malformada. O teste novo em Go grava uma edição, grava de novo com uma matéria a mais e confere que só ela entra, com a `data_publicacao` do dia da edição. O laço do `make ingest` foi rodado com o `make` de dentro trocado por um substituto que falha num dos dias: os três dias foram tentados em ordem, o que falhou foi nomeado e o `make` saiu com erro. **Não** foi exercitado: o `make ingest` com janela contra o INLABS, por falta de credencial — nem o tempo nem o tamanho de sete dias de download foram medidos. A parte da issue que pede o ato atrasado na partição certa do Delta depende da #25 e não foi feita.
- **Quem revisou:** pendente.


### 2026-10-12 — PR #39 trazido para o `main` (janela de reprocessamento, #31)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** merge do `main` na branch `feature/issue-31-janela`; `Makefile` (`ingest`, `ingest-dia`), `README.md` (seção "Dado atrasado"), `AI-USAGE.md`
- **O que foi pedido:** destravar o PR #39, que apontava para a branch do #37, já mergeada, e conflitava com o `ingest-mensal` do #43.
- **O que foi aproveitado:** como no #40, a árvore partiu do `main` e recebeu só o commit próprio do #39 (`df574ef`), como merge, sem reescrever a branch. Três conflitos foram resolvidos à mão. (1) No `Makefile`, o `ingest` com janela e o `ingest-dia` do #39 ficaram, mas o corpo do `ingest-dia` é o do `main`: o #39 foi escrito antes da revisão do #35 e parava o dia no primeiro passo que falhasse, o que desfaria a correção de gravar o que foi baixado quando uma seção falha. (2) No README, o texto do #39 foi ajustado para esse comportamento e ganhou um item: a janela é de dias do INLABS, cujo login automático é recusado (#42), e na fonte mensal não há janela. (3) No `AI-USAGE.md`, as entradas dos dois lados ficaram. O valor de N continua o provisório do #39 (7), à espera da squad.
- **Como foi verificado:** `make vet-go` e `make test` inteiro verdes, com o banco cheio de agosto de 2026, incluindo os 7 casos do `tests/ingest/test_janela.sh` e o `TestPersistTakesAMateriaThatArrivedLate`; `make -n ingest` confere que cada dia da janela chama o `ingest-dia`. **Não** foi exercitado: o `make ingest` com janela contra o INLABS, cujo login automático é recusado.
- **Quem revisou:** pendente — a Luiza, no PR.

### 2026-10-13 — Proposta de bases de enriquecimento para a E3

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `site/jornada-do-dado.md` (seção "Enriquecer com outras bases" e um nó no diagrama), `docs/adr/README.md` (decisão em aberto nº 6)
- **O que foi pedido:** levantar quais bases poderiam enriquecer o modelo analítico da E3 e registrar a proposta na documentação.
- **O que foi aproveitado:** a proposta de três bases, por ordem de retorno — o cadastro de órgãos (SIORG), uma tabela de marcos legais e de governo e o Brasil Participativo — registrada como **decisão em aberto da squad**, e não como decisão tomada. O que já estava no repositório veio dele: o uso parcial do SIORG (68 dos 82 conselhos com código e 28 das 125 grafias sem casamento, ADR 0004) e a citação do Brasil Participativo no README e no ADR 0001. **Sugestões da IA, sem verificação:** o Decreto nº 9.759/2019 como exemplo de marco, e a avaliação de que o Brasil Participativo é a base de maior risco; ninguém conferiu se ele tem API, nem a cobertura e o histórico.
- **Como foi verificado:** os requisitos da E3 foram lidos na página da disciplina em 13/10 (fato e dimensão, dimensão de variação lenta); os números do SIORG conferidos no ADR 0004; build do site sem link quebrado.
- **Quem revisou:** pendente — a Luiza, no PR.

### 2026-10-13 — Página "Entrega E2" no site (#33)

- **Ferramenta:** Claude Code (Claude Opus 5.5)
- **Onde:** `site/entrega-e2.md` (nova), `site/.vitepress/config.mts` (rota, menu e barra lateral)
- **O que foi pedido:** uma aba da E2 no site, no formato da página da E1.
- **O que foi aproveitado:** a página inteira, com os 8 itens do checklist da E2 na ordem da página da disciplina, o bloco "conferir em máquina limpa" e o link da evidência de cada item. Os itens que ainda não estão no `main` aparecem marcados como pendentes, com a issue, em vez de afirmar o que não existe. Atualizada no fim do dia, depois dos merges do #48 (Delta, compressão) e do #49 (CDC): os itens 2, 3 e 6 viraram evidência com os números dos ADRs 0006 e 0007; ficam pendentes a demonstração forçada da semântica (#30), o ADR da ingestão (#32) e a demonstração do dado atrasado no Delta (#31).
- **Como foi verificado:** os números da ingestão de agosto são os das execuções registradas no PR #43; build do site sem link quebrado; no servidor local, todas as páginas linkadas abriram e as três âncoras da "Visão geral" existem.
- **Quem revisou:** pendente — a Luiza, no PR.

### 2026-10-13 — Plano de migração do ingestor Go para Python (proposta para a E3)

- **Ferramenta:** Claude Code (Claude Opus 5.5 e Fable 5.1; agente de planejamento em segundo plano)
- **Onde:** `docs/planos/2026-10-13-migracao-ingestor-go-para-python.md`
- **O que foi pedido:** a Luiza quer o pipeline todo em Python; pediu um plano de migração do módulo Go (`src/ingestor/`) para discutir com a squad depois da E2.
- **O que foi aproveitado:** o plano inteiro, como **proposta não decidida**: inventário pacote a pacote com o equivalente Python (stdlib + `psycopg`, que o lake já usa), cinco fatias (infra → `fetch-mensal` → `extract` → `persist` → descarte do cliente INLABS com ADR → ADR 0008), prova de equivalência por fatia sobre `S01082026.zip` (fotos de `ato` e `orgao_alias` e prova cruzada: o Python relendo o que o Go gravou tem de dar `inalteradas=96`), ~43 h de esforço e riscos (paridade da chave Unicode, desempenho do `HTMLParser`, cobertura dos 112 testes Go). **Recomendação do agente, a decidir pela squad:** não portar o cliente INLABS, cujo login é recusado a scripts, e sim descontinuá-lo com ADR.
- **Como foi verificado:** o agente só leu o repositório (sem editar nem rodar nada no banco); os números citados (8.590 matérias, 96 atos, 751 aliases, contagem de testes Go) batem com o `AI-USAGE.md` de 12/10 e com `go test`. Não foi verificado por execução: nenhuma fatia foi implementada.
- **Quem revisou:** pendente — a Luiza e a squad; o Go é do Iago e do Luis, e a decisão não é só dela.

### 2026-10-13 — Camada analítica em Delta Lake (#25, ADR 0006)

- **Ferramenta:** Gemini for Developers
- **Onde:** `docs/adr/0006-...md`, `docs/adr/README.md`, `src/lake/`, `docker-compose.yml`, `Makefile`, `tests/lake/test_lake.sh`, `README.md`
- **O que foi pedido:** estruturar a ADR da camada analítica (Delta Lake, particionamento anual e idempotência por merge) e implementar o módulo Python `src/lake` com o serviço no compose e alvo no Makefile.
- **O que foi aproveitado:** a estrutura da ADR 0006, a query de consolidação com os nomes históricos e tipologia vigente, a lógica de merge no `sync.py` com `deltalake`, compressão ZSTD, medições comparativas reais, o serviço `lake` e o alvo `make lake`.
- **Como foi verificado:** conferido que a extração preserva os 215 atos da planilha; executado `make lake` duas vezes comprovando idempotência (0 inserções na segunda); teste analítico com DuckDB rodando contra `data/silver/atos/`; suíte `make test` completa passando.
- **Quem revisou:** Gabriel Moura e pendente (quem revisar o PR)

### 2026-10-13 — Migração 0: pacote `src/dou/`, serviços e alvos de teste em Python (#52)

- **Ferramenta:** Claude Code (Claude Fable 5.1)
- **Onde:** `src/dou/` (`__init__.py`, `__main__.py`, `requirements.txt`), `tests/dou/` e `tests/dou_db/` (fumaça e o apoio `dbtest.py`), `docker-compose.yml` (serviços `dou` e `dou-db-test`), `Makefile` (`test-py-dou`, `test-db-py`, os dois dentro do `make test`), `README.md`
- **O que foi pedido:** a primeira fatia da migração Go → Python decidida na #51: a infra para as fatias seguintes, sem comportamento novo e sem tocar no Go.
- **O que foi aproveitado:** tudo. **Decidido pela IA**, a revisar: o `python -m dou` tem um registro de subcomandos (`SUBCOMANDOS`) que as fatias preenchem, e sem nenhum sai com 2 e lista "nenhum ainda"; os testes sem banco rodam no serviço `carga` (sem rede), como os da planilha; os com banco rodam num serviço próprio, cada teste numa transação desfeita (`dbtest.CasoComBanco`, o par do `internal/dbtest` do Go), e são pulados — não falham — sem `PGHOST`; o `pip` instala em `--target /tmp/site` para rodar como o usuário do host sem gravar em `/usr/local`.
- **Como foi verificado:** `make test` inteiro verde (o Go intacto: 11 pacotes `ok`; mais 3 testes de fumaça do CLI e 1 do banco, que grava um revisor e confere que o rollback o apaga); `docker compose config` válido; `python -m dou` sem argumento sai com 2, `--help` com 0, subcomando desconhecido com 2.
- **Quem revisou:** pendente — a Luiza, no PR.
