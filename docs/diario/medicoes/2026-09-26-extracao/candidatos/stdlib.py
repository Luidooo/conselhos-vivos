# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Candidato "stdlib" do diário de 26/09 (#3): o .xlsx é um zip de XMLs; lê com zipfile + xml.etree.
# Contrato comum aos candidatos: ver o docstring de ../bench.py.
import csv
import datetime as dt
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
EPOCA = dt.date(1899, 12, 30)  # dia 0 do Excel (sistema 1900), válido para datas depois de 01/03/1900

# aba: (linha do cabeçalho, coluna da data, coluna da referência legal, coluna da tipologia)
ABAS = {
    "CNAS": (1, "C", None, "G"),
    "CONAMA": (2, "B", "E", "G"),
    "CONCIDADES": (1, "C", "E", "J"),
    "CONDRAF": (1, "C", "E", "I"),
    "CNPIR": (1, "C", "E", "F"),
}


def celulas(z, caminho, textos):
    """Linha do Excel -> {coluna: (valor, é_número)}; ignora células só com estilo."""
    linhas = {}
    for row in ET.fromstring(z.read(caminho)).iter(M + "row"):
        valores = {}
        for c in row.findall(M + "c"):
            v, tipo = c.find(M + "v"), c.get("t")
            if tipo == "inlineStr":
                valores[re.match(r"[A-Z]+", c.get("r"))[0]] = ("".join(t.text or "" for t in c.iter(M + "t")), False)
            elif v is not None:
                col = re.match(r"[A-Z]+", c.get("r"))[0]
                valores[col] = (textos[int(v.text)], False) if tipo == "s" else (v.text, tipo is None or tipo == "n")
        if valores:
            linhas[int(row.get("r"))] = valores
    return linhas


def data(serial):
    return (EPOCA + dt.timedelta(days=float(serial))).isoformat()


def inteiro(valor):
    texto, numero = valor
    return str(int(float(texto))) if numero else texto


def ref_legal(aba, valor):
    if valor is None:
        return ""
    texto, numero = valor
    if aba == "CNPIR" and numero:  # o Excel leu "1/2005" como data: o mês é o número do ato
        d = EPOCA + dt.timedelta(days=float(texto))
        return f"{d.month}/{d.year}"
    return texto


def main(xlsx):
    z = zipfile.ZipFile(xlsx)
    textos = ["".join(t.text or "" for t in si.iter(M + "t"))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(M + "si")]
    alvos = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    folhas = {s.get("name"): "xl/" + alvos[s.get(REL)].removeprefix("/xl/")
              for s in ET.fromstring(z.read("xl/workbook.xml")).iter(M + "sheet")}

    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["aba", "linha", "id_versao", "data", "ref_legal", "tipologia", "tema"])
    for aba, (cab, c_data, c_ref, c_tip) in ABAS.items():
        for linha, v in sorted(celulas(z, folhas[aba], textos).items()):
            if linha <= cab:
                continue
            out.writerow([aba, linha, inteiro(v["A"]), data(v[c_data][0]),
                          ref_legal(aba, v.get(c_ref)), inteiro(v[c_tip]), v["D"][0]])


if __name__ == "__main__":
    main(sys.argv[1])
