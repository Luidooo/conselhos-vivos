"""A camada semântica fora do dbt (ADR 0011): cada consulta salva do MetricFlow vira um CSV em data/gold/metricas/,
lido pelo painel e por quem quiser os números. A lista vem do semantic_manifest.json: consulta nova no YAML
entra sem mexer aqui."""

import json
import os
import subprocess


def consultas(manifesto: dict) -> list[str]:
    """Os nomes das consultas salvas do manifesto semântico, em ordem."""
    return sorted(q["name"] for q in manifesto.get("saved_queries", []))


def exportar(nomes: list[str], destino: str, projeto: str) -> None:
    """Roda o mf de cada consulta no projeto dbt e grava DESTINO/<nome>.csv. Falha na primeira que falhar."""
    for nome in nomes:
        subprocess.run(["mf", "query", "--saved-query", nome, "--csv", os.path.join(destino, f"{nome}.csv")],
                       cwd=projeto, check=True)


def ler_manifesto(projeto: str) -> dict:
    with open(os.path.join(projeto, "target", "semantic_manifest.json"), encoding="utf-8") as f:
        return json.load(f)
