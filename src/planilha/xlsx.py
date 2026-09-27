"""Leitor mínimo de .xlsx com a biblioteca padrão: o arquivo é um zip de XMLs.

Cobre o que a planilha da pesquisadora usa: strings compartilhadas (com ou sem rich text),
strings inline, números e o sistema de datas de 1900. Qualquer outra coisa (datas de 1904,
célula de erro como #N/A, booleano, fórmula sem valor calculado) levanta NaoSuportado, em vez
de virar um valor errado em silêncio. Escolha registrada no diário de 26/09 (#3).
"""

import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


class NaoSuportado(Exception):
    """A planilha usa um recurso do .xlsx que este leitor não interpreta."""


@dataclass(frozen=True)
class Celula:
    texto: str    # como está no XML; número vem em texto (ex.: "37671.0")
    numero: bool


@dataclass
class Aba:
    nome: str
    linhas: dict[int, dict[str, Celula]]  # linha do Excel -> coluna -> célula; só linhas com valor
    ultima_linha: int                     # maior linha com <row> no XML, com ou sem valor (o max_row do openpyxl)


def _texto_rico(si):
    """Texto de um <si>: <t> direto ou os <r><t> do rich text (ignora a fonética <rPh>)."""
    if (t := si.find(M + "t")) is not None:
        return t.text or ""
    return "".join(r.findtext(M + "t") or "" for r in si.findall(M + "r"))


def _celula(c, textos):
    ref, tipo, v = c.get("r"), c.get("t"), c.find(M + "v")
    if tipo == "inlineStr":
        return Celula(_texto_rico(c.find(M + "is")), False)
    if v is None:
        if c.find(M + "f") is not None:
            raise NaoSuportado(f"célula {ref}: fórmula sem valor calculado")
        return None  # só formatação
    if tipo == "s":
        return Celula(textos[int(v.text)], False)
    if tipo == "str":  # resultado de fórmula em texto
        return Celula(v.text or "", False)
    if tipo in (None, "n"):
        return Celula(v.text, True)
    raise NaoSuportado(f"célula {ref}: tipo {tipo!r} ({'erro' if tipo == 'e' else 'não suportado'}), valor {v.text!r}")


def ler(caminho):
    """Todas as abas: {nome: Aba}."""
    with zipfile.ZipFile(caminho) as z:
        livro = ET.fromstring(z.read("xl/workbook.xml"))
        pr = livro.find(M + "workbookPr")
        if pr is not None and pr.get("date1904") in ("1", "true"):
            raise NaoSuportado("sistema de datas de 1904")
        textos = []
        if "xl/sharedStrings.xml" in z.namelist():
            textos = [_texto_rico(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(M + "si")]
        alvos = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}

        abas = {}
        for s in livro.iter(M + "sheet"):
            alvo = alvos[s.get(REL)]
            caminho_xml = alvo.lstrip("/") if alvo.startswith("/") else "xl/" + alvo
            linhas, ultima = {}, 0
            for row in ET.fromstring(z.read(caminho_xml)).iter(M + "row"):
                n = int(row.get("r"))
                ultima = max(ultima, n)
                valores = {}
                for c in row.findall(M + "c"):
                    if (cel := _celula(c, textos)) is not None:
                        valores[re.match(r"[A-Z]+", c.get("r"))[0]] = cel
                if valores:
                    linhas[n] = valores
            abas[s.get("name")] = Aba(s.get("name"), linhas, ultima)
        return abas
