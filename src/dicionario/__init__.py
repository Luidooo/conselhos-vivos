"""O dicionário de dados gerado, como a linhagem: as colunas reais vêm do catalog do dbt (gold e fontes) e do
catálogo do Postgres (OLTP); o significado, das descrições no YAML do dbt e dos COMMENT ON. Assim o dicionário
nunca fica atrás do banco, e coluna sem descrição aparece. Só biblioteca padrão."""

INICIO = "<!-- dicionario:inicio -->"
FIM = "<!-- dicionario:fim -->"


def linhas(manifest, catalog, oltp):
    """(camada, tabela, coluna, tipo, significado) de cada coluna, em ordem."""
    out = []
    for chave, camada_de in (("nodes", lambda n: "gold" if {"marts", "metricas"} & set(n.get("fqn", [])) else "staging"),
                             ("sources", lambda n: f"fonte {n.get('source_name', '')}")):
        for uid, real in catalog.get(chave, {}).items():
            n = manifest.get(chave, {}).get(uid)
            if not n or n.get("resource_type", "source") not in ("model", "source"):
                continue
            descritas = {c.lower(): v.get("description", "") for c, v in n.get("columns", {}).items()}
            for c in real["columns"].values():
                out.append((camada_de(n), n["name"], c["name"], c["type"], descritas.get(c["name"].lower()) or ""))
    out += [("oltp", t, c, tipo, d or "") for t, c, tipo, d in oltp]
    return sorted(out)


def sem_descricao(lista):
    return [f"{camada}.{tabela}.{coluna}" for camada, tabela, coluna, _, d in lista if not d.strip()]


def markdown(lista):
    partes = []
    for camada in dict.fromkeys(l[0] for l in lista):
        partes += [f"## {camada}", "", "| Tabela | Coluna | Tipo | Significado |", "|---|---|---|---|"]
        partes += [f"| {t} | {c} | {tipo} | {d.replace('|', '/')} |" for cam, t, c, tipo, d in lista if cam == camada]
        partes.append("")
    return "\n".join(partes)
