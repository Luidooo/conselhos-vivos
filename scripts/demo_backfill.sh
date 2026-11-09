#!/usr/bin/env bash
# Backfill de um intervalo de meses pelo Dagster: um run por mês, em ordem, cada um com retry.
# Em sequência de propósito: a silver (Delta) e a gold (DuckDB, um escritor só) não aguentam runs em paralelo.
# Cada execução grava um arquivo novo, com data e hora no nome: uma prova já versionada nunca é sobrescrita.
# Uso: bash scripts/demo_backfill.sh 2026-07 2026-09
set -euo pipefail
cd "$(dirname "$0")/.."
de=${1:?mês inicial AAAA-MM}; ate=${2:?mês final AAAA-MM}
test -f dbt/target/manifest.json || { echo "falta o manifesto do dbt: rode make gold antes"; exit 1; }
command -v sqlite3 >/dev/null || { echo "falta o sqlite3, que lê o log de eventos do Dagster"; exit 1; }
mkdir -p data/gold data/dagster docs/adr/medicoes/0009-gold
saida=docs/adr/medicoes/0009-gold/backfill-$de-a-$ate-$(date -u +%Y%m%dT%H%M%SZ).txt
echo "# make demo-backfill DE=$de ATE=$ate, $(date -u '+%Y-%m-%d %H:%M:%S') UTC, gerado por scripts/demo_backfill.sh" | tee "$saida"
mes=$de
while [[ "$mes" < "$ate" || "$mes" == "$ate" ]]; do
  log=$(DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T orquestrador \
    dagster asset materialize -m orquestracao --select '*' --partition "$mes-01" 2>&1) || { tail -30 <<<"$log"; exit 1; }
  # O run id está em toda linha de evento da saída: "... - __ASSET_JOB - <run id> - ...".
  run=$(grep -m1 -oE '__ASSET_JOB - [0-9a-f-]{36}' <<<"$log" | cut -d' ' -f3)
  echo "==> partição $mes-01, run $run" | tee -a "$saida"
  bash scripts/eventos_do_run.sh "$run" | tee -a "$saida"
  mes=$(date -j -v+1m -f "%Y-%m-%d" "$mes-01" +%Y-%m 2>/dev/null || date -d "$mes-01 +1 month" +%Y-%m)
done
echo "==> atos do DOU por mês depois do backfill" | tee -a "$saida"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select date_trunc('"'"'month'"'"', data_publicacao)::date, count(*) from ato where origem = '"'"'DOU'"'"' group by 1 order by 1"' | tee -a "$saida"
