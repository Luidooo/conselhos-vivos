"""python -m alertas: lê a mart_vitalidade da gold e grava os alertas no Postgres como etl_reverso (ADR 0011)."""

import os
import sys

import duckdb
import psycopg

from . import alertas, gravar

COLUNAS = "orgao_id, nome, sigla, situacao, mes_referencia, meses_sem_publicar, mencoes_no_periodo"

if __name__ == "__main__":
    with duckdb.connect(os.environ.get("ALERTAS_GOLD", "/data/gold/conselhos.duckdb"), read_only=True) as con:
        cur = con.execute(f"select {COLUNAS} from mart_vitalidade")
        nomes = [d[0] for d in cur.description]
        linhas = [dict(zip(nomes, r)) for r in cur.fetchall()]
    lista = alertas(linhas)
    with psycopg.connect(host=os.environ.get("PGHOST", "db"), dbname=os.environ["PGDATABASE"],
                         user=os.environ["ALERTAS_PGUSER"], password=os.environ["ALERTAS_PGPASSWORD"]) as conn:
        novos, atualizados, inalterados = gravar(conn, lista)
    print(f"[INFO] done novos={novos} atualizados={atualizados} inalterados={inalterados}", file=sys.stderr)
