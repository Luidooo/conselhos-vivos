#!/usr/bin/env bash
# Demonstra as falhas que o orquestrador separa (#83, #84, #85) e grava a prova em docs/adr/medicoes/0009-gold/:
#   1. mês ainda não publicado: o mês corrente, que nunca está publicado; falha sem retry, com a causa (#83);
#   2. a agenda: pede o mês anterior que falta e pula o que já foi carregado (#83);
#   3. ZIP com um XML que não lê como matéria: falha sem retry (#84);
#   4. lake e dbt forçados a falhar (host e banco que não existem): retry, e a causa com o erro do processo (#85);
#   5. um teste do dbt que falha de verdade (o mês do meio tirado com o excluir_mes): a prova traz o nome do teste (#85).
# Nada é baixado e o OLTP não é tocado: o mês corrente não tem ZIP, o ZIP do caso 3 só tem a entrada inválida, e os
# casos 4 não chegam ao banco. O caso 5 grava a gold sem o mês do meio e a restaura logo depois com um dbt build normal.
# Uso: bash scripts/demo_falhas.sh   (leva uns 4 minutos: os casos 4 esperam o retry)
set -euo pipefail
cd "$(dirname "$0")/.."
test -f dbt/target/manifest.json || { echo "falta o manifesto do dbt: rode make gold antes"; exit 1; }
command -v sqlite3 >/dev/null || { echo "falta o sqlite3, que lê o log de eventos do Dagster"; exit 1; }
mkdir -p data/dagster docs/adr/medicoes/0009-gold
corrente=$(TZ=America/Sao_Paulo date +%Y-%m)
saida=docs/adr/medicoes/0009-gold/falhas-$(date -u +%Y%m%dT%H%M%SZ).txt
log=$(mktemp)
trap 'rm -f "$log" "$saida.tmp"' EXIT   # uma prova pela metade não fica na pasta versionada

# Um container só: o pip install é pago uma vez. Cada caso imprime "CASO <nome> <run id>".
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T -e CORRENTE="$corrente" orquestrador sh -c '
# A saída inteira vai para um arquivo antes do grep: um grep que para no primeiro achado fecha o pipe,
# e o dagster cai com Broken pipe.
run_id() { "$@" > /tmp/materialize.log 2>&1 || true; grep -m1 -oE "__ASSET_JOB - [0-9a-f-]{36}" /tmp/materialize.log | cut -d" " -f3; }
python - <<"PY"
import os, warnings, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore")
import dagster as dg
from orquestracao import RETRY, mensal_schedule
from orquestracao.comandos import roda
instancia = dg.DagsterInstance.get()
corrente = os.environ["CORRENTE"]

# 1. O mesmo comando e a mesma regra do atos_do_mes, com o mês corrente: ele nunca está publicado.
@dg.asset(retry_policy=RETRY)
def fetch_mes_corrente(context):
    roda(context, "python", "-m", "dou", "fetch-mensal", "--month", corrente,
         de_dado="mês ainda não publicado nos dados abertos; a agenda tenta de novo amanhã")
print("CASO nao-publicado", dg.materialize([fetch_mes_corrente], instance=instancia, raise_on_error=False).run_id)

# 2. A agenda no dia 15 do mês seguinte ao corrente (pede o corrente) e no dia 15 do corrente (o anterior já entrou).
sp = ZoneInfo("America/Sao_Paulo")
ano, mes = map(int, corrente.split("-"))
for quando in (datetime(ano + mes // 12, mes % 12 + 1, 15, 6, tzinfo=sp), datetime(ano, mes, 15, 6, tzinfo=sp)):
    r = mensal_schedule(dg.build_schedule_context(instance=instancia, scheduled_execution_time=quando))
    pedido = f"RunRequest partição {r.partition_key}" if isinstance(r, dg.RunRequest) else f"SkipReason: {r.skip_message}"
    print(f"AGENDA em {quando:%Y-%m-%d %H:%M} (Brasília): {pedido}")

# 3. Um ZIP com uma entrada só, que não lê como matéria: o persist não grava nada e sai com o código de dado.
with zipfile.ZipFile("/tmp/ruim.zip", "w") as z:
    z.writestr("materia-quebrada.xml", "<xml><article id=")
@dg.asset(retry_policy=RETRY)
def persist_zip_ruim(context):
    roda(context, "python", "-m", "dou", "persist", "/tmp/ruim.zip",
         de_dado="ZIP corrompido ou com entrada que não lê como matéria; o que leu foi gravado")
print("CASO zip-invalido", dg.materialize([persist_zip_ruim], instance=instancia, raise_on_error=False).run_id)

# 5. A gold com o mês do meio tirado: o teste distribuicao_mes_sem_nenhum_ato falha de verdade. O asset existe só aqui,
# com o projeto dbt de produção; o gold de produção não ganha parâmetro. Sem retry: um teste que falha não melhora.
# shortcut: 2026-08 é o mês do meio da cobertura de julho a setembro; com outra cobertura, troque o mês.
from dagster_dbt import DbtCliResource, dbt_assets
from orquestracao import DBT
@dbt_assets(manifest=DBT.manifest_path, name="gold_sem_o_mes_do_meio")
def gold_sem_o_mes_do_meio(context, dbt: DbtCliResource):
    yield from dbt.cli(["build", "--vars", "{excluir_mes: 2026-08-01}", "--exclude-resource-type", "unit_test"],
                       context=context).stream()
r = dg.materialize([gold_sem_o_mes_do_meio], instance=instancia, resources={"dbt": DbtCliResource(project_dir=DBT)},
                   raise_on_error=False)
print("CASO dbt-teste", r.run_id)
PY
# A gold volta ao normal; se não voltar, a demonstração falha.
if dbt build --project-dir /app/dbt --quiet > /tmp/restaura.log 2>&1; then echo "GOLD restaurada com um dbt build normal"
else echo "GOLD NAO_RESTAURADA"; tail -5 /tmp/restaura.log; fi
# 4. Os assets de verdade, com uma variável de conexão quebrada.
echo "CASO lake $(run_id env PGHOST=host-que-nao-existe dagster asset materialize -m orquestracao --select silver/atos --partition 2026-08-01)"
echo "CASO dbt $(run_id env PGDATABASE=banco_que_nao_existe dagster asset materialize -m orquestracao --select stg_atos --partition 2026-08-01)"
' 2>&1 | grep -E "^(CASO|AGENDA|GOLD) " > "$log"
grep -q "^GOLD restaurada" "$log" || { echo "FALHOU: a gold não foi restaurada; rode make gold"; exit 1; }

{
  echo "# make demo-falhas, $(date -u '+%Y-%m-%d %H:%M:%S') UTC, mês corrente $corrente, gerado por scripts/demo_falhas.sh (horários em UTC)"
  echo "# A agenda olha as partições já materializadas no data/dagster desta máquina: noutra máquina, ou num clone limpo, o SkipReason pode virar RunRequest."
  while read -r tipo nome run; do
    if [[ "$tipo" == AGENDA ]]; then echo "==> agenda: $nome $run"; continue; fi
    if [[ "$tipo" == GOLD ]]; then echo "==> gold $nome $run"; continue; fi
    echo "==> caso $nome, run $run"
    bash scripts/eventos_do_run.sh "$run"
  done < "$log"
} > "$saida.tmp"
mv "$saida.tmp" "$saida"
cat "$saida"
