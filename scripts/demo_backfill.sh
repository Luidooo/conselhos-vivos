#!/usr/bin/env bash
# Backfill de um intervalo de meses pelo Dagster: um run por mês, em ordem, cada um com retry.
# Uso: bash scripts/demo_backfill.sh 2026-07 2026-09
set -euo pipefail
cd "$(dirname "$0")/.."
de=${1:?mês inicial AAAA-MM}; ate=${2:?mês final AAAA-MM}
test -f dbt/target/manifest.json || { echo "falta o manifesto do dbt: rode make gold antes"; exit 1; }
command -v sqlite3 >/dev/null || { echo "falta o sqlite3, que lê o log de eventos do Dagster"; exit 1; }
mkdir -p data/gold data/dagster docs/adr/medicoes/0009-gold
saida=docs/adr/medicoes/0009-gold/backfill-$de-a-$ate.txt
[[ -e "$saida" ]] && saida=${saida%.txt}-de-novo.txt   # a segunda rodada, que prova que nada duplica
: > "$saida"
mes=$de
while [[ "$mes" < "$ate" || "$mes" == "$ate" ]]; do
  echo "==> partição $mes-01" | tee -a "$saida"
  log=$(DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T orquestrador \
    dagster asset materialize -m orquestracao --select '*' --partition "$mes-01" 2>&1) || { tail -30 <<<"$log"; exit 1; }
  run=$(grep -m1 -oE '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}' <<<"$log")
  # Cada passo roda noutro processo: os eventos dele ficam no log do run, e a saída do persist nos compute logs.
  sqlite3 "data/dagster/history/runs/$run.db" \
    "select replace(dagster_event_type, 'PIPELINE_', 'RUN_') || ' ' || coalesce(step_key, '') from event_logs where dagster_event_type in ('STEP_SUCCESS','STEP_FAILURE','STEP_UP_FOR_RETRY','PIPELINE_SUCCESS','PIPELINE_FAILURE') order by id" | tee -a "$saida"
  grep -ho "done gravadas.*" data/dagster/storage/"$run"/compute_logs/*.err | sed 's/^done /persist: /' | tee -a "$saida"
  mes=$(date -j -v+1m -f "%Y-%m-%d" "$mes-01" +%Y-%m 2>/dev/null || date -d "$mes-01 +1 month" +%Y-%m)
done
echo "==> atos por mês depois do backfill" | tee -a "$saida"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select date_trunc('"'"'month'"'"', data_publicacao)::date, count(*) from ato where origem = '"'"'DOU'"'"' group by 1 order by 1"' | tee -a "$saida"
