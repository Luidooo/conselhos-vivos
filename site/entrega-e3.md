---
title: Entrega E3
outline: [2, 3]
---

# Entrega E3 — camada analítica transformada, testada e orquestrada

A pergunta da E1 é **"Quais conselhos nacionais de participação social ainda estão funcionando?"**. A E3 a responde com uma gold em estrela, construída pelo dbt sobre o DuckDB, orquestrada pelo Dagster e lida por um painel em Streamlit. A decisão está no [ADR 0009](/docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster), e o escopo do que conta como conselho, no [ADR 0010](/docs/adr/0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome).

As provas estão em [`docs/adr/medicoes/0009-gold/`](https://github.com/Luidooo/conselhos-vivos/tree/main/docs/adr/medicoes/0009-gold), geradas por script ou pelos alvos do `Makefile`, com o DOU de julho a setembro de 2026 e os 215 atos da planilha.

::: tip Conferir em máquina limpa
```bash
git clone https://github.com/Luidooo/conselhos-vivos.git && cd conselhos-vivos
make setup                                  # .env, Postgres, migrações e a planilha
make test                                   # inclui os testes do orquestrador e do painel
make demo-backfill DE=2026-07 ATE=2026-09   # baixa e carrega três meses do DOU pelo Dagster
make gold                                   # a gold, com os testes do dbt
make demo-retry                             # para o Postgres por ~1 min e mostra o retry recuperando
make painel                                 # a resposta em http://127.0.0.1:8501
```
Pré-requisitos: Docker com Compose v2, `make` e `sqlite3`. O backfill baixa os ZIPs dos dados abertos (o de julho tem 555 MB).
:::

## Entregáveis

| O que | Onde está | Como conferir |
|---|---|---|
| **Modelo em estrela** com variação lenta | `dbt/models/marts/` · `dim_conselho`, `fct_ato`, `fct_conselho_mes` | `make gold`; grão declarado na descrição de cada modelo |
| **Resposta à pergunta** | `mart_vitalidade` · `make painel` | 26 ativos, 33 sem ato no período coberto, 59 conselhos |
| **Testes de dados** | `dbt/models/*/*.yml` · `dbt/tests/` | `make gold`: 77 de 77 em `PASS` |
| **Orquestração** com retry, backfill e agenda | `src/orquestracao/` · `dagster/dagster.yaml` | `make orquestrador`, `make demo-retry`, `make demo-backfill`, `make demo-falhas` |
| **Enriquecimento:** menções de outros órgãos | `src/mencoes/` · `fct_mencao` · asset `silver/mencoes` | `make mencoes`; 10 dos 33 conselhos sem ato próprio são citados por outros órgãos |
| **Freshness e SLA** | `freshness_vitalidade` · `dbt/tests/sla_vitalidade.sql` | o mês M até o dia 20 do mês M+1 |
| **Plano de execução** | `docs/adr/medicoes/0009-gold/explain*` | `bash docs/adr/medicoes/0009-gold/explain.sh` |
| **Linhagem e catálogo** | [Linhagem dos dados](/linhagem) · `make gold-docs` | do ZIP do DOU ao painel; o diagrama do dbt é gerado do `manifest.json`, e o catálogo do dbt sai publicado no site |
| **ADRs da E3** | [0009](/docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster) modelagem e ferramentas · [0010](/docs/adr/0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome) escopo · [0008](/docs/adr/0008-unificar-o-pipeline-em-python) pipeline em Python | medições em `docs/adr/medicoes/0009-gold/` |

## Checklist de aceite

Cada item do [checklist da E3](https://unb-bd2.github.io/PlanoEnsino/projeto/e3/), na ordem da página da disciplina.

| # | Item | Prova |
|---|---|---|
| 1 | Fato e dimensão, granularidade declarada, variação lenta | [dim_conselho-renomeados.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/dim_conselho-renomeados.txt) · [granularidade.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/granularidade.txt) |
| 2 | Transformações versionadas em dbt, em camadas | `dbt/models/staging/` → `dbt/models/marts/` |
| 3 | Testes de esquema, volume, unicidade, integridade referencial e distribuição | [teste-distribuicao-pega-o-mes.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/teste-distribuicao-pega-o-mes.txt) |
| 4 | Orquestração agendada com grafo, retry e backfill demonstrado | [grafo-dagster.jpg](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/grafo-dagster.jpg) · [retry](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/retry-2026-08-20261108T231400Z.txt) · [backfill](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/backfill-2026-07-a-2026-09-20261109T000430Z.txt) · [falhas](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/falhas-20261109T024652Z.txt) |
| 5 | Consulta otimizada pelo plano de execução, `EXPLAIN (ANALYZE, BUFFERS)` antes e depois | [resultado.md](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/resultado.md) |
| 6 | Freshness e SLA declarado | [sla-vitalidade-avisa.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/sla-vitalidade-avisa.txt) |
| 7 | ADR sobre modelagem ou ferramenta | [ADR 0009](/docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster) |
| 8 | Painel respondendo à pergunta da E1 | [painel.png](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/painel.png) · `make painel` |

## 1. Modelo analítico com fato, dimensão e variação lenta

- **`dim_conselho`, SCD tipo 2:** uma linha por nome que o conselho teve, com `valido_de` e `valido_ate`. Renomear é inserir, não sobrescrever. CNDPI, CNDM e CNDH aparecem com dois nomes e um só atual; são 62 linhas para 59 conselhos.
- **`fct_ato`:** uma linha por matéria publicada, na versão mais recente, ligada ao nome que o conselho tinha na data, pelo `asof join`. Um ato anterior ao primeiro nome fica com o mais antigo, marcado como aproximado.
- **`fct_conselho_mes`:** conselho × mês, **com zeros**. É o mês sem ato que responde à pergunta.
- **Granularidade medida:** 458 linhas na grão por matéria, 177 na mensal e 5.428 na diária hipotética, 30 vezes a mensal sem pergunta que a use.

**Enriquecimento: menções de outros órgãos.** Um terceiro fato, `fct_mencao`, guarda as matérias publicadas por **outro** órgão que têm o conselho como assunto: a homologação de um parecer, a renovação da composição, o regimento. A ingestão é automática, no mesmo job mensal. Ela é um segundo sinal de vida, mostrado ao lado da situação: dos 33 conselhos sem ato próprio no período, 10 são citados por outros órgãos ([mencoes-carga.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/mencoes-carga.txt)). O SIORG completo, a Seção 2 do DOU, o Brasil Participativo e o IBGE foram avaliados e ficaram para depois; o ADR 0009 diz por quê.

## 2. Transformações em dbt, em camadas

dbt-core com o adaptador do DuckDB. O staging, em views, lê a silver (`delta_scan`) e o OLTP (`ATTACH` só leitura). Os marts, em tabelas, montam a estrela. Tudo é versionado em `dbt/`, e `make gold` roda modelos e testes.

## 3. Testes de dados

- **Esquema:** `not_null`, `accepted_values` e tipologias.
- **Unicidade:** `unique` nas chaves e na dupla conselho × mês.
- **Integridade referencial:** `relationships` do fato para a dimensão.
- **Volume:** o fato tem o mesmo número de matérias do staging no escopo, e nunca menos que os 215 da planilha.
- **Distribuição:** nenhum mês coberto sem ato, e no máximo 20% fora da tipologia.
- **Unitários:** o nome da época, a vigência e o SLA na fronteira do dia 20.

Os testes pegam erro silencioso de verdade. Com agosto tirado da série, `distribuicao_mes_sem_nenhum_ato` falha apontando `2026-08-01`, e o `make gold` seguinte volta a passar. Cada teste novo foi conferido trocando o código pelo comportamento errado e vendo-o falhar.

## 4. Orquestração com grafo, retry e backfill

O Dagster roda um job mensal particionado: `atos_do_mes` → `silver/atos` → modelos do dbt.

- **Agenda:** todo dia do 15 ao 28, às 6h de Brasília. Ela pula o mês já carregado e tenta de novo o que ainda não saiu.
- **Retry:** com o Postgres parado de propósito, a primeira tentativa cai (`Name or service not known`), o `RetryPolicy` espera 30 s e recupera.
- **Backfill de três meses:** a primeira rodada grava julho e setembro; a segunda dá `gravadas=0` nos três.
- **Falhas separadas por tipo:** mês não publicado e ZIP inválido falham **sem** retry, porque repetir não resolve. Queda de rede e de banco usam o retry. Toda falha leva a causa real do processo, e a falha de um teste do dbt traz o nome do teste.
- **Um run por vez:** a silver (Delta) e a gold (DuckDB) não aguentam runs em paralelo.

## 5. Consulta otimizada pelo plano de execução

A consulta escolhida é a extração do lake (`QUERY_OLTP`), de que toda a camada analítica depende. O `EXPLAIN (ANALYZE, BUFFERS)` antes e depois está no repositório, gerado por script:

- o nó mais caro é o `Seq Scan` em `classificacao`, com 933 de 1.429 buffers (65%);
- o índice candidato em `orgao_nome` **não teve ganho** neste volume, e o planner nem o usa;
- forçado, o índice que já existe em `classificacao` é usado, mas o ganho fica no ruído.

Pelo critério da issue, índice sem ganho medido não entra. A conclusão vale para este volume; o backfill histórico pede medir de novo.

## 6. Freshness e SLA

**SLA:** o mês M está na gold até o dia 20 do mês M+1. A `freshness_vitalidade` é uma view, para o "hoje" valer na leitura. Ela expõe o último mês coberto, o mês esperado e o atraso. O teste `sla_vitalidade` **avisa sem travar o build**: com setembro tirado, ele dá `WARN 1` e o build termina com `ERROR=0`. Um DOU vazio conta como fora do SLA.

## 7. ADR sobre modelagem e ferramenta

O [ADR 0009](/docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster) compara estrela, one big table e Data Vault; dbt e SQLMesh; Dagster, Airflow e a **opção nula**, um cron com `make`, levada a sério: o ADR lista o que ela exigiria de código próprio para o retry, o backfill e a separação das falhas. Ele traz as medições acima e os gatilhos de revisão.

## 8. Painel respondendo à pergunta

`make painel` abre em `127.0.0.1:8501`, só na máquina local. O título é a pergunta, e a primeira linha é a resposta: quantos conselhos estão ativos, em silêncio ou sem ato no período coberto. Abaixo vêm:

- a situação de cada conselho, com a marca de participação social da pesquisadora e as menções de outros órgãos;
- as regras de negócio por extenso, num bloco "Como ler este painel";
- os atos por mês;
- o que cada conselho decide, por tipologia.

A página mostra o período coberto e o SLA. O painel abre a gold só para leitura e a fecha a cada carga, então o `make gold` passa com ele aberto.

## Limites conhecidos e pendências da squad

- **ADR 0010:** o escopo de 59 conselhos segue "proposto", à espera da aprovação da squad.
- **Regra da vitalidade:** o limite de 3 meses é provisório, à espera da pesquisadora. Com outubro na silver, a cobertura passa de 3 meses, e os conselhos sem ato viram "em silêncio".
- **Sem ato no DOU não prova que o conselho parou:** muito conselho funciona sem publicar no DOU. O painel diz isso ao lado dos números.
- **A silver e a gold são recalculadas inteiras a cada mês.** Vale enquanto o `dbt build` leva segundos; o ADR 0009 diz quando mudar.
