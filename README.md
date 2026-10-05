# Conselhos Vivos

> Quais conselhos nacionais de participação social ainda estão funcionando?

**Documentação:** <https://luidooo.github.io/conselhos-vivos/> — decisões, medições, relatórios de carga e o checklist da E1, num só lugar.

Os conselhos nacionais — CONAMA, CNAS, ConCidades, CONDRAF, CNPIR e dezenas de outros — são órgãos paritários onde sociedade civil e governo decidem juntos sobre política pública. Eles são **autogeridos**: se ninguém convoca a reunião, o conselho simplesmente para de funcionar. Não é extinto, não é noticiado, não aparece em lugar nenhum. Ele só silencia.

Este projeto constrói a plataforma de dados que detecta esse silêncio — lendo o Diário Oficial da União, identificando quem publicou o quê, classificando o tipo de decisão e publicando um indicador de vitalidade por conselho.

## O problema

A professora Lizandra Serafim (UFPB) pesquisa a produção decisória desses conselhos desde 2003. O método é ler o DOU ato por ato, anotar autor e tema, e classificar cada decisão numa tipologia de cinco categorias.

Tudo à mão. Em vinte anos de trabalho, cobriu **cinco conselhos**. Existem entre oitenta e cem.

## A tipologia

Cada ato é classificado em uma destas categorias — é o que o pipeline precisa aprender a fazer:

| Sigla  | Significado |
|--------|-------------|
| `DEF`  | Define a política — diretrizes, regulação, orçamento. Ato vinculante, antes da execução. |
| `FISC` | Fiscaliza — aprova ou reprova contas, responsabiliza, aplica sanção. |
| `GEST` | Gestão administrativa da política já definida. |
| `AUTO` | Autorregulação — o conselho falando de si mesmo: regimento, eleições internas, grupos de trabalho. |
| `IP`   | Gere outras instâncias participativas — conferências, eleições, comissões setoriais. |

Um conselho que só produz `AUTO` está se auto-administrando, não incidindo em política pública. **A distribuição da tipologia ao longo do tempo já é, sozinha, uma medida de saúde.**

## Fontes de dados

| Fonte | O que traz | Acesso |
|---|---|---|
| [INLABS / Imprensa Nacional](https://inlabs.in.gov.br/) | Edições completas do DOU em XML, desde 01/01/2020 | Gratuito, exige cadastro |
| Planilhas da pesquisadora | 215 atos já classificados à mão, 2003–2020 — nosso *ground truth* | Pública; cópia versionada em `data/raw/` |
| [Brasil Participativo](https://brasilparticipativo.presidencia.gov.br/) | Composição, agenda e reuniões de cada conselho | Público (Decidim) |
| Cadastro de órgãos (SIORG / decretos) | O censo de conselhos existentes — o denominador | Público |

> **Por que o censo não pode sair do DOU:** o DOU só mostra quem publicou. Conselho que não publica há dois anos é precisamente o que queremos detectar. Se o denominador vier do DOU, o conselho morto some da conta e o indicador mente. **A ausência de publicação é o dado mais importante deste projeto.**

## Como rodar

Pré-requisitos: Docker com Compose v2 (`docker compose version`), `make` e `jq`.

```bash
make setup     # cria o .env (se faltar), sobe tudo, aplica as migrações de sql/ e carrega a planilha
```

Depois, preencha as credenciais do INLABS no `.env`. Sem `make`, o equivalente é `cp .env.example .env && docker compose up -d --wait && bash scripts/migrate.sh && bash scripts/carga.sh`.

Isso sobe:

| Serviço | Onde | Para quê |
|---|---|---|
| `db` — PostgreSQL 16 | `localhost:5432` (host) · `db:5432` (entre containers) | o OLTP de curadoria |
| `pgadmin` — pgAdmin 4 | <http://localhost:5050> | explorar o banco pelo navegador — abre sem login, com o servidor `conselhos-vivos (db)` já cadastrado e conectado |

Os dados ficam no volume `pgdata` e sobrevivem a `docker compose down`.

> **`db` ou `localhost`?** Dentro do compose (pgAdmin, ingestores) o banco é `db:5432`. Fora dele, no seu terminal ou no DBeaver, é `localhost:5432`. Dentro de um container, `localhost` é o próprio container.

```bash
make test      # testes: Go do ingestor, infra, esquema do OLTP, leitura da planilha, identidade dos conselhos e carga
make test-go   # só os testes do ingestor em Go, em container (sem rede, sem credencial)
make fetch     # baixa as edições do DOU de hoje em Brasília; DATA=AAAA-MM-DD para outro dia
make extract   # lê as matérias dos ZIPs já baixados de DATA e imprime uma por linha, em JSON
make migrate   # aplica as migrações de sql/ que ainda não rodaram
make carga     # carrega os conselhos e a planilha da pesquisadora (idempotente) e atualiza os relatórios
make siorg     # baixa o SIORG (precisa de rede) e atualiza o recorte em data/referencia/
make psql      # abre o psql dentro do container
make docs      # sobe o site de documentação em localhost:5173 (precisa de Node)
make down      # para, mantém os dados
make reset     # APAGA o banco, sobe do zero, migra e carrega a planilha
make pgadmin-reset  # recria o pgAdmin (se mudar POSTGRES_USER ou POSTGRES_DB)
make           # lista todos os comandos
```

> **Porta 5432 ocupada?** Se você já tem um Postgres instalado na máquina, o `up` falha com `port is already allocated`. Troque `POSTGRES_PORT` no seu `.env` (ex.: `5433`) — só no `.env`, não no `.env.example`.
>
> **Só na sua máquina.** O banco e o pgAdmin escutam apenas em `127.0.0.1`: ninguém na mesma rede (Wi-Fi da UnB, por exemplo) alcança. Não troque isso — o pgAdmin roda **sem login**.
>
> **Senha com `$`?** No `.env`, coloque o valor entre aspas simples (`INLABS_SENHA='a$b'`), senão o Compose tenta interpolar. A senha do Postgres não pode ter `:` nem `\` (formato do `pgpass` do pgAdmin).
>
> **Subiu a branch da #2 antes desta correção?** O esquema era criado pelo `initdb`, e o `make migrate` quebra com `relation "orgao" already exists`. Rode `make reset` uma vez (apaga o banco local, que ainda não tem dado real).

**Carga da planilha:** o `make carga` lê `data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx` no serviço `carga` do compose (só biblioteca padrão do Python, sem rede), grava os 215 atos e as classificações da pesquisadora, e reescreve [`docs/carga/relatorio-planilha.md`](docs/carga/relatorio-planilha.md): quantas linhas entraram, quantas foram descartadas e por quê. Rodar de novo não duplica nada nem muda o relatório. Os atos normalizados ficam em `data/interim/planilha/atos.csv`.

**Identidade dos conselhos:** antes dos atos, o `make carga` junta os 125 nomes da aba "Conselhos mapeados no DOU" em **82 órgãos** ([ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)). Nomes que só diferem em caixa, acento ou sigla se juntam sozinhos; o resto é decisão registrada em [`data/referencia/conselhos-decisoes.csv`](data/referencia/conselhos-decisoes.csv) (grafia, renomeação com o ato legal, nome, indefinido ou ambíguo), que abre em qualquer planilha. Para corrigir uma decisão, edite o CSV e rode `make carga`. O resultado, com a conta que chega a 82, está em [`docs/carga/relatorio-conselhos.md`](docs/carga/relatorio-conselhos.md).

**Migrações:** cada arquivo `sql/NNN_*.sql` roda uma vez, em ordem e em transação, e fica registrado em `schema_migrations`. Depois de mergeado no `main`, um arquivo de migração **não se edita**: mudança nova vira o próximo número.

## Baixar o DOU

O `make fetch` baixa do INLABS as edições da Seção 1 — `DO1` e a edição extra `DO1E` — de um dia, e grava os ZIPs em `data/bronze/inlabs/` (o `make fetch` cria o diretório; o comando Go, chamado direto, exige que ele exista). Precisa das credenciais do INLABS no `.env` (cadastro gratuito em <https://inlabs.in.gov.br/>).

```bash
make fetch                    # hoje, no horário de Brasília
make fetch DATA=2026-10-01    # um dia específico
```

Um arquivo só aparece com o nome final quando o conteúdo é um ZIP que abre: sessão expirada devolve a página de login.

**Não há retomada.** Cada execução baixa o dia de novo, sobrescrevendo o que estiver em disco. Para vários dias:

O código de saída diz o que aconteceu: `0` nada falhou, `1` a execução foi abortada ou alguma seção falhou, `2` erro de uso (`-date` ausente ou malformado). Uma data que o INLABS não pode ter — futura, ou anterior a 2020-01-01, que é desde quando ele serve — aborta a execução com `1` e nenhuma requisição: é regra do INLABS, e não do argumento.

## Ler as matérias

O `make extract` abre os ZIPs que o `make fetch` deixou em `data/bronze/inlabs/` para um dia (`DO1` e, se houver, `DO1E`) e imprime **uma matéria por linha, em JSON**, no stdout. Não fala com o banco nem com a rede, e não precisa de credencial.

```bash
make extract DATA=2026-10-01 > materias.jsonl   # o log e o resumo vão para o stderr
make extract DATA=2026-10-01 | jq -r '.artCategory[-1]' | sort | uniq -c | sort -rn   # quem mais publicou
```

Cada linha traz os atributos do `<article>` (`id`, `idMateria`, `artType`, `pubDate`, `pubName`, `numberPage`, `editionNumber`, `artClass`), os campos do `<body>` (`identifica`, `ementa`, `titulo`, `subTitulo`) e:

- **`artCategory` já partido na hierarquia**, do ministério para baixo. O último nível é o órgão que publicou — o conselho, quando é um. A resolução é só `split('/')`; casar o nome com um dos 82 conselhos é trabalho da persistência (#19).
- **`texto`, o `<Texto>` em texto puro:** um parágrafo por linha, entidades HTML decodificadas, células de tabela separadas por ` | `. O HTML como publicado sai com `HTML=1` (`make extract DATA=... HTML=1`) e é a fonte da verdade: as marcas `<p class="assina">` e `<p class="identifica">` só existem nele, e o texto puro é derivado dele sem perda de palavras.

Uma entrada que não é XML — a imagem de uma matéria — é ignorada e logada. Um XML que não lê como matéria (malformado, sem `id`, sem `pubDate`, sem `artCategory`) é logado com o nome do arquivo e o resto do ZIP segue; nesse caso o código de saída é `1`.

## Estrutura

```
sql/            DDL versionado do banco
src/            ingestão, parsing e transformações
docs/adr/       decisões de arquitetura (o porquê de cada escolha)
docs/diario/    registro semanal do andamento
docs/carga/     relatórios da carga (gerados pelo make carga, versionados)
data/           dados locais (não versionados), exceto a planilha em raw/ e referencia/
data/referencia/ decisões de identidade dos conselhos e recorte do SIORG (versionados)
tests/          testes do pipeline
site/           site de documentação (VitePress); as páginas são os .md do repositório
```

## Decisões de arquitetura

As decisões relevantes ficam registradas em [`docs/adr/`](docs/adr/), com contexto, alternativas consideradas e consequências aceitas. Se você quer entender *por que* o projeto é assim, comece por ali.

## Créditos

Bancos de dados de produção decisória: SERAFIM, Lizandra e colaboradores (UFPB / Cebrap, 2020–2026).

Tipologia de análise: GURZA LAVALLE, A.; VOIGT, J.; SERAFIM, L. *O que fazem os conselhos e quando o fazem?* Dados, v. 59, n. 3, 2016 — adaptada por GURZA LAVALLE, A.; GUICHENEY, H.; VELLO, B.; RODRIGUES, F. (CEM, 2018).

Referência arquitetural: [GovHub BR](https://gov-hub.io/).

---

Projeto da disciplina de Banco de Dados 2 — FCTE / UnB, 2026/2.
