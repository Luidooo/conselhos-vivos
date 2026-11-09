#!/usr/bin/env bash
# Derruba o banco, dispara um mês no Dagster e religa o banco antes do retry: a primeira tentativa
# falha, o RetryPolicy (30 s) tenta de novo e passa. O mês usado já está no bronze: nada é baixado.
# Atenção: o Postgres é o mesmo do pgAdmin e do CDC, que ficam sem banco por cerca de 1 minuto.
# Cada execução grava um arquivo novo, com data e hora no nome.
set -euo pipefail
cd "$(dirname "$0")/.."
MES=${MES:-2026-08}
mkdir -p data/dagster/history/runs docs/adr/medicoes/0009-gold
saida=docs/adr/medicoes/0009-gold/retry-$MES-$(date -u +%Y%m%dT%H%M%SZ).txt
test -f dbt/target/manifest.json || { echo "falta o manifesto do dbt: rode make gold antes"; exit 1; }
command -v sqlite3 >/dev/null || { echo "falta o sqlite3, que lê o log de eventos do Dagster"; exit 1; }
marca=$(mktemp)
trap 'docker compose start db >/dev/null; rm -f "$marca"' EXIT   # o banco volta mesmo se o script cair
docker compose stop db
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T --no-deps orquestrador \
  dagster asset materialize -m orquestracao --select atos_do_mes --partition "$MES-01" > "$saida.log" 2>&1 &
pid=$!
# Só religa o banco depois que a primeira tentativa cair: o pip install leva uns 30 s, e um tempo fixo
# pode religar cedo demais. O retry espera 30 s, tempo de o Postgres subir.
# shortcut: o run da demonstração é o primeiro log de eventos mais novo que a marca; não rode a agenda
# nem a interface ao mesmo tempo.
run=""
for _ in $(seq 180); do
  if [[ -z "$run" ]]; then
    db=$(find data/dagster/history/runs -name '*.db' -newer "$marca" | head -1)
    [[ -n "$db" ]] && run=$(basename "$db" .db)
  fi
  [[ -n "$run" ]] && bash scripts/eventos_do_run.sh "$run" 2>/dev/null | grep -q STEP_UP_FOR_RETRY && break
  sleep 1
done
docker compose start db
rc=0; wait "$pid" || rc=$?   # sem o || o set -e encerraria o script antes da conferência
[[ -n "$run" ]] || { echo "FALHOU: o run não começou"; tail -20 "$saida.log"; exit 1; }
{ echo "# make demo-retry, mês $MES, run $run, banco parado antes da primeira tentativa (horários em UTC)"
  bash scripts/eventos_do_run.sh "$run"; } > "$saida"
rm -f "$saida.log"
cat "$saida"
grep -q STEP_UP_FOR_RETRY "$saida" || { echo "FALHOU: não houve retry"; exit 1; }
grep -q RUN_SUCCESS "$saida" || { echo "FALHOU: o retry não recuperou"; exit 1; }
echo "OK: a primeira tentativa caiu com o banco fora e o retry recuperou (rc=$rc)"
