-- Medição do ADR 0001: custo de ler a classificação vigente, insert-only × CRUD.
--
-- Uso (banco migrado, a partir da raiz do repositório):
--   docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v n=2638' \
--     < docs/adr/medicoes/0001-classificacao-vigente.sql
--
-- :n = número de atos. 2638 = carga inicial registrada no diário de 25/09; a recontagem
-- de 26/09 achou 215 atos na planilha. O valor fica para reproduzir a medição do ADR 0001.
-- Os atos e classificações são SINTÉTICOS no volume do domínio (a carga real é a #3).
-- Por ato: a pesquisadora classifica 1 a 3 vezes (reclassificações) e o pipeline 1 vez.
-- Tudo roda numa transação desfeita no fim: o banco não é alterado.

\set ON_ERROR_STOP on
\timing off
BEGIN;
SET LOCAL client_min_messages = warning;

INSERT INTO orgao DEFAULT VALUES;

INSERT INTO ato (origem, ref_legal, orgao_id, data_publicacao, ementa)
SELECT 'PLANILHA', 'Resolução ' || g || '/bench', currval('orgao_id_seq'),
       DATE '2003-01-01' + (g % 7000), 'ementa sintética ' || g
FROM generate_series(1, :n) g;

-- insert-only: 1..3 linhas da pesquisadora + 1 do pipeline por ato
INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id, criado_em)
SELECT a.id,
       (ARRAY['DEF','FISC','GEST','AUTO','IP'])[1 + (a.id + r) % 5],
       (SELECT id FROM revisor WHERE tipo = 'HUMANO' LIMIT 1),
       now() - make_interval(days => 10 - r)
FROM ato a CROSS JOIN LATERAL generate_series(1, 1 + (a.id % 3)::int) r
WHERE a.ref_legal LIKE '%/bench';

INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id, confianca)
SELECT a.id, (ARRAY['DEF','FISC','GEST','AUTO','IP'])[1 + a.id % 5],
       (SELECT id FROM revisor WHERE tipo = 'PIPELINE' LIMIT 1), 0.8
FROM ato a WHERE a.ref_legal LIKE '%/bench';

-- CRUD: mesma informação, só o estado atual (uma linha por ato × revisor)
CREATE TEMP TABLE classificacao_crud ON COMMIT DROP AS
SELECT ato_id, revisor_id, tipologia_sigla FROM classificacao_vigente;
ALTER TABLE classificacao_crud ADD PRIMARY KEY (ato_id, revisor_id);
ANALYZE classificacao; ANALYZE classificacao_crud; ANALYZE ato;

SELECT (SELECT count(*) FROM classificacao)      AS linhas_insert_only,
       (SELECT count(*) FROM classificacao_crud) AS linhas_crud;

\echo '== Q1 insert-only: vigente de UM ato (tela de curadoria)'
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON)
SELECT * FROM classificacao_vigente WHERE ato_id = (SELECT max(id) FROM ato);
\echo '== Q1 CRUD'
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON)
SELECT * FROM classificacao_crud WHERE ato_id = (SELECT max(id) FROM ato);

\echo '== Q2 insert-only: distribuição da tipologia vigente humana (indicador)'
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON)
SELECT v.tipologia_sigla, count(*) FROM classificacao_vigente v
JOIN revisor r ON r.id = v.revisor_id AND r.tipo = 'HUMANO' GROUP BY 1;
\echo '== Q2 CRUD'
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON)
SELECT c.tipologia_sigla, count(*) FROM classificacao_crud c
JOIN revisor r ON r.id = c.revisor_id AND r.tipo = 'HUMANO' GROUP BY 1;

\echo '== Q3 só existe no insert-only: atos em que a pesquisadora mudou de ideia'
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON)
SELECT ato_id FROM classificacao c JOIN revisor r ON r.id = c.revisor_id AND r.tipo = 'HUMANO'
GROUP BY ato_id HAVING count(DISTINCT tipologia_sigla) > 1;

ROLLBACK;
