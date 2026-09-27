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
estado() {
  psql_db -c "SELECT (SELECT count(*) FROM ato) || '|' || (SELECT count(*) FROM classificacao) || '|' ||
                     (SELECT count(*) FROM orgao) || '|' || (SELECT count(*) FROM orgao_nome) || '|' ||
                     (SELECT count(*) FROM orgao_alias)"
}

echo "carga"
bash scripts/carga.sh >/dev/null
relatorio=$(sha256sum docs/carga/relatorio-planilha.md docs/carga/relatorio-conselhos.md)
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

echo "conselhos"
espera_valor "82 órgãos, e os 5 conselhos da #3 não duplicaram" "82|5" \
  "SELECT (SELECT count(*) FROM orgao) || '|' || (SELECT count(*) FROM conselho)"
espera_valor "125 aliases: 120 resolvidos, 2 indefinidos, 3 ambíguos" "AMBIGUO=3,INDEFINIDO=2,RESOLVIDO=120" \
  "SELECT string_agg(status || '=' || c, ',' ORDER BY status) FROM (
     SELECT status, count(*) c FROM orgao_alias WHERE fonte = 'PLANILHA' GROUP BY status) x"
espera_valor "o CNDH tem o nome antigo fechado na véspera da Lei 12.986" \
  "Conselho de Defesa dos Direitos da Pessoa Humana:1964-03-16:2014-06-01,Conselho Nacional dos Direitos Humanos:2014-06-02:" \
  "SELECT string_agg(nome || ':' || data_inicio || ':' || COALESCE(data_fim::text, ''), ',' ORDER BY data_inicio)
     FROM orgao_nome WHERE orgao_id = (SELECT orgao_id FROM orgao_nome WHERE nome = 'Conselho Nacional dos Direitos Humanos')"
espera_valor "as 3 grafias da pirataria no mesmo órgão" "1" \
  "SELECT count(DISTINCT orgao_id) FROM orgao_alias WHERE nome LIKE 'Conselho Nacional de Combate à Pirataria%'"
espera_valor "o CONAMA do sql/004 ganhou código SIORG e as grafias da planilha" "1023|3" \
  "SELECT o.codigo_siorg || '|' || (SELECT count(*) FROM orgao_alias a WHERE a.orgao_id = o.id)
     FROM orgao o JOIN orgao_nome n ON n.orgao_id = o.id AND n.data_fim IS NULL WHERE n.nome = 'Conselho Nacional do Meio Ambiente'"

echo "idempotência"
bash scripts/carga.sh >/dev/null
if [ "$(estado)" = "$depois_da_primeira" ]; then ok "carregar de novo não cria órgão, nome, alias, ato nem classificação"
else falha "carregar de novo mudou o banco: $depois_da_primeira → $(estado)"; fi
if [ "$(sha256sum docs/carga/relatorio-planilha.md docs/carga/relatorio-conselhos.md)" = "$relatorio" ]; then ok "os relatórios saem iguais"
else falha "um relatório mudou entre duas cargas da mesma planilha"; fi

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
if [ "$(estado)" = "$depois_da_primeira" ]; then ok "e nada ficou no banco"
else falha "o caso da curadoria deixou linhas no banco: $depois_da_primeira → $(estado)"; fi

echo
if [ "$falhas" -gt 0 ]; then echo "FALHOU: $falhas caso(s)"; exit 1; fi
echo "OK"
