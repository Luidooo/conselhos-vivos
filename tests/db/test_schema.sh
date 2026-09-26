#!/usr/bin/env bash
# Testes do esquema do OLTP de curadoria (issue #2).
# Pré-requisito: banco no ar e migrado (make migrate). Cada caso roda numa
# transação que nunca é confirmada, então o teste não deixa lixo no banco.
# Uso: bash tests/db/test_schema.sh   (a partir de qualquer diretório)
set -euo pipefail
cd "$(dirname "$0")/../.."

falhas=0
ok()    { echo "  ok    $1"; }
falha() { echo "  FALHA $1"; falhas=$((falhas + 1)); }

# Credenciais lidas dentro do container: o .env é formato do Compose, não de shell.
psql_db() {
  docker compose exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1" 2>&1
}

# Roda o SQL numa transação desfeita no fim e devolve a saída.
em_rollback() { psql_db "BEGIN; $1; ROLLBACK;"; }

# Passa se o SQL for aceito e imprimir exatamente o esperado.
espera_valor() {
  local nome=$1 esperado=$2 sql=$3 out
  if out=$(em_rollback "$sql") && [ "$out" = "$esperado" ]; then ok "$nome"
  else falha "$nome — esperava '$esperado', veio: $out"; fi
}

# Passa só se o SQL for recusado PELO motivo esperado (nome da restrição ou trecho da mensagem).
espera_erro() {
  local nome=$1 motivo=$2 sql=$3 out
  if out=$(em_rollback "$sql"); then falha "$nome — o banco aceitou"
  elif grep -q "$motivo" <<<"$out"; then ok "$nome"
  else falha "$nome — recusou por outro motivo: $out"; fi
}

# Um órgão, um ato do DOU e a pesquisadora (revisor do seed), prontos para cada caso.
BASE="INSERT INTO orgao DEFAULT VALUES;
INSERT INTO ato (origem, id_dou, orgao_id, data_publicacao, conteudo)
  VALUES ('DOU', 'TESTE-1', currval('orgao_id_seq'), '2021-01-01', 'texto');"
PESQUISADORA="(SELECT id FROM revisor WHERE email = 'curadoria@pesquisa.local')"

echo "estrutura"
espera_valor "7 tabelas + schema_migrations" "8" \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
espera_valor "migrações 001 e 002 registradas" "001_schema.sql,002_seeds.sql" \
  "SELECT string_agg(arquivo, ',' ORDER BY arquivo) FROM schema_migrations"
espera_valor "tabelas do public documentadas com COMMENT ON (só as nossas)" "t" \
  "SELECT count(DISTINCT c.relname) >= 7 FROM pg_description d
     JOIN pg_class c ON c.oid = d.objoid JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND d.objsubid = 0 AND c.relkind = 'r'"

echo "tipologia (definições do README)"
espera_valor "5 siglas" "AUTO,DEF,FISC,GEST,IP" \
  "SELECT string_agg(sigla, ',' ORDER BY sigla) FROM tipologia"
espera_valor "AUTO é autorregulação" "t" "SELECT nome ILIKE 'Autorregula%' FROM tipologia WHERE sigla = 'AUTO'"
espera_valor "IP gere instâncias participativas" "t" "SELECT nome ILIKE '%participativ%' FROM tipologia WHERE sigla = 'IP'"
espera_valor "GEST é gestão da política já definida" "t" "SELECT descricao ILIKE '%já definida%' FROM tipologia WHERE sigla = 'GEST'"

echo "ato"
espera_valor "ato da planilha entra sem id_dou nem conteúdo" "1" \
  "INSERT INTO orgao DEFAULT VALUES;
   INSERT INTO ato (origem, ref_legal, orgao_id, data_publicacao, ementa)
     VALUES ('PLANILHA', 'Resolução 12/2003', currval('orgao_id_seq'), '2003-02-19', 'ementa');
   SELECT count(*) FROM ato WHERE origem = 'PLANILHA'"
espera_erro "ato do DOU sem id_dou é recusado" "ck_ato_dou_completo" \
  "INSERT INTO orgao DEFAULT VALUES;
   INSERT INTO ato (origem, orgao_id, data_publicacao, conteudo) VALUES ('DOU', currval('orgao_id_seq'), '2021-01-01', 't')"
espera_erro "ato sem conteúdo nem ementa é recusado" "ck_ato_tem_texto" \
  "INSERT INTO orgao DEFAULT VALUES;
   INSERT INTO ato (origem, orgao_id, data_publicacao) VALUES ('PLANILHA', currval('orgao_id_seq'), '2003-01-01')"

echo "classificação insert-only"
espera_valor "reclassificar guarda as duas e a vigente é a última" "GEST|2" \
  "$BASE
   INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'DEF', $PESQUISADORA);
   INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'GEST', $PESQUISADORA);
   SELECT v.tipologia_sigla || '|' || (SELECT count(*) FROM classificacao WHERE ato_id = currval('ato_id_seq'))
     FROM classificacao_vigente v WHERE v.ato_id = currval('ato_id_seq')"
espera_valor "humana e automática convivem no mesmo ato" "2" \
  "$BASE
   INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'DEF', $PESQUISADORA);
   INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id, confianca)
     VALUES (currval('ato_id_seq'), 'GEST', (SELECT id FROM revisor WHERE tipo = 'PIPELINE' LIMIT 1), 0.8);
   SELECT count(*) FROM classificacao_vigente WHERE ato_id = currval('ato_id_seq')"
espera_erro "UPDATE em classificacao é bloqueado" "insert-only" \
  "$BASE
   INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'DEF', $PESQUISADORA);
   UPDATE classificacao SET tipologia_sigla = 'IP' WHERE ato_id = currval('ato_id_seq')"
espera_erro "apagar ato com classificação é bloqueado" "classificacao_ato_id_fkey" \
  "$BASE
   INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'DEF', $PESQUISADORA);
   DELETE FROM ato WHERE id = currval('ato_id_seq')"

echo "órgão"
espera_erro "dois nomes vigentes para o mesmo órgão são recusados" "uq_orgao_nome_vigente" \
  "INSERT INTO orgao DEFAULT VALUES;
   INSERT INTO orgao_nome (orgao_id, nome, data_inicio) VALUES
     (currval('orgao_id_seq'), 'Conselho A', '2020-01-01'), (currval('orgao_id_seq'), 'Conselho B', '2021-01-01')"
espera_valor "renomeação com vigência fechada é aceita" "2" \
  "INSERT INTO orgao DEFAULT VALUES;
   INSERT INTO orgao_nome (orgao_id, nome, data_inicio, data_fim) VALUES
     (currval('orgao_id_seq'), 'Ministério do Meio Ambiente', '2000-01-01', '2022-12-31');
   INSERT INTO orgao_nome (orgao_id, nome, data_inicio) VALUES
     (currval('orgao_id_seq'), 'Ministério do Meio Ambiente e Mudança do Clima', '2023-01-01');
   SELECT count(*) FROM orgao_nome WHERE orgao_id = currval('orgao_id_seq')"

echo
if [ "$falhas" -gt 0 ]; then echo "FALHOU: $falhas caso(s)"; exit 1; fi
echo "OK"
