"""Medição do ADR 0004 (#4): como resolver a identidade dos 125 nomes de conselho da planilha.

Compara, contra o gabarito proposto em gabarito.csv, as alternativas do ADR:
  A  nome literal (opção nula)
  B  chave normalizada: caixa, acento, espaços e quebras de linha, sigla no fim
  C  B + similaridade de texto (difflib), com agrupamento por ligação simples, em 4 limiares
  D  casar a chave B com os nomes do SIORG (cadastro de órgãos do Executivo federal)

Métrica por pares de linhas: um par é positivo se as duas linhas são do mesmo grupo no
gabarito. Pares com linha "ambiguo" ou "indefinido" ficam fora da conta de acerto; uma
fusão que junta linha "indefinido" a outra conta como fusão errada.

Só biblioteca padrão. Da raiz do repositório:
    python3 docs/adr/medicoes/0004-identidade/bench.py
Baixa o SIORG (~96 MB) uma vez para data/interim/siorg/ (fora do git) e grava resultados.json.
"""

import csv
import difflib
import hashlib
import itertools
import json
import pathlib
import re
import sys
import unicodedata
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[4]
AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))
from planilha import xlsx  # noqa: E402

PLANILHA = RAIZ / "data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx"
ABA = "Conselhos mapeados no DOU manua"
SIORG_URL = ("https://estruturaorganizacional.dados.gov.br/doc/estrutura-organizacional/resumida"
             "?codigoPoder=1&codigoEsfera=1")
SIORG = RAIZ / "data/interim/siorg/estrutura-resumida.json"
LIMIARES = (0.80, 0.85, 0.90, 0.95)


def chave(nome):
    """Alternativa B: o nome sem o que não muda a identidade."""
    s = " ".join(nome.split())                    # quebra de linha e espaço duplo
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)        # sigla entre parênteses no fim
    s = re.sub(r"-[A-Z]{2,}$", "", s)             # sigla colada com hífen no fim
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def grupos_por(rotulo, linhas):
    """{linha: rótulo} vira {linha: id do grupo}."""
    ids = {}
    return {n: ids.setdefault(rotulo(n), len(ids)) for n in linhas}


def ligacao_simples(linhas, parecidos):
    """Agrupa por união: basta um par parecido para juntar dois grupos."""
    pai = {n: n for n in linhas}

    def raiz(n):
        while pai[n] != n:
            pai[n] = pai[pai[n]]
            n = pai[n]
        return n
    for a, b in parecidos:
        pai[raiz(a)] = raiz(b)
    return {n: raiz(n) for n in linhas}


def pontua(grupo, gab, nomes):
    certas = [n for n in gab if gab[n]["status"] == "certo"]
    vp = fp = fn = 0
    erradas = []
    for a, b in itertools.combinations(sorted(gab), 2):
        junto = grupo[a] == grupo[b]
        sa, sb = gab[a]["status"], gab[b]["status"]
        if "ambiguo" in (sa, sb):
            continue
        deveria = sa == sb == "certo" and gab[a]["grupo"] == gab[b]["grupo"]
        if junto and deveria:
            vp += 1
        elif junto:
            fp += 1
            erradas.append([nomes[a], nomes[b]])
        elif deveria:
            fn += 1
    return {
        "entidades": len(set(grupo.values())),
        "pares_certos_juntados": vp,
        "pares_que_faltou_juntar": fn,
        "fusoes_erradas": fp,
        "exemplos_de_fusao_errada": erradas[:5],
        "linhas_certas": len(certas),
    }


def siorg():
    if not SIORG.exists():
        SIORG.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SIORG_URL, timeout=300) as r:
            SIORG.write_bytes(r.read())
    dados = SIORG.read_bytes()
    unidades = json.loads(dados)["unidades"]
    return hashlib.sha256(dados).hexdigest(), json.loads(dados)["servico"]["data"], unidades


def main():
    aba = xlsx.ler(PLANILHA)[ABA]
    nomes = {n: " ".join(aba.linhas[n]["A"].texto.split()) for n in sorted(aba.linhas)}
    with open(AQUI / "gabarito.csv", newline="") as f:
        gab = {int(r["linha"]): r for r in csv.DictReader(f)}
    assert set(gab) == set(nomes), "o gabarito não cobre as mesmas linhas da aba"
    chaves = {n: chave(t) for n, t in nomes.items()}
    res = {"linhas": len(nomes),
           "gabarito": {"grupos_certos": len({gab[n]["grupo"] for n in gab if gab[n]["status"] == "certo"}),
                        "ambiguas": sum(r["status"] == "ambiguo" for r in gab.values()),
                        "indefinidas": sum(r["status"] == "indefinido" for r in gab.values())},
           "alternativas": {}}

    # A: nome literal; B: chave normalizada. A normalização ingênua do diário de 25/09 fica de referência.
    def sem_acento(s):
        return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    ingenua = {n: " ".join(sem_acento(re.sub(r"\s*\([^)]*\)\s*$", "", t)).casefold().split())
               for n, t in nomes.items()}
    res["alternativas"]["A nome literal"] = pontua(grupos_por(nomes.get, nomes), gab, nomes)
    res["alternativas"]["B0 normalização do diário de 25/09"] = pontua(grupos_por(ingenua.get, nomes), gab, nomes)
    res["alternativas"]["B chave normalizada"] = pontua(grupos_por(chaves.get, nomes), gab, nomes)

    # C: B + similaridade. Ligação simples sobre as chaves.
    razao = {(a, b): difflib.SequenceMatcher(None, chaves[a], chaves[b]).ratio()
             for a, b in itertools.combinations(sorted(nomes), 2)}
    for lim in LIMIARES:
        parecidos = [p for p, r in razao.items() if r >= lim or chaves[p[0]] == chaves[p[1]]]
        res["alternativas"][f"C similaridade >= {lim:.2f}"] = pontua(ligacao_simples(nomes, parecidos), gab, nomes)

    # D: SIORG. Casa a chave B com a chave do nome de cada unidade.
    sha, data, unidades = siorg()
    por_chave = {}
    for u in unidades:
        por_chave.setdefault(chave(u["nome"]), []).append(u)
    achou = {n: por_chave.get(chaves[n], []) for n in nomes}
    unico = {n: u[0]["codigoUnidade"].rsplit("/", 1)[1] for n, u in achou.items() if len(u) == 1}
    grupo_d = {n: unico.get(n, f"sem-{n}") for n in nomes}
    d = pontua(grupo_d, gab, nomes)
    tipos = {}
    for n, u in achou.items():
        if len(u) == 1:
            t = u[0]["codigoTipoUnidade"].rsplit("/", 1)[1]
            tipos[t] = tipos.get(t, 0) + 1
    d.update({
        "siorg": {"data": data, "sha256": sha, "unidades": len(unidades),
                  "unidades_colegiadas": sum(u["codigoTipoUnidade"].endswith("/unidade-colegiada") for u in unidades)},
        "linhas_com_1_unidade": len(unico),
        "linhas_com_varias_unidades": {nomes[n]: len(u) for n, u in achou.items() if len(u) > 1},
        "linhas_sem_unidade": sum(1 for u in achou.values() if not u),
        "tipo_da_unidade_achada": tipos,
        "grupos_certos_com_codigo": len({gab[n]["grupo"] for n in unico if gab[n]["status"] == "certo"}),
        "exemplos_sem_unidade": [nomes[n] for n, u in achou.items() if not u][:12],
    })
    res["alternativas"]["D SIORG pela chave B"] = d

    # E (escolhida): B + decisões registradas. Custo: grupos que B não fecha e linhas que pedem decisão humana.
    b = grupos_por(chaves.get, nomes)
    abertos = {gab[n]["grupo"] for n in gab if gab[n]["status"] == "certo"
               and len({b[m] for m in gab if gab[m]["grupo"] == gab[n]["grupo"]}) > 1}
    res["alternativas"]["E chave B + decisões registradas"] = {
        "grupos_que_B_nao_fecha": len(abertos),
        "linhas_sem_decisao_possivel_por_codigo": res["gabarito"]["ambiguas"] + res["gabarito"]["indefinidas"],
    }

    (AQUI / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    print(f"{'alternativa':40} {'entid.':>6} {'certos':>6} {'faltou':>6} {'errados':>7}")
    for nome, r in res["alternativas"].items():
        if "entidades" in r:
            print(f"{nome:40} {r['entidades']:>6} {r['pares_certos_juntados']:>6} "
                  f"{r['pares_que_faltou_juntar']:>6} {r['fusoes_erradas']:>7}")
    print(json.dumps({k: v for k, v in d.items() if k != "exemplos_de_fusao_errada"}, ensure_ascii=False, indent=1))
    print(json.dumps(res["alternativas"]["E chave B + decisões registradas"], ensure_ascii=False))


main()
