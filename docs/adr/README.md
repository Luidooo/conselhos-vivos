# Registros de Decisão de Arquitetura (ADR)

Cada decisão relevante de dados vira um arquivo aqui, numerado em ordem.

Formato: `NNNN-titulo-no-imperativo.md` — ex.: `0001-adotar-postgres-como-banco-principal.md`

## Decisões em aberto

Levantadas na fase de entendimento do domínio, ainda sem ADR escrito:

| # | Decisão | Por que trava as outras |
|---|---|---|
| 2 | De onde vem o censo de conselhos | Sem denominador independente do DOU, o indicador de silêncio não fecha |
| 3 | Como classificar a tipologia automaticamente — regras, classificador clássico ou LLM local | É o valor científico do projeto; temos 215 exemplos rotulados para medir |
| 4 | Onde mora a camada analítica — Postgres+Parquet/DuckDB ou lakehouse completo | Critério de desempate é operacional: o que a pesquisadora consegue subir sozinha |
| 5 | Formato da camada de consumo | Define o que entregamos como produto final |

## Índice

| # | Decisão | Status |
|---|---|---|
| [0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md) | O OLTP do projeto é o sistema de curadoria, com classificação insert-only | proposto |
| [0002](0002-manter-postgresql-como-motor-do-oltp.md) | O OLTP de curadoria continua em PostgreSQL 16 | proposto |
| [0003](0003-carregar-a-planilha-como-rotulo-da-curadoria.md) | A planilha da pesquisadora entra no OLTP como rótulo da curadoria, lida só com a biblioteca padrão | proposto |
| [0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md) | A identidade de um conselho sai de uma chave normalizada mais decisões registradas, nunca de similaridade de texto | proposto |
