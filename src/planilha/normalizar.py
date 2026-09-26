"""Linhas da planilha -> atos no vocabulário único de abas.py.

Nenhuma linha some em silêncio: se a estrutura da planilha mudou (aba ou coluna faltando),
a carga para (ErroDeEstrutura); se uma linha não pode virar ato, ela é descartada com o
motivo; o que entra mas merece atenção vira aviso. Tudo isso vai para o relatório.
"""

import collections
import datetime as dt
import hashlib
from dataclasses import dataclass, field

from . import xlsx
from .abas import MAPAS, TIPOLOGIAS

EPOCA = dt.date(1899, 12, 30)  # dia 0 do Excel; vale a partir do serial 61 (01/03/1900)
REF_LEGAL_MAX = 100            # ato.ref_legal é VARCHAR(100)


class ErroDeEstrutura(Exception):
    """A planilha não tem a forma que abas.py descreve: a carga para."""


class Descarte(Exception):
    """A linha não pode virar ato; a mensagem é o motivo que vai para o relatório."""


@dataclass
class Ato:
    aba: str
    linha: int
    conselho: str
    id_planilha: int
    data_publicacao: dt.date
    ref_legal: str | None
    ementa: str | None
    conteudo: str | None
    tipologia: str | None           # sigla, ou None se a linha não tem rótulo válido
    tipologia_original: str
    referente: str | None


@dataclass
class Resultado:
    arquivo: str
    sha256: str
    atos: list = field(default_factory=list)
    descartes: list = field(default_factory=list)          # (aba, linha, motivo)
    sem_classificacao: list = field(default_factory=list)  # (aba, linha, motivo)
    avisos: list = field(default_factory=list)             # (aba, linha, texto)
    conversoes: list = field(default_factory=list)         # (aba, linha, texto)
    contagem: dict = field(default_factory=dict)           # aba -> {"no_arquivo": n, "com_valor": n}
    nao_carregados: dict = field(default_factory=dict)     # (aba, campo) -> Counter dos valores


def texto(cel):
    """Texto sem espaços nas pontas; célula ausente ou em branco vira None."""
    if cel is None or not cel.texto.strip():
        return None
    return str(int(float(cel.texto))) if cel.numero and float(cel.texto).is_integer() else cel.texto.strip()


def data_do_serial(serial):
    s = float(serial)
    if s < 61:
        raise Descarte(f"data {serial} é anterior a 01/03/1900 (o Excel conta errado antes disso)")
    return EPOCA + dt.timedelta(days=int(s))


def normalizar(caminho):
    with open(caminho, "rb") as f:
        res = Resultado(str(caminho), hashlib.sha256(f.read()).hexdigest())
    abas = xlsx.ler(caminho)
    for mapa in MAPAS:
        if mapa.aba not in abas:
            raise ErroDeEstrutura(f"a planilha não tem a aba {mapa.aba}")
        _aba(mapa, abas[mapa.aba], res)
    return res


def _aba(mapa, aba, res):
    titulos = {c.texto.strip(): letra for letra, c in aba.linhas.get(mapa.cabecalho, {}).items()}
    col = {}
    for campo, titulo in mapa.colunas.items():
        if titulo not in titulos:
            raise ErroDeEstrutura(f"{mapa.aba}: não há coluna '{titulo}' no cabeçalho (linha {mapa.cabecalho})")
        col[campo] = titulos[titulo]
    mapeadas = set(col.values())
    corpo = {n: cels for n, cels in aba.linhas.items() if n > mapa.cabecalho}
    res.contagem[mapa.aba] = {"no_arquivo": aba.ultima_linha - mapa.cabecalho, "com_valor": len(corpo)}
    for n in sorted(aba.linhas):
        if n < mapa.cabecalho:
            res.avisos.append((mapa.aba, n, "linha acima do cabeçalho com valor, ignorada"))

    vistos = {}
    for n, cels in sorted(corpo.items()):
        pega = lambda campo: cels.get(col[campo]) if campo in col else None
        for letra in sorted(set(cels) - mapeadas):
            res.avisos.append((mapa.aba, n, f"célula {letra}{n} fora das colunas do cabeçalho, não carregada: "
                                            f"{cels[letra].texto.strip()!r}"))
        for campo in ("autor", "emissao"):
            if campo in col:
                res.nao_carregados.setdefault((mapa.aba, campo), collections.Counter())[texto(pega(campo))] += 1
        try:
            ato = _ato(mapa, n, pega, vistos, res)
        except Descarte as motivo:
            res.descartes.append((mapa.aba, n, str(motivo)))
            continue
        vistos[ato.id_planilha] = n
        res.atos.append(ato)


def _ato(mapa, n, pega, vistos, res):
    bruto = texto(pega("id_versao"))
    if bruto is None:
        raise Descarte("sem ID_VERSAO")
    if not bruto.isdigit():
        raise Descarte(f"ID_VERSAO não é um número inteiro: {bruto!r}")
    id_ = int(bruto)
    if id_ in vistos:
        raise Descarte(f"ID_VERSAO {id_} repetido (já está na linha {vistos[id_]})")

    cel = pega("data")
    if cel is None or not cel.texto.strip():
        raise Descarte("sem data")
    if not cel.numero:
        raise Descarte(f"a data não é uma data do Excel: {cel.texto.strip()!r}")
    data = data_do_serial(cel.texto)

    ementa, conteudo = texto(pega("ementa")), texto(pega("conteudo"))
    if ementa is None and conteudo is None:
        raise Descarte("sem texto: nem resumo nem transcrição")

    ref = _ref_legal(mapa, n, pega("ref_legal"), res)
    if ref is not None and len(ref) > REF_LEGAL_MAX:
        raise Descarte(f"referência legal com mais de {REF_LEGAL_MAX} caracteres")

    ano = texto(pega("ano"))
    if ano is not None and ano != str(data.year):
        res.avisos.append((mapa.aba, n, f"ANO {ano} diferente do ano da data ({data.isoformat()})"))

    original = texto(pega("tipologia")) or ""
    sigla, _, nota = original.partition(" ")
    if sigla not in TIPOLOGIAS:
        sigla = None
        res.sem_classificacao.append((mapa.aba, n, f"tipologia {original!r} não é uma das siglas"
                                                   if original else "sem tipologia"))
    elif nota:
        res.conversoes.append((mapa.aba, n, f"tipologia {original!r} → {sigla} (a anotação fica no CSV)"))

    return Ato(mapa.aba, n, mapa.conselho, id_, data, ref, ementa, conteudo, sigla, original, texto(pega("referente")))


def _ref_legal(mapa, n, cel, res):
    # CNPIR: o Excel leu "1/2005" (ato/ano) como a data 01/01/2005; o mês é o número do ato
    if mapa.aba == "CNPIR" and cel is not None and cel.numero:
        d = data_do_serial(cel.texto)
        ref = f"{d.month}/{d.year}"
        res.conversoes.append((mapa.aba, n, f"DIS_LEG {texto(cel)} (o Excel leu como {d.isoformat()}) → {ref!r}"))
        return ref
    return texto(cel)
