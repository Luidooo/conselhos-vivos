"""A linhagem do dbt como diagrama Mermaid, gerada do manifest.json: fontes, staging, marts, a camada semântica e
as consultas salvas (E4), com as setas de dependência. Assim o diagrama do site nunca fica atrás do projeto dbt. Só biblioteca padrão.
"""

import json

INICIO = "<!-- linhagem-dbt:inicio -->"
FIM = "<!-- linhagem-dbt:fim -->"


def nos(manifest):
    """{unique_id: (camada, rótulo)} das fontes, seeds, modelos, modelos semânticos, métricas e consultas salvas
    do projeto; testes ficam de fora."""
    out = {}
    for uid, s in manifest.get("sources", {}).items():
        out[uid] = (f"fonte {s['source_name']}", f"{s['source_name']}.{s['name']}")
    for uid, n in manifest.get("nodes", {}).items():
        if n["resource_type"] == "seed":
            out[uid] = ("seed", n["name"])
        elif n["resource_type"] == "model":
            out[uid] = ("staging" if "staging" in n.get("fqn", []) else "marts", n["name"])
    for uid, s in manifest.get("semantic_models", {}).items():
        out[uid] = ("semântica", f"modelo semântico {s['name']}")
    for uid, m in manifest.get("metrics", {}).items():
        out[uid] = ("semântica", f"métrica {m['name']}")
    for uid, q in manifest.get("saved_queries", {}).items():
        out[uid] = ("consultas salvas", q["name"])
    return out


def mermaid(manifest):
    """O diagrama, com uma caixa por camada e as setas de cada modelo para quem ele lê. Ordenado: a mesma
    entrada dá sempre o mesmo texto."""
    todos = nos(manifest)
    ident = {uid: f"n{i}" for i, uid in enumerate(sorted(todos))}
    camadas = {}
    for uid, (camada, rotulo) in todos.items():
        camadas.setdefault(camada, []).append((rotulo, uid))
    linhas = ["```mermaid", "flowchart LR"]
    ordem = sorted(c for c in camadas if c.startswith("fonte")) + [c for c in ("seed", "staging", "marts", "semântica", "consultas salvas") if c in camadas]
    for i, camada in enumerate(ordem):
        linhas.append(f'  subgraph c{i}["{camada}"]')
        for rotulo, uid in sorted(camadas[camada]):
            linhas.append(f'    {ident[uid]}["{rotulo}"]')
        linhas.append("  end")
    for uid in sorted(todos):
        n = next((manifest[k][uid] for k in ("nodes", "semantic_models", "metrics", "saved_queries")
                  if uid in manifest.get(k, {})), None)
        if not n:
            continue
        for pai in sorted(set(n.get("depends_on", {}).get("nodes", []))):
            if pai in ident:
                linhas.append(f"  {ident[pai]} --> {ident[uid]}")
    linhas.append("```")
    return "\n".join(linhas)


def atualizar(pagina, manifest_path):
    """Troca o diagrama entre os marcadores da página pelo gerado agora."""
    with open(manifest_path, encoding="utf-8") as f:
        diagrama = mermaid(json.load(f))
    with open(pagina, encoding="utf-8") as f:
        texto = f.read()
    i, j = texto.index(INICIO) + len(INICIO), texto.index(FIM)
    with open(pagina, "w", encoding="utf-8") as f:
        f.write(texto[:i] + "\n" + diagrama + "\n" + texto[j:])
