"""Orquestração da E3: ingestão do mês, silver e gold, num grafo mensal com retry e backfill."""

import os
import subprocess
from pathlib import Path

import dagster as dg
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from dou import dadosabertos

DBT = DbtProject(project_dir=Path("/app/dbt"), profiles_dir=Path("/app/dbt"))
DBT.prepare_if_dev()

# O mês só existe nos dados abertos depois que acaba: a última partição é o mês passado.
MENSAL = dg.MonthlyPartitionsDefinition(start_date="2002-01-01")
# A Imprensa Nacional e o banco falham de vez em quando; 30 s dá tempo de voltar.
RETRY = dg.RetryPolicy(max_retries=3, delay=30)


def _roda(context: dg.AssetExecutionContext, *cmd: str) -> None:
    context.log.info(" ".join(cmd))
    subprocess.run(cmd, check=True)


@dg.asset(partitions_def=MENSAL, retry_policy=RETRY, group_name="ingestao")
def atos_do_mes(context: dg.AssetExecutionContext) -> None:
    """Baixa o ZIP do mês dos dados abertos e grava os atos de conselho no Postgres."""
    mes = dadosabertos.Mes.parse(context.partition_key[:7])
    _roda(context, "python", "-m", "dou", "fetch-mensal", "--month", str(mes))
    # O mesmo nome e o mesmo diretório que o fetch-mensal usa ao gravar.
    zip_do_mes = Path(os.environ["DADOS_ABERTOS_OUTPUT_DIR"]) / dadosabertos.nome_do_zip(mes)
    _roda(context, "python", "-m", "dou", "persist", str(zip_do_mes))


# shortcut: silver e gold são recalculadas inteiras a cada mês (MERGE idempotente, tabelas pequenas);
# particionar de verdade quando o dbt build passar de alguns minutos.
@dg.asset(key=["silver", "atos"], deps=[atos_do_mes], partitions_def=MENSAL, retry_policy=RETRY, group_name="silver")
def silver_atos(context: dg.AssetExecutionContext) -> None:
    """Atualiza a tabela Delta da E2 a partir do OLTP."""
    _roda(context, "python", "-m", "lake", "/data/silver/atos")


@dbt_assets(manifest=DBT.manifest_path, partitions_def=MENSAL)
def gold(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


mensal = dg.define_asset_job("mensal", selection="*", partitions_def=MENSAL)

defs = dg.Definitions(
    assets=[atos_do_mes, silver_atos, gold],
    jobs=[mensal],
    # dia 15: o ZIP do mês anterior costuma sair por volta do dia 13 (setembro saiu em 13/10).
    schedules=[dg.build_schedule_from_partitioned_job(mensal, day_of_month=15, hour_of_day=6)],
    resources={"dbt": DbtCliResource(project_dir=DBT)},
)
