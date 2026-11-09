"""Orquestração da E3: ingestão do mês, silver e gold, num grafo mensal com retry e backfill."""

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import dagster as dg
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from dou import dadosabertos

from .comandos import mes_a_carregar, roda

DBT = DbtProject(project_dir=Path("/app/dbt"), profiles_dir=Path("/app/dbt"))
DBT.prepare_if_dev()

# O mês só existe nos dados abertos depois que acaba: a última partição é o mês passado.
# O fuso das partições é também o da agenda: 6h de Brasília, não de UTC.
MENSAL = dg.MonthlyPartitionsDefinition(start_date="2002-01-01", timezone="America/Sao_Paulo")
# A Imprensa Nacional e o banco falham de vez em quando; 30 s dá tempo de voltar. Falha de dado não usa
# o retry: o roda levanta Failure(allow_retries=False).
RETRY = dg.RetryPolicy(max_retries=3, delay=30)


@dg.asset(partitions_def=MENSAL, retry_policy=RETRY, group_name="ingestao")
def atos_do_mes(context: dg.AssetExecutionContext) -> None:
    """Baixa o ZIP do mês dos dados abertos e grava os atos de conselho no Postgres."""
    mes = dadosabertos.Mes.parse(context.partition_key[:7])
    roda(context, "python", "-m", "dou", "fetch-mensal", "--month", str(mes),
         de_dado="mês ainda não publicado nos dados abertos; a agenda tenta de novo amanhã")
    # O mesmo nome e o mesmo diretório que o fetch-mensal usa ao gravar.
    zip_do_mes = Path(os.environ["DADOS_ABERTOS_OUTPUT_DIR"]) / dadosabertos.nome_do_zip(mes)
    roda(context, "python", "-m", "dou", "persist", str(zip_do_mes),
         de_dado="entrada do ZIP que não lê como matéria; o resto do ZIP foi gravado")


# shortcut: silver e gold são recalculadas inteiras a cada mês (MERGE idempotente, tabelas pequenas);
# particionar de verdade quando o dbt build passar de alguns minutos.
@dg.asset(key=["silver", "atos"], deps=[atos_do_mes], partitions_def=MENSAL, retry_policy=RETRY, group_name="silver")
def silver_atos(context: dg.AssetExecutionContext) -> None:
    """Atualiza a tabela Delta da E2 a partir do OLTP."""
    roda(context, "python", "-m", "lake", "/data/silver/atos")


@dbt_assets(manifest=DBT.manifest_path, partitions_def=MENSAL, retry_policy=RETRY)
def gold(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


mensal = dg.define_asset_job("mensal", selection="*", partitions_def=MENSAL)


# Todo dia do 15 ao 28, às 6h de Brasília: o ZIP do mês anterior costuma sair por volta do dia 13 (setembro
# saiu em 13/10), mas pode atrasar (#83). Mês já carregado é pulado; mês ainda não publicado falha sem retry
# e é tentado de novo no dia seguinte. Ligada desde o início: com o make orquestrador no ar, roda sozinha.
@dg.schedule(job=mensal, cron_schedule="0 6 15-28 * *", execution_timezone="America/Sao_Paulo",
             default_status=dg.DefaultScheduleStatus.RUNNING)
def mensal_schedule(context: dg.ScheduleEvaluationContext):
    quando = context.scheduled_execution_time or datetime.now(ZoneInfo("America/Sao_Paulo"))
    mes = mes_a_carregar(quando.date(), set(context.instance.get_materialized_partitions(atos_do_mes.key)))
    if mes is None:
        return dg.SkipReason("o mês anterior já foi carregado")
    return dg.RunRequest(run_key=f"{mes}@{quando:%Y-%m-%d}", partition_key=mes)

defs = dg.Definitions(
    assets=[atos_do_mes, silver_atos, gold],
    jobs=[mensal],
    schedules=[mensal_schedule],
    resources={"dbt": DbtCliResource(project_dir=DBT)},
)
