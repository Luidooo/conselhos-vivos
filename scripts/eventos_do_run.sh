#!/usr/bin/env bash
# Eventos de passo e de run de um run do Dagster, com horário (UTC) e a causa de cada falha, lidos do log
# que o Dagster grava durante o run. A saída do `dagster asset materialize` não traz os eventos de passo,
# porque cada passo roda noutro processo. Depois, o resumo do persist e o erro dele, dos compute logs.
# Uso: bash scripts/eventos_do_run.sh RUN_ID
set -euo pipefail
cd "$(dirname "$0")/.."
run=${1:?run id}
sqlite3 "data/dagster/history/runs/$run.db" "
  select substr(timestamp, 1, 19) || ' ' || replace(dagster_event_type, 'PIPELINE_', 'RUN_')
         || coalesce(' ' || step_key, '')
         || coalesce(' | causa: ' || trim(json_extract(event, '$.dagster_event.event_specific_data.error.cause.message'), char(10)), '')
  from event_logs
  where dagster_event_type in ('STEP_START','STEP_FAILURE','STEP_UP_FOR_RETRY','STEP_RESTARTED','STEP_SUCCESS',
                               'PIPELINE_SUCCESS','PIPELINE_FAILURE')
  order by id"
cat data/dagster/storage/"$run"/compute_logs/*.err 2>/dev/null \
  | grep -oE "done gravadas.*|run aborted err=.*" | sed -e 's/^done /persist: /' -e 's/^run aborted /persist falhou: /' || true
