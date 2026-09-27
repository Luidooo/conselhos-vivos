"""Relatório de carga em Markdown, versionado em docs/carga/relatorio-planilha.md.

Determinístico: rodar a carga de novo sobre a mesma planilha gera o mesmo arquivo, então
um diff no git quer dizer que a planilha ou o código mudou.
"""

import collections

from .abas import CAMPOS, MAPAS, TIPOLOGIAS


def _n(x):
    return f"{x:,}".replace(",", ".")


def _tabela(cabecalho, linhas):
    return ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)] + [
        "| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in l) + " |" for l in linhas]


def _lista(titulo, itens, vazio, cabecalho):
    out = [f"## {titulo}", ""]
    out += _tabela(cabecalho, itens) if itens else [vazio]
    return out + [""]


def relatorio(res):
    por_aba = collections.defaultdict(list)
    for a in res.atos:
        por_aba[a.aba].append(a)
    descartes = collections.Counter(aba for aba, _, _ in res.descartes)

    resumo = []
    for m in MAPAS:
        c, atos = res.contagem[m.aba], por_aba[m.aba]
        if len(atos) + descartes[m.aba] != c["com_valor"]:  # toda linha com valor vira ato ou descarte
            raise AssertionError(f"{m.aba}: {len(atos)} atos + {descartes[m.aba]} descartes ≠ {c['com_valor']} linhas")
        resumo.append([m.aba, m.conselho, c["no_arquivo"], c["com_valor"], len(atos), descartes[m.aba],
                       sum(1 for a in atos if a.tipologia)])
    no_arquivo, com_valor, atos, descartados, _ = total = [sum(l[i] for l in resumo) for i in range(2, 7)]
    resumo = [l[:2] + [_n(x) for x in l[2:]] for l in resumo] + [["**Total**", ""] + [f"**{_n(x)}**" for x in total]]

    out = [
        "# Relatório de carga da planilha da pesquisadora",
        "",
        "> Gerado por `make carga` (`python -m planilha relatorio`); não editar à mão. "
        "Rodar de novo sobre a mesma planilha gera este mesmo arquivo.",
        "",
        f"**Arquivo:** `{res.arquivo}` · sha256 `{res.sha256}`",
        "",
        "## Resumo",
        "",
        *_tabela(["Aba", "Conselho", "Linhas no arquivo¹", "Com valor", "Atos", "Descartadas", "Com classificação"],
                 resumo),
        "",
        "¹ Abaixo do cabeçalho, contando as que só têm formatação de célula. Linha sem nenhum valor não é "
        "registro. O 2.638 do diário de 25/09 é a soma do `max_row` − 1 do openpyxl, que no CONAMA conta "
        "também o cabeçalho, porque ele está na linha 2.",
        "",
        f"Toda linha com valor virou ato ou descarte: {_n(atos)} + {_n(descartados)} = {_n(com_valor)}.",
        "",
    ]
    out += _lista("Descartes", res.descartes, "Nenhuma linha descartada.", ["Aba", "Linha", "Motivo"])
    out += _lista("Atos sem classificação", res.sem_classificacao,
                  "Todo ato tem classificação da pesquisadora.", ["Aba", "Linha", "Motivo"])

    siglas = list(TIPOLOGIAS)
    tip = [[m.aba] + [sum(1 for a in por_aba[m.aba] if a.tipologia == s) for s in siglas]
           + [sum(1 for a in por_aba[m.aba] if not a.tipologia)] for m in MAPAS]
    tip.append(["**Total**"] + [f"**{sum(l[i] for l in tip)}**" for i in range(1, len(siglas) + 2)])
    out += ["## Tipologia por aba", "", *_tabela(["Aba", *siglas, "sem"], tip), ""]

    out += [f"## Conversões", "",
            f"{_n(len(res.atos))} datas convertidas do serial do Excel (dia 0 = 30/12/1899). Além delas:", ""]
    out += _tabela(["Aba", "Linha", "Conversão"], res.conversoes) if res.conversoes else ["Nenhuma."]
    out += [""]
    out += _lista("Avisos", res.avisos, "Nenhum.", ["Aba", "Linha", "Aviso"])

    out += ["## Mapeamento", "",
            "Cada coluna da planilha vira um campo do vocabulário único (`src/planilha/abas.py`).", ""]
    for m in MAPAS:
        out += [f"### {m.aba} → {m.conselho}", "", f"Cabeçalho na linha {m.cabecalho}.", ""]
        out += _tabela(["Coluna na planilha", "Campo", "Destino", "Por quê"],
                       [[f"`{titulo}`", campo, *CAMPOS[campo]] for campo, titulo in m.colunas.items()])
        for (aba, campo), valores in sorted(res.nao_carregados.items()):
            if aba == m.aba:
                vistos = "; ".join(f"{v!r} ({n})" for v, n in sorted(valores.items(), key=lambda x: str(x[0])))
                out += ["", f"Valores de `{m.colunas[campo]}`, não carregada: {vistos}."]
        out += [""]
    return "\n".join(out).rstrip() + "\n"
