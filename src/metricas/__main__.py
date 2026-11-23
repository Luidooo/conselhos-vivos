"""python -m metricas DESTINO: exporta as consultas salvas da camada semântica para DESTINO/<nome>.csv.
O projeto dbt precisa de um dbt parse antes (o make metricas e o asset do Dagster fazem isso)."""

import os
import sys

from . import consultas, exportar, ler_manifesto

if __name__ == "__main__":
    projeto = os.environ.get("METRICAS_PROJETO", "/app/dbt")
    destino = sys.argv[1]
    os.makedirs(destino, exist_ok=True)
    nomes = consultas(ler_manifesto(projeto))
    exportar(nomes, destino, projeto)
    print(f"[INFO] done consultas={len(nomes)} destino={destino}", file=sys.stderr)
