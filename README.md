# Conselhos Vivos

> Quais conselhos nacionais de participação social ainda estão funcionando?

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
| Planilhas da pesquisadora | 2.638 atos já classificados à mão — nosso *ground truth* | Cedidas pela pesquisadora |
| [Brasil Participativo](https://brasilparticipativo.presidencia.gov.br/) | Composição, agenda e reuniões de cada conselho | Público (Decidim) |
| Cadastro de órgãos (SIORG / decretos) | O censo de conselhos existentes — o denominador | Público |

> **Por que o censo não pode sair do DOU:** o DOU só mostra quem publicou. Conselho que não publica há dois anos é precisamente o que queremos detectar. Se o denominador vier do DOU, o conselho morto some da conta e o indicador mente. **A ausência de publicação é o dado mais importante deste projeto.**

## Como rodar

Pré-requisitos: Docker com Compose v2 (`docker compose version`) e `make`.

```bash
make setup     # cria o .env a partir do .env.example (se faltar) e sobe tudo
```

Depois, preencha as credenciais do INLABS no `.env`. Sem `make`, o equivalente é `cp .env.example .env && docker compose up -d --wait`.

Isso sobe:

| Serviço | Onde | Para quê |
|---|---|---|
| `db` — PostgreSQL 16 | `localhost:5432` (host) · `db:5432` (entre containers) | o OLTP de curadoria |
| `adminer` | <http://localhost:8080> | explorar o banco pelo navegador — servidor `db`, credenciais do `.env` |

Os dados ficam no volume `pgdata` e sobrevivem a `docker compose down`.

```bash
make test      # teste de fumaça: sobe healthy e persiste entre down/up
make psql      # abre o psql dentro do container
make down      # para, mantém os dados
make reset     # APAGA o banco e sobe do zero
make           # lista todos os comandos
```

> **Porta 5432 ocupada?** Se você já tem um Postgres instalado na máquina, o `up` falha com `port is already allocated`. Troque `POSTGRES_PORT` no seu `.env` (ex.: `5433`) — só no `.env`, não no `.env.example`.

## Estrutura

```
sql/            DDL versionado do banco
src/            ingestão, parsing e transformações
docs/adr/       decisões de arquitetura (o porquê de cada escolha)
docs/diario/    registro semanal do andamento
data/           dados locais (não versionados)
tests/          testes do pipeline
```

## Decisões de arquitetura

As decisões relevantes ficam registradas em [`docs/adr/`](docs/adr/), com contexto, alternativas consideradas e consequências aceitas. Se você quer entender *por que* o projeto é assim, comece por ali.

## Créditos

Bancos de dados de produção decisória: SERAFIM, Lizandra e colaboradores (UFPB / Cebrap, 2020–2026).

Tipologia de análise: GURZA LAVALLE, A.; VOIGT, J.; SERAFIM, L. *O que fazem os conselhos e quando o fazem?* Dados, v. 59, n. 3, 2016 — adaptada por GURZA LAVALLE, A.; GUICHENEY, H.; VELLO, B.; RODRIGUES, F. (CEM, 2018).

Referência arquitetural: [GovHub BR](https://gov-hub.io/).

---

Projeto da disciplina de Banco de Dados 2 — FCTE / UnB, 2026/2.
