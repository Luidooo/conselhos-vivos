#!/usr/bin/env bash
# Teste do fluxo de mudanças OLTP -> Delta (ADR 0007): uma reclassificação confirmada
# no OLTP atravessa o slot lógico e aparece no Delta; reexecutar não reaplica nada.
# Usa slot e Delta próprios (não mexe no slot nem na tabela do dia a dia).
# classificacao é insert-only: a linha do teste fica no banco local (make reset limpa).
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

cls_teste=""
# classificacao é insert-only; para não deixar resíduo (test_carga conta as linhas), o teste
# apaga a própria linha numa transação única, com o trigger desligado só ali dentro.
limpa() {
  cdc --drop-slot >/dev/null 2>&1 || true
  rm -rf "$TMP_HOST_DIR"
  if [ -n "$cls_teste" ]; then
    psql_db "ALTER TABLE classificacao DISABLE TRIGGER tg_classificacao_insert_only; DELETE FROM classificacao WHERE id = $cls_teste; ALTER TABLE classificacao ENABLE TRIGGER tg_classificacao_insert_only;" >/dev/null || echo "AVISO: não removeu a classificação $cls_teste do teste"
  fi
}
trap limpa EXIT INT TERM
limpa

[ "$(psql_db 'SHOW wal_level')" = logical ] || { echo "FALHOU: wal_level não é logical"; exit 1; }

echo "==> [test_cdc] 1. Carga completa em $TMP_HOST_DIR e slot novo sem pendências"
docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR" >/dev/null 2>&1
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=0" || { echo "FALHOU: slot recém-criado devia estar sem pendências:"; echo "$saida"; exit 1; }

ato=$(psql_db "SELECT id FROM ato ORDER BY id LIMIT 1")
revisor=$(psql_db "SELECT id FROM revisor WHERE tipo = 'HUMANO' ORDER BY id LIMIT 1")
antes=$(tipologia_no_delta "$ato")
nova=$(psql_db "SELECT sigla FROM tipologia WHERE sigla <> '$antes' ORDER BY sigla DESC LIMIT 1")

echo "==> [test_cdc] 2. Reclassificando o ato $ato ('${antes}' -> '$nova')"
cls_teste=$(psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$nova', $revisor) RETURNING id")
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=1 atos_afetados=1" || { echo "FALHOU: esperava 1 evento e 1 ato:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "atualizadas=1" || { echo "FALHOU: o Delta não atualizou a linha:"; echo "$saida"; exit 1; }
depois=$(tipologia_no_delta "$ato")
[ "$depois" = "$nova" ] || { echo "FALHOU: Delta tem '$depois', esperava '$nova'"; exit 1; }

echo "==> [test_cdc] 3. Segunda execução: nada pendente"
saida=$(cdc "$TMP_CONTAINER_DIR")
echo "$saida" | grep -q "pendentes=0" || { echo "FALHOU: o slot não avançou:"; echo "$saida"; exit 1; }

echo "==> [test_cdc] OK: reclassificação do ato $ato atravessou o slot até o Delta"

