"""Recorte do SIORG para a carga dos conselhos (ADR 0004): só as unidades cujo nome tem a
mesma chave de algum nome da planilha. Roda com rede (make siorg), fora da carga, e o
recorte fica versionado em data/referencia/: a carga não depende de rede nem muda sozinha.
"""

import csv
import hashlib
import io
import json
import urllib.request

from .identidade import chave, ler_nomes

URL = ("https://estruturaorganizacional.dados.gov.br/doc/estrutura-organizacional/resumida"
       "?codigoPoder=1&codigoEsfera=1")


def baixar():
    with urllib.request.urlopen(URL, timeout=300) as r:
        return r.read()


def recorte(planilha, dados):
    """CSV com uma linha por chave da planilha: quantas unidades casam e, se for uma só, qual."""
    js = json.loads(dados)
    unidades = js["unidades"]
    por_chave = {}
    for u in unidades:
        por_chave.setdefault(chave(u["nome"]), []).append(u)
    out = io.StringIO()
    out.write(f"# fonte={URL.split('?')[0]} data={js['servico']['data']} "
              f"sha256={hashlib.sha256(dados).hexdigest()} unidades={len(unidades)}\n")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["chave", "unidades", "codigo", "nome", "sigla", "tipo"])
    for k in sorted({chave(n) for n in ler_nomes(planilha).values()}):
        us = por_chave.get(k, [])
        if len(us) == 1:
            u = us[0]
            w.writerow([k, 1, u["codigoUnidade"].rsplit("/", 1)[1], u["nome"].strip(), (u["sigla"] or "").strip(),
                        u["codigoTipoUnidade"].rsplit("/", 1)[1]])
        else:
            w.writerow([k, len(us), "", "", "", ""])
    return out.getvalue()
