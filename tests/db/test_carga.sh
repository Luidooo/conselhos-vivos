#!/usr/bin/env bash
# Teste da carga da planilha (issue #3): carrega, confere o banco, carrega de novo e
# confere que nada duplicou e que o relatório não mudou.
# Pré-requisito: banco no ar e migrado (make migrate). A carga deixa os 215 atos no banco,
# que é o estado esperado depois do make setup; os outros casos rodam em transação desfeita.
# Uso: bash tests/db/test_carga.sh   (a partir de qualquer diretório)
set -euo pipefail
cd "$(dirname "$0")/../.."

falhas=0
ok()    { echo "  ok    $1"; }
falha() { echo "  FALHA $1"; falhas=$((falhas + 1)); }

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA "$@"' sh "$@" 2>&1
}

espera_valor() {
  local nome=$1 esperado=$2 sql=$3 out
  if out=$(psql_db -c "$sql") && [ "$out" = "$esperado" ]; then ok "$nome"
  else falha "$nome — esperava '$esperado', veio: $out"; fi
}

PLANILHA="SELECT a.* FROM ato a JOIN orgao_nome n ON n.orgao_id = a.orgao_id AND n.data_fim IS NULL
           WHERE a.origem = 'PLANILHA'"
PESQUISADORA="(SELECT id FROM revisor WHERE email = 'curadoria@pesquisa.local')"
estado() { psql_db -c "SELECT (SELECT count(*) FROM ato) || '|' || (SELECT count(*) FROM classificacao)"; }

echo "carga"
bash scripts/carga.sh >/dev/null
relatorio=$(sha256sum docs/carga/relatorio-planilha.md)
depois_da_primeira=$(estado)
espera_valor "215 atos da planilha, por conselho" "12,24,28,53,98" \
  "SELECT string_agg(c::text, ',' ORDER BY c) FROM (SELECT count(*) c FROM ato WHERE origem = 'PLANILHA' GROUP BY orgao_id) x"
espera_valor "uma classificação da pesquisadora por ato" "215|215" \
  "SELECT count(*) || '|' || count(DISTINCT k.ato_id) FROM classificacao k JOIN ato a ON a.id = k.ato_id
    WHERE a.origem = 'PLANILHA' AND k.revisor_id = $PESQUISADORA"
espera_valor "tipologia como na planilha" "99=6,AUTO=97,DEF=68,FISC=31,GEST=6,IP=7" \
  "SELECT string_agg(s || '=' || c, ',' ORDER BY s) FROM (
     SELECT v.tipologia_sigla s, count(*) c FROM classificacao_vigente v JOIN ato a ON a.id = v.ato_id
      WHERE a.origem = 'PLANILHA' GROUP BY 1) x"
espera_valor "data serial convertida (CNAS, ID 1)" "2003-02-19" \
  "SELECT data_publicacao FROM ($PLANILHA AND n.nome = 'Conselho Nacional de Assistência Social') a WHERE id_planilha = 1"
espera_valor "ato/ano do CNPIR recuperado (ID 1)" "1/2005" \
  "SELECT ref_legal FROM ($PLANILHA AND n.nome = 'Conselho Nacional de Promoção da Igualdade Racial') a WHERE id_planilha = 1"
espera_valor "resumo em ementa, texto em conteudo (ConCidades, ID 1)" "true|true" \
  "SELECT (ementa LIKE 'Aprovação do Regimento%') || '|' || (conteudo LIKE 'RESOLVE:%')
     FROM ($PLANILHA AND n.nome = 'Conselho das Cidades') a WHERE id_planilha = 1"

echo "idempotência"
bash scripts/carga.sh >/dev/null
if [ "$(estado)" = "$depois_da_primeira" ]; then ok "carregar de novo não cria ato nem classificação"
else falha "carregar de novo mudou o banco: $depois_da_primeira → $(estado)"; fi
if [ "$(sha256sum docs/carga/relatorio-planilha.md)" = "$relatorio" ]; then ok "o relatório sai igual"
else falha "o relatório mudou entre duas cargas da mesma planilha"; fi

echo "curadoria"
# A pesquisadora reclassifica um ato pela curadoria; a carga roda de novo dentro da mesma
# transação (sem o BEGIN/COMMIT dela) e não pode sobrepor. Tudo é desfeito no fim.
out=$({
  echo "BEGIN;"
  echo "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id)
          SELECT a.id, 'IP', $PESQUISADORA FROM ato a WHERE a.origem = 'PLANILHA' AND a.id_planilha = 1
           ORDER BY a.id LIMIT 1;"
  docker compose --progress quiet run --rm -T carga sql | sed '/^BEGIN;$/d; /^COMMIT;$/d'
  echo "SELECT 'vigente=' || v.tipologia_sigla FROM classificacao_vigente v
          WHERE v.revisor_id = $PESQUISADORA AND v.ato_id = (SELECT id FROM ato WHERE origem = 'PLANILHA'
                                                              AND id_planilha = 1 ORDER BY id LIMIT 1);"
  echo "ROLLBACK;"
} | psql_db -f - || true)
if [ "$(grep '^vigente=' <<<"$out")" = "vigente=IP" ]; then ok "a carga não sobrepõe a reclassificação da curadoria"
else falha "a carga sobrepôs a curadoria ou falhou: $out"; fi
espera_valor "e nada ficou no banco" "$depois_da_primeira" \
  "SELECT (SELECT count(*) FROM ato) || '|' || (SELECT count(*) FROM classificacao)"

echo
if [ "$falhas" -gt 0 ]; then echo "FALHOU: $falhas caso(s)"; exit 1; fi
echo "OK"
