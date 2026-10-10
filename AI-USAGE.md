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
