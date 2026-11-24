"""Medições do ADR 0011, rodadas em /app/dbt: o MetricFlow contra a opção nula (SQL direto na gold)."""

import csv
import subprocess
import time

import duckdb

print("## mf query de cada consulta salva")
for q in ("atividade_por_mes", "atividade_por_conselho"):
    s = time.time()
    subprocess.run(["mf", "query", "--saved-query", q, "--csv", f"/tmp/{q}.csv"], check=True, capture_output=True)
    with open(f"/tmp/{q}.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    print(f"{q}: {len(linhas)} linhas em {time.time() - s:.1f} s")
    if q == "atividade_por_mes":
        for l in linhas:
            print("  ", l["metric_time__month"][:7], l["atos_publicados"])

print("## o SQL que o MetricFlow gerou para atividade_por_mes")
sql = subprocess.run(["mf", "query", "--saved-query", "atividade_por_mes", "--explain"],
                     check=True, capture_output=True, text=True).stdout
# Só o SQL: o mf imprime antes o aviso de versão nova e os quadros da animação de espera.
print(sql[sql.index("SELECT"):].rstrip())

print("## opção nula: atos por mês em SQL direto na gold")
with duckdb.connect("/data/gold/conselhos.duckdb", read_only=True) as c:
    s = time.time()
    r = c.sql("select date_trunc('month', data_publicacao) as mes, count(*) from fct_ato "
              "where origem = 'DOU' group by 1 order by 1").fetchall()
    print(f"{len(r)} linhas em {time.time() - s:.3f} s")
    for mes, atos in r:
        print("  ", f"{mes:%Y-%m}", atos)
