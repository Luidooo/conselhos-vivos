#!/usr/bin/env bash
# Eventos de passo e de run de um run do Dagster, com horário (UTC) e a causa de cada falha, lidos do log
# que o Dagster grava durante o run. A saída do `dagster asset materialize` não traz os eventos de passo,
# porque cada passo roda noutro processo. Depois, dos compute logs: o resumo e o erro do persist, e as
# linhas de falha do dbt.
# Uso: bash scripts/eventos_do_run.sh RUN_ID
set -euo pipefail
cd "$(dirname "$0")/.."
run=${1:?run id}
# Tudo passa pelo sed do fim: uma string de conexão no erro (o dbt imprime a do attach) não pode levar a senha
# para a prova versionada.
{
# A causa: a exceção encadeada, quando há; senão a mensagem do próprio Failure, que o roda monta com a última
# linha do stderr do comando (#85). Só a primeira linha, sem o nome da classe.
sqlite3 "data/dagster/history/runs/$run.db" "
  with e as (
    select id, timestamp, dagster_event_type, step_key,
           coalesce(json_extract(event, '$.dagster_event.event_specific_data.error.cause.message'),
                    json_extract(event, '$.dagster_event.event_specific_data.error.message')) as erro
    from event_logs
    where dagster_event_type in ('STEP_START','STEP_FAILURE','STEP_UP_FOR_RETRY','STEP_RESTARTED','STEP_SUCCESS',
                                 'PIPELINE_SUCCESS','PIPELINE_FAILURE'))
  select substr(timestamp, 1, 19) || ' ' || replace(dagster_event_type, 'PIPELINE_', 'RUN_')
         || coalesce(' ' || step_key, '')
         || coalesce(' | causa: ' || replace(
              case when instr(erro, char(10)) > 0 then substr(erro, 1, instr(erro, char(10)) - 1) else erro end,
              'dagster._core.definitions.events.Failure: ', ''), '')
  from e order by id"
logs=data/dagster/storage/"$run"/compute_logs
cat "$logs"/*.err 2>/dev/null \
  | grep -oE "done gravadas.*|run aborted err=.*" | sed -e 's/^done /persist: /' -e 's/^run aborted /persist falhou: /' || true
# O dbt escreve no stdout; as cores saem antes do grep. Na saída que o Dagster grava, a linha não começa com o
# horário ("39 of 53 FAIL 1 teste ..."); no terminal, começa ("02:42:16  39 of 53 ..."): só o horário sai.
cat "$logs"/*.out 2>/dev/null | sed $'s/\x1b\\[[0-9;]*m//g' \
  | grep -E " FAIL [0-9]+ | ERROR (creating|running)|Failure in |\[ERROR\]: in |(IO|Runtime|Database|Compilation|Parsing) Error:" \
  | sed -E 's/^[0-9]{2}:[0-9]{2}:[0-9]{2} +//; s/^.*Exception: //; s/^/dbt: /' | awk '!visto[$0]++' | head -8 || true
} | sed -E 's/(password=)[^ "]*/\1***/g'
