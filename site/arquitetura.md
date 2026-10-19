---
title: Arquitetura final
outline: [2, 3]
---

# Arquitetura final

Este é o desenho que o projeto entrega ao fim da E4. Ele parte de uma regra: **a pesquisadora usa um app só**, com três abas, e não precisa saber o que roda por trás. Todo o resto existe para alimentar essas três abas e para cumprir o que a disciplina pede em cada entrega.

<ArquiteturaInterativa />

<p class="cv-legenda">Clique numa parte para ver o que ela faz, a ferramenta e o porquê, ou percorra o caminho do dado passo a passo. O mesmo desenho, estático, está em <a href="/conselhos-vivos/arquitetura-final.svg" target="_blank">arquitetura-final.svg</a>.</p>

## Como o dado anda

1. **Entrada.** Uma vez por mês, o ingestor em Python baixa o ZIP da Imprensa Nacional e grava cada ato no Postgres, com o texto e o link da publicação.
2. **Curadoria.** A tipologia e a identidade dos conselhos ficam no mesmo Postgres, sem nada ser sobrescrito ([ADR 0001](/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp)).
3. **Análise.** As mudanças vão por CDC para a silver em Delta. O dbt, rodando no DuckDB, monta a gold: fatos, dimensões com histórico e as métricas de vitalidade.
4. **Volta para quem decide.** As métricas viram alertas, gravados de volta no Postgres. É o ETL reverso: a pesquisadora vê o alerta na aba Revisar e reclassifica se precisar.
5. **Perguntas.** O texto dos atos é indexado pela busca textual do próprio Postgres, em português. A aba Perguntar acha os atos e pede a resposta à API do Claude, citando cada um.

O RAG lê só o Postgres. O lakehouse fica fora do caminho das perguntas, então uma falha na parte analítica não derruba o assistente.

## Ferramentas

| Parte | Ferramenta | Situação | Por que essa |
|---|---|---|---|
| Infra e comandos | Docker Compose + `make` | ✅ já tem | tudo sobe com um comando |
| Ingestão | Python (`src/dou`, biblioteca padrão + `psycopg`) | ✅ já tem | a migração do Go para Python |
| OLTP e curadoria | PostgreSQL 16 | ✅ já tem | [ADR 0002](/docs/adr/0002-manter-postgresql-como-motor-do-oltp) |
| CDC | slot de replicação lógica do Postgres | ✅ já tem | [ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica), sem Kafka |
| Silver | Delta Lake, pela biblioteca `deltalake` | ✅ já tem | [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta) |
| Motor analítico | DuckDB | ✅ já tem | lê o Delta direto, sem servidor |
| Gold e testes de dados | dbt-core + dbt-duckdb | 🆕 E3 | modelos em SQL versionados, com testes de esquema, unicidade e integridade |
| Camada semântica | métricas definidas no dbt | 🆕 E4 | uma definição só, usada pelo painel e pelos alertas |
| Orquestração | Dagster, com a opção nula cron + `make` | 🆕 E3 | partições mensais dão o backfill e o retry por configuração |
| ETL reverso | script Python, disparado pelo orquestrador | 🆕 E4 | lê a gold e grava os alertas no Postgres |
| Busca do RAG | busca textual do Postgres (`tsvector`, em português) | 🆕 | já vem no banco: sem extensão, sem modelo de embedding, sem conta a mais |
| Respostas do RAG | API do Claude, pelo SDK `anthropic` | 🆕 | escreve a resposta a partir dos trechos achados |
| App da pesquisadora | Streamlit | 🆕 | um app Python, com as três abas |
| Catálogo e linhagem | `dbt docs`, publicado no site | 🆕 E4 | o grafo vai da fonte até o painel e os alertas |
| Controle de acesso | papéis e `GRANT` do Postgres, com RLS se precisar | 🆕 E4 | o app só lê e escreve o que precisa |
| CI e documentação | GitHub Actions + VitePress | ✅ já tem | |

São quatro peças novas de verdade: dbt, Dagster, Streamlit e o SDK do Claude. O resto é configuração do que já existe.

### O que fica de fora, e por quê

- **Airflow.** Pede vários containers para um job por mês. O [diário de 25/09](/docs/diario/2026-09-25) registra a restrição do briefing: quem mantém isso rodando é a pesquisadora, então vale o mais simples de operar.
- **Kafka e Debezium.** O [ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica) trocou os dois pelo slot lógico.
- **Spark e Iceberg.** Não se justificam neste volume. O Delta já entregue cobre o formato aberto.
- **LangChain e LlamaIndex.** O RAG aqui é uma consulta SQL e uma chamada à API. Um framework esconderia isso e traria dependências.
- **Busca vetorial.** A API do Claude não gera embeddings, e vetores pediriam mais um modelo e mais uma conta. A busca textual do Postgres acha palavras, não sentido; o Claude pode reescrever a pergunta em termos de busca antes da consulta.

## Decisões em aberto

Cada uma vira um ADR, com a opção nula tratada a sério e medida.

- **Orquestrador.** Dagster cumpre retry e backfill por configuração, mas é mais um serviço. Com cron + `make`, os dois viram código nosso.
- **Camada semântica.** As métricas no próprio dbt ou uma tabela de métricas escrita à mão.

## O que cada entrega cobre

| Entrega | Exigência | Onde está no desenho |
|---|---|---|
| E1 ✅ | OLTP com integridade e decisões registradas | Postgres: atos e curadoria |
| E2 ✅ | ingestão em lote, CDC, formato aberto, dado atrasado | dados abertos, slot lógico, silver em Delta |
| E3 | fato, dimensões e SCD em camadas | gold no dbt |
| E3 | testes de dados | testes do dbt |
| E3 | orquestração com retry e backfill | orquestrador |
| E3 | `EXPLAIN` antes e depois, frescor e SLA | gold e índices do Postgres |
| E3 | painel | aba Painel |
| E4 | camada semântica | métricas no dbt |
| E4 | ETL reverso para quem age | alertas e aba Revisar |
| E4 | catálogo e linhagem da fonte ao consumo | `dbt docs` |
| E4 | LGPD e controle de acesso por linha e coluna | papéis do Postgres |
| Produto | a pesquisadora pergunta e confere a fonte | aba Perguntar, busca textual do Postgres, API do Claude |
