#!/usr/bin/env bash
# Teste do fluxo de mudanças OLTP -> Delta (ADR 0007): uma reclassificação confirmada
# no OLTP atravessa o slot lógico e aparece no Delta; reexecutar não reaplica nada.
# Usa slot e Delta próprios (não mexe no slot nem na tabela do dia a dia).
# classificacao é insert-only: a linha do teste fica no banco com revisor de teste e não afeta outros testes.
set -euo pipefail
cd "$(dirname "$0")/../.."

export CDC_SLOT=conselhos_lake_teste
TMP_NAME="_test_cdc_$$"
TMP_HOST_DIR="data/silver/$TMP_NAME"
TMP_CONTAINER_DIR="/data/silver/$TMP_NAME"
export DOCKER_UID=$(id -u) DOCKER_GID=$(id -g)

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1"
}
cdc() { docker compose --progress quiet run --rm -T cdc "$@" 2>&1; }
tipologia_no_delta() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -csv -noheader -c "
INSTALL delta; LOAD delta;
SELECT tipologia_sigla FROM delta_scan('$TMP_CONTAINER_DIR') WHERE ato_id = $1;" | tr -d '[:space:]'
}
contagem_delta() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -csv -noheader -c "
INSTALL delta; LOAD delta;
SELECT count(*) FROM delta_scan('$TMP_CONTAINER_DIR');" | tr -d '[:space:]'
}
duplicatas_delta() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -csv -noheader -c "
INSTALL delta; LOAD delta;
SELECT count(*) FROM (SELECT ato_id FROM delta_scan('$TMP_CONTAINER_DIR') GROUP BY ato_id HAVING count(*) > 1);" | tr -d '[:space:]'
}

ato=""
antes=""
revisor=""

# Limpeza do slot temporário e da pasta temporária do Delta.
# classificacao é insert-only (ADR 0001): as reclassificações ficam no histórico.
# Caso ocorra falha no meio, o trap restaura a tipologia original com novo INSERT.
limpa() {
  cdc --drop-slot >/dev/null 2>&1 || true
  rm -rf "$TMP_HOST_DIR"
  if [ -n "$antes" ] && [ -n "$ato" ] && [ -n "$revisor" ]; then
    psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id)
             SELECT $ato, '$antes', $revisor
             WHERE (SELECT tipologia_sigla FROM classificacao_vigente cv JOIN revisor r ON r.id = cv.revisor_id WHERE cv.ato_id = $ato ORDER BY (r.tipo='HUMANO') DESC, cv.criado_em DESC LIMIT 1) <> '$antes';" >/dev/null 2>&1 || true
  fi
}
trap limpa EXIT INT TERM
limpa

[ "$(psql_db 'SHOW wal_level')" = logical ] || { echo "FALHOU: wal_level não é logical"; exit 1; }

echo "==> [test_cdc] 1. Carga completa em $TMP_HOST_DIR e slot novo sem pendências"
docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR" >/dev/null 2>&1
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=0" || { echo "FALHOU: slot recém-criado devia estar sem pendências:"; echo "$saida"; exit 1; }
total_esperado=$(contagem_delta)
[ "$total_esperado" -gt 0 ] || { echo "FALHOU: Delta está vazio"; exit 1; }

ato=$(psql_db "SELECT id FROM ato ORDER BY id LIMIT 1")
revisor=$(psql_db "INSERT INTO revisor (nome, tipo, email) VALUES ('Revisor de Teste CDC', 'HUMANO', 'teste-cdc@sistema.local') ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome RETURNING id")
antes=$(tipologia_no_delta "$ato")
nova=$(psql_db "SELECT sigla FROM tipologia WHERE sigla <> '$antes' ORDER BY sigla DESC LIMIT 1")

echo "==> [test_cdc] 2. Reclassificando o ato $ato ('${antes}' -> '$nova')"
psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$nova', $revisor)" >/dev/null
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=1 atos_afetados=1" || { echo "FALHOU: esperava 1 evento e 1 ato:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "atualizadas=1" || { echo "FALHOU: o Delta não atualizou a linha:"; echo "$saida"; exit 1; }
depois=$(tipologia_no_delta "$ato")
[ "$depois" = "$nova" ] || { echo "FALHOU: Delta tem '$depois', esperava '$nova'"; exit 1; }

echo "==> [test_cdc] 3. Segunda execução: nada pendente"
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=0" || { echo "FALHOU: o slot não avançou:"; echo "$saida"; exit 1; }

echo "==> [test_cdc] 4. Queda forçada: reclassifica, consumidor grava Delta e cai antes de avançar o slot"
terceira=$(psql_db "SELECT sigla FROM tipologia WHERE sigla NOT IN ('$antes', '$nova') ORDER BY sigla DESC LIMIT 1")
if [ -z "$terceira" ]; then
  terceira="$antes"
fi
psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$terceira', $revisor)" >/dev/null

set +e
saida=$(cdc "$TMP_CONTAINER_DIR" --falhar-apos-gravar)
rc=$?
set -e
[ $rc -eq 42 ] || { echo "FALHOU: esperava código de saída 42 na simulação de queda, obteve $rc:"; echo "$saida"; exit 1; }

# Slot não avançou no Postgres:
pendentes_queda=$(psql_db "SELECT count(*) FROM pg_logical_slot_peek_changes('$CDC_SLOT', NULL, NULL)")
[ "$pendentes_queda" -gt 0 ] || { echo "FALHOU: slot não devia ter avançado após a queda"; exit 1; }

# Delta já gravou o ato e contagem total não mudou:
[ "$(tipologia_no_delta "$ato")" = "$terceira" ] || { echo "FALHOU: Delta devia ter '$terceira' após a gravação"; exit 1; }
[ "$(contagem_delta)" = "$total_esperado" ] || { echo "FALHOU: contagem total no Delta alterou na queda"; exit 1; }

echo "==> [test_cdc] 5. Reprocessamento pós-queda: consumidor reexecuta e MERGE idempotente absorve sem duplicar"
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=1 atos_afetados=1" || { echo "FALHOU no reprocessamento: esperava 1 evento e 1 ato:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "inalteradas=1" || { echo "FALHOU no reprocessamento: esperava inalteradas=1:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "atualizadas=0" || { echo "FALHOU no reprocessamento: esperava atualizadas=0:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "inseridas=0" || { echo "FALHOU no reprocessamento: esperava inseridas=0:"; echo "$saida"; exit 1; }

# Slot agora avançou:
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=0" || { echo "FALHOU: slot devia estar zerado após recuperação:"; echo "$saida"; exit 1; }
[ "$(contagem_delta)" = "$total_esperado" ] || { echo "FALHOU: contagem total no Delta alterou após reprocessamento"; exit 1; }
[ "$(duplicatas_delta)" = "0" ] || { echo "FALHOU: chaves duplicadas no Delta após reprocessamento"; exit 1; }

echo "==> [test_cdc] 6. Restaurando tipologia original ('$terceira' -> '$antes')"
psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$antes', $revisor)" >/dev/null
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=1 atos_afetados=1" || { echo "FALHOU na restauração: esperava 1 evento e 1 ato:"; echo "$saida"; exit 1; }
restaurado=$(tipologia_no_delta "$ato")
[ "$restaurado" = "$antes" ] || { echo "FALHOU: Delta tem '$restaurado', esperava '$antes'"; exit 1; }
[ "$(contagem_delta)" = "$total_esperado" ] || { echo "FALHOU: contagem no Delta alterou após restauração"; exit 1; }
[ "$(duplicatas_delta)" = "0" ] || { echo "FALHOU: chaves duplicadas no Delta após restauração"; exit 1; }

echo "==> [test_cdc] 7. Nada pendente após restauração"
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=0" || { echo "FALHOU: o slot não avançou após restauração:"; echo "$saida"; exit 1; }

echo "==> [test_cdc] OK: reclassificação, simulação de queda com reprocessamento e restauração passaram com sucesso"

