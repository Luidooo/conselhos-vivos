# Registros de Decisão de Arquitetura (ADR)

Cada decisão relevante de dados vira um arquivo aqui, numerado em ordem.

Formato: `NNNN-titulo-no-imperativo.md` — ex.: `0001-adotar-postgres-como-banco-principal.md`

## Decisões em aberto

Levantadas na fase de entendimento do domínio, ainda sem ADR escrito:

| # | Decisão | Por que trava as outras |
|---|---|---|
| 2 | De onde vem o censo de conselhos | Sem denominador independente do DOU, o indicador de silêncio não fecha |
| 3 | Como classificar a tipologia automaticamente — regras, classificador clássico ou LLM local | É o valor científico do projeto; temos 215 exemplos rotulados para medir |
| 4 | Onde mora a camada analítica — **tomada:** silver em Delta ([ADR 0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md)) e gold no DuckDB pelo dbt ([ADR 0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md)) | A squad confirma no ADR 0009 |
| 5 | Formato da camada de consumo — **tomada na E3:** um painel em Streamlit que lê só a gold ([ADR 0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md)); as abas Revisar e Perguntar ficam para a E4 e o produto | A squad confirma no ADR 0009 |
| 6 | Quais bases enriquecem o modelo analítico — **na E3, as menções de outros órgãos no próprio DOU**, automáticas no job mensal; SIORG completo, Seção 2, Brasil Participativo e IBGE avaliados e deixados para depois ([ADR 0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md)) | A squad confirma no ADR 0009 |

## Índice

| # | Decisão | Status |
|---|---|---|
| [0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md) | O OLTP do projeto é o sistema de curadoria, com classificação insert-only | proposto |
| [0002](0002-manter-postgresql-como-motor-do-oltp.md) | O OLTP de curadoria continua em PostgreSQL 16 | proposto |
| [0003](0003-carregar-a-planilha-como-rotulo-da-curadoria.md) | A planilha da pesquisadora entra no OLTP como rótulo da curadoria, lida só com a biblioteca padrão | proposto |
| [0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md) | A identidade de um conselho sai de uma chave normalizada mais decisões registradas, nunca de similaridade de texto | proposto |
| [0005](0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc.md) | Ingerir atos de conselho do DOU no OLTP e propagar ao Delta Lake por CDC lógico | proposto |
| [0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md) | Armazenar a camada analítica em tabelas Delta particionadas por ano e comprimidas com zstd | proposto |
| [0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md) | Propagar mudanças do OLTP ao Delta por slot de replicação lógica, sem Kafka | proposto |
| [0008](0008-unificar-o-pipeline-em-python.md) | Unificar o pipeline em Python e descontinuar o cliente do INLABS sem portar | aceito |
| [0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md) | Modelar a gold em estrela com dbt sobre DuckDB e orquestrar com Dagster | proposto |
| [0010](0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome.md) | É conselho todo órgão que já teve um nome começando com "Conselho", menos uma lista curta de exclusões; a marca de participação social fica à parte | proposto |
