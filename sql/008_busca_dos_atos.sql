-- E4 (ADR 0012): a busca do RAG, pela busca textual do próprio Postgres, em português. O parser padrão ignora as
-- tags do HTML do DOU. A expressão é a mesma da consulta em src/painel/busca.py, para o índice ser usado.
CREATE INDEX ix_ato_busca ON ato USING GIN (to_tsvector('portuguese', coalesce(ementa, '') || ' ' || coalesce(conteudo, '')));

\getenv senha_perguntas APP_PERGUNTAS_PASSWORD
CREATE ROLE app_perguntas LOGIN PASSWORD :'senha_perguntas';

-- app_perguntas: a página Perguntar lê só o que a busca usa; nada de revisor, classificação ou alerta.
GRANT SELECT (id, origem, id_dou, versao, orgao_id, data_publicacao, ementa, conteudo) ON ato TO app_perguntas;
GRANT SELECT ON orgao_nome TO app_perguntas;
