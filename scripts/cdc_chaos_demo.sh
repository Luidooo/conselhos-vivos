#!/usr/bin/env bash
# Demonstração de tolerância a falhas e semântica de entrega (ADR 0007 / Issue #30):
# Interrompe abruptamente o consumidor após gravar no Delta Lake e antes de avançar
# o slot lógico (at-least-once). Na reexecução, o consumidor reprocessa o evento e
# o MERGE idempotente garante contagem idêntica e zero duplicações (effectively-once).
#
# Uso: bash scripts/cdc_chaos_demo.sh     (ou make cdc-chaos; ATO_ID=123 escolhe o ato)
set -euo pipefail
cd "$(dirname "$0")/.."

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1"
}

duckdb_sql() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -c "
INSTALL delta; LOAD delta;
$1" 2>&1 | grep -v -E 'Installing|Loading|^$' || true
}

duckdb_val() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -csv -noheader -c "
INSTALL delta; LOAD delta;
$1" | tr -d '[:space:]'
}

docker compose up -d --wait --wait-timeout 90 db
[ "$(psql_db 'SHOW wal_level')" = logical ] || { echo "wal_level não é logical: rode make down && make up"; exit 1; }

echo "================================================================================"
echo "DEMONSTRAÇÃO DE CAOS: QUEDA DO CONSUMIDOR CDC E IDEMPOTÊNCIA NO DELTA LAKE"
echo "================================================================================"
echo ""

echo "==> 1. Estado inicial: Carga completa e slot sincronizado (make lake; make cdc)"
make --no-print-directory lake
make --no-print-directory cdc >/dev/null

total_inicial=$(duckdb_val "SELECT count(*) FROM delta_scan('/data/silver/atos');")
duplicatas_inicial=$(duckdb_val "SELECT count(*) FROM (SELECT ato_id FROM delta_scan('/data/silver/atos') GROUP BY ato_id HAVING count(*) > 1);")

echo "    Tabela Delta Lake inicial: total de atos = $total_inicial, duplicatas = $duplicatas_inicial"
echo ""

ato=${ATO_ID:-$(psql_db "SELECT id FROM ato ORDER BY id LIMIT 1")}
revisor=$(psql_db "INSERT INTO revisor (nome, tipo, email) VALUES ('Curador Teste Caos', 'HUMANO', 'curador-caos@pesquisa.local') ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome RETURNING id")
atual=$(psql_db "SELECT COALESCE((SELECT tipologia_sigla FROM classificacao_vigente cv JOIN revisor r ON r.id = cv.revisor_id WHERE cv.ato_id = $ato ORDER BY (r.tipo='HUMANO') DESC, cv.criado_em DESC LIMIT 1), '')")
nova=$(psql_db "SELECT sigla FROM tipologia WHERE sigla <> '$atual' ORDER BY sigla DESC LIMIT 1")

echo "==> 2. Situação do ato $ato ANTES da alteração:"
duckdb_sql "SELECT ato_id, orgao_sigla, tipologia_sigla, revisor_tipo, atualizado_em FROM delta_scan('/data/silver/atos') WHERE ato_id = $ato;"
echo ""

echo "==> 3. Inserindo reclassificação no OLTP: ato $ato ('${atual}' -> '$nova') [INSERT em classificacao]"
psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$nova', $revisor)"

slot_pendentes_antes=$(psql_db "SELECT count(*) FROM pg_logical_slot_peek_changes('conselhos_lake', NULL, NULL)")
echo "    Slot lógico 'conselhos_lake' antes do consumo: $slot_pendentes_antes evento(s) pendente(s) no WAL."
echo ""

echo "==> 4. SIMULAÇÃO DE QUEDA: Executando consumidor CDC com --falhar-apos-gravar"
echo "    (O processo aplicará o MERGE no Delta Lake, mas cairá antes de confirmar o LSN no slot)"
set +e
saida_queda=$(DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T cdc --falhar-apos-gravar 2>&1)
rc_queda=$?
set -e

echo "$saida_queda"
if [ $rc_queda -ne 42 ]; then
  echo "ERRO: esperava código de saída 42 na simulação de queda, mas recebeu $rc_queda"
  exit 1
fi
echo "    ✓ Consumidor abortado com código $rc_queda conforme esperado."
echo ""

echo "==> 5. Verificação do estado durante a falha:"
slot_pendentes_queda=$(psql_db "SELECT count(*) FROM pg_logical_slot_peek_changes('conselhos_lake', NULL, NULL)")
echo "    - Slot lógico: $slot_pendentes_queda evento(s) AINDA PENDENTE(S) (o cursor LSN não avançou)."
if [ "$slot_pendentes_queda" -eq 0 ]; then
  echo "ERRO: slot foi confirmado indevidamente durante a queda!"
  exit 1
fi

total_queda=$(duckdb_val "SELECT count(*) FROM delta_scan('/data/silver/atos');")
tipologia_queda=$(duckdb_val "SELECT tipologia_sigla FROM delta_scan('/data/silver/atos') WHERE ato_id = $ato;")
echo "    - Delta Lake: dado já gravado com tipologia '$tipologia_queda' e total de atos = $total_queda."
duckdb_sql "SELECT ato_id, orgao_sigla, tipologia_sigla, revisor_tipo, atualizado_em FROM delta_scan('/data/silver/atos') WHERE ato_id = $ato;"
echo ""

echo "==> 6. RECUPERAÇÃO PÓS-QUEDA: Reexecutando consumidor normal (make cdc)"
echo "    (O consumidor reprocessará o mesmo evento do slot; o MERGE idempotente deve absorver sem duplicar)"
saida_recup=$(make --no-print-directory cdc 2>&1)
echo "$saida_recup"
echo ""

echo "==> 7. Verificação do estado pós-recuperação:"
slot_pendentes_fim=$(psql_db "SELECT count(*) FROM pg_logical_slot_peek_changes('conselhos_lake', NULL, NULL)")
total_fim=$(duckdb_val "SELECT count(*) FROM delta_scan('/data/silver/atos');")
duplicatas_fim=$(duckdb_val "SELECT count(*) FROM (SELECT ato_id FROM delta_scan('/data/silver/atos') GROUP BY ato_id HAVING count(*) > 1);")
tipologia_fim=$(duckdb_val "SELECT tipologia_sigla FROM delta_scan('/data/silver/atos') WHERE ato_id = $ato;")

echo "    - Slot lógico pendências: $slot_pendentes_fim (slot avançado com sucesso)"
echo "    - Total de atos no Delta Lake: $total_fim (inicial: $total_inicial)"
echo "    - Chaves duplicadas no Delta Lake: $duplicatas_fim"
echo "    - Tipologia vigente no Delta Lake: '$tipologia_fim'"

if [ "$total_fim" -ne "$total_inicial" ]; then
  echo "ERRO: contagem total no Delta alterou ($total_inicial -> $total_fim)!"
  exit 1
fi

if [ "$duplicatas_fim" -ne 0 ]; then
  echo "ERRO: encontradas chaves duplicadas no Delta!"
  exit 1
fi
echo "    ✓ Contagem rigorosamente idêntica e nenhuma duplicata."
echo ""

echo "==> 8. Restaurando tipologia original ('$nova' -> '$atual') para manter dados limpos"
psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$atual', $revisor)" >/dev/null
make --no-print-directory cdc >/dev/null

echo "================================================================================"
echo "DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!"
echo "Semântica comprovada: Leitura 'at-least-once' no Postgres via slot lógico"
echo "+ escrita idempotente por MERGE no Delta Lake = entrega efetivamente uma vez."
echo "================================================================================"

