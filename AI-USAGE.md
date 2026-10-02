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
