"""Os 125 nomes da aba de conselhos -> órgãos canônicos e aliases (ADR 0004).

A chave normalizada junta automaticamente. Todo o resto vem do arquivo de decisões
(data/referencia/conselhos-decisoes.csv): grafia, renomeação, nome de órgão sem SIORG,
indefinido e ambíguo. O nome vigente vem do SIORG quando a chave casa com uma unidade só;
senão, da decisão "nome". Decisão incoerente para a carga (ErroDeDecisao): nada é
resolvido por aproximação.
"""

import csv
import datetime as dt
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from planilha import xlsx

ABA = "Conselhos mapeados no DOU manua"
TIPOS = ("grafia", "renomeacao", "nome", "indefinido", "ambiguo")
STATUS = {"indefinido": "INDEFINIDO", "ambiguo": "AMBIGUO"}


class ErroDeDecisao(Exception):
    """O arquivo de decisões não fecha com a planilha ou com o SIORG: a carga para."""


def espacos(nome):
    return " ".join(nome.split())


def sem_sigla(nome):
    """Nome sem a sigla no fim, entre parênteses ou colada com hífen."""
    return re.sub(r"-[A-Z]{2,}$", "", re.sub(r"\s*\([^)]*\)\s*$", "", espacos(nome)))


def chave(nome):
    """Nome sem o que não muda a identidade: caixa, acento, espaços, sigla no fim (ADR 0004, B)."""
    s = unicodedata.normalize("NFKD", sem_sigla(nome))
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


@dataclass(frozen=True)
class Decisao:
    linha: int
    tipo: str
    canonico: str | None
    sigla: str | None
    inicio: dt.date | None
    troca: dt.date | None
    ato: str | None
    motivo: str | None


@dataclass(frozen=True)
class Unidade:
    codigo: int
    nome: str
    sigla: str | None


@dataclass
class NomeAntigo:
    nome: str
    inicio: dt.date | None
    fim: dt.date
    ato: str
    linha: int


@dataclass
class Orgao:
    nome: str
    sigla: str | None
    codigo_siorg: int | None
    inicio: dt.date | None
    fonte_do_nome: str                      # "SIORG" ou "decisão (linha N)"
    nomes_antigos: list = field(default_factory=list)
    linhas: list = field(default_factory=list)


@dataclass
class Alias:
    linha: int
    nome: str
    chave: str
    orgao: str | None
    status: str                             # RESOLVIDO, INDEFINIDO, AMBIGUO
    como: str                               # como a linha chegou ao órgão, para o relatório
    motivo: str | None


@dataclass
class Resultado:
    arquivos: dict                          # rótulo -> (caminho, sha256)
    siorg: dict                             # metadados da consulta, do cabeçalho do recorte
    orgaos: list
    aliases: list
    chaves: int                             # chaves distintas nas linhas da planilha


def sha256(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _data(texto, linha, coluna):
    if not texto:
        return None
    try:
        return dt.date.fromisoformat(texto)
    except ValueError:
        raise ErroDeDecisao(f"decisão da linha {linha}: {coluna} {texto!r} não é data AAAA-MM-DD") from None


def ler_decisoes(caminho, nomes):
    """{linha: Decisao}, conferindo cada uma contra a planilha."""
    decisoes = {}
    with open(caminho, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if None in r or None in r.values():  # vírgula sem aspas desloca as colunas
                raise ErroDeDecisao(f"decisão da linha {r['linha']}: número de colunas errado "
                                    "(texto com vírgula precisa de aspas)")
            linha = int(r["linha"])
            if linha not in nomes:
                raise ErroDeDecisao(f"decisão para a linha {linha}, que não existe na aba {ABA!r}")
            if espacos(r["nome_na_planilha"]) != nomes[linha]:
                raise ErroDeDecisao(f"decisão da linha {linha}: o nome não bate com a planilha "
                                    f"({r['nome_na_planilha']!r} × {nomes[linha]!r})")
            if linha in decisoes:
                raise ErroDeDecisao(f"duas decisões para a linha {linha}")
            if r["tipo"] not in TIPOS:
                raise ErroDeDecisao(f"decisão da linha {linha}: tipo {r['tipo']!r} não é um de {TIPOS}")
            d = Decisao(linha, r["tipo"], r["canonico"].strip() or None, r["sigla"].strip() or None,
                        _data(r["inicio"], linha, "inicio"), _data(r["troca"], linha, "troca"),
                        r["ato"].strip() or None, r["motivo"].strip() or None)
            faltando = {"grafia": ("canonico", "motivo"), "renomeacao": ("canonico", "troca", "ato"),
                        "nome": ("canonico",), "indefinido": ("motivo",), "ambiguo": ("motivo",)}[d.tipo]
            if vazios := [c for c in faltando if getattr(d, c) is None]:
                raise ErroDeDecisao(f"decisão da linha {linha} ({d.tipo}) sem {', '.join(vazios)}")
            decisoes[linha] = d
    return decisoes


def ler_siorg(caminho):
    """Recorte do SIORG: ({chave: Unidade}, metadados). Chave com 0 ou várias unidades fica de fora."""
    meta, unidades, linhas = {}, {}, []
    with open(caminho, newline="", encoding="utf-8") as f:
        for x in f:
            if x.startswith("#"):  # "# chave=valor chave=valor": metadados da consulta
                meta.update(p.split("=", 1) for p in x[1:].split() if "=" in p)
            else:
                linhas.append(x)
    for r in csv.DictReader(linhas):
        if r["unidades"] == "1":
            unidades[r["chave"]] = Unidade(int(r["codigo"]), r["nome"].strip(), r["sigla"].strip() or None)
    return unidades, meta


def ler_nomes(planilha):
    aba = xlsx.ler(planilha).get(ABA)
    if aba is None:
        raise ErroDeDecisao(f"a planilha não tem a aba {ABA!r}")
    if any(set(v) != {"A"} for v in aba.linhas.values()):
        raise ErroDeDecisao(f"a aba {ABA!r} tem valor fora da coluna A: a estrutura mudou")
    return {n: espacos(aba.linhas[n]["A"].texto) for n in sorted(aba.linhas)}


def resolver(planilha, decisoes_csv, siorg_csv):
    nomes = ler_nomes(planilha)
    decisoes = ler_decisoes(decisoes_csv, nomes)
    siorg, meta = ler_siorg(siorg_csv)
    chaves = {n: chave(t) for n, t in nomes.items()}
    por_chave = {}
    for n in nomes:
        por_chave.setdefault(chaves[n], []).append(n)

    # Cada chave: pendente, redirecionada (grafia/renomeação) ou dona de um nome canônico.
    pendente, destino, proprio = {}, {}, {}
    for k, linhas in por_chave.items():
        ds = [decisoes[n] for n in linhas if n in decisoes]
        tipos = {d.tipo for d in ds}
        if len(tipos) > 1 or len({d.canonico for d in ds}) > 1:
            raise ErroDeDecisao(f"linhas {linhas} têm a mesma chave e decisões diferentes")
        d = ds[0] if ds else None
        if d and d.tipo in STATUS:
            pendente[k] = d
        elif d and d.tipo in ("grafia", "renomeacao"):
            destino[k] = d
        elif k in siorg:
            if d:
                raise ErroDeDecisao(f"linha {d.linha}: decisão \"nome\", mas o SIORG já dá o nome "
                                    f"({siorg[k].nome!r}); o ADR 0004 manda usar o do SIORG")
            proprio[k] = ("SIORG", siorg[k].nome)
        elif d:
            proprio[k] = (f"decisão (linha {d.linha})", d.canonico)
        else:
            raise ErroDeDecisao(f"linhas {linhas} ({nomes[linhas[0]]!r}): sem unidade no SIORG e sem "
                                "decisão; registre o nome (tipo \"nome\") ou a pendência")

    orgaos = {}
    for k, (fonte, nome) in sorted(proprio.items(), key=lambda x: x[1][1]):
        if nome in orgaos:
            raise ErroDeDecisao(f"dois grupos de linhas com o mesmo nome canônico {nome!r}: "
                                "junte-os com uma decisão \"grafia\"")
        u = siorg.get(k)
        dono = decisoes.get(next((n for n in por_chave[k] if n in decisoes), None))
        orgaos[nome] = Orgao(nome, u.sigla if u else dono.sigla, u.codigo if u else None,
                             dono.inicio if dono else None, fonte)
    for k, d in destino.items():
        if d.canonico not in orgaos:
            raise ErroDeDecisao(f"linha {d.linha}: {d.tipo} para {d.canonico!r}, que não é nome de nenhum órgão "
                                "(do SIORG ou de decisão \"nome\")")
        if d.tipo == "renomeacao":
            o = orgaos[d.canonico]
            antigo = sem_sigla(nomes[d.linha])
            o.nomes_antigos.append(NomeAntigo(antigo, d.inicio, d.troca - dt.timedelta(days=1), d.ato, d.linha))
            o.inicio = max(o.inicio or d.troca, d.troca)

    codigos = [o.codigo_siorg for o in orgaos.values() if o.codigo_siorg is not None]
    if len(codigos) != len(set(codigos)):
        raise ErroDeDecisao("dois órgãos com o mesmo código SIORG")

    aliases = []
    for n, t in nomes.items():
        k = chaves[n]
        if k in pendente:
            d = pendente[k]
            aliases.append(Alias(n, t, k, None, STATUS[d.tipo], d.tipo, d.motivo))
            continue
        if k in destino:
            d = destino[k]
            orgao, como, motivo = d.canonico, d.tipo, d.motivo or d.ato
        else:
            orgao = proprio[k][1]
            como = "mesma chave" if len(por_chave[k]) > 1 else "única"
            motivo = None
        orgaos[orgao].linhas.append(n)
        aliases.append(Alias(n, t, k, orgao, "RESOLVIDO", como, motivo))

    for o in orgaos.values():
        o.nomes_antigos.sort(key=lambda a: a.fim)
    arquivos = {"planilha": (str(planilha), sha256(planilha)), "decisões": (str(decisoes_csv), sha256(decisoes_csv)),
                "recorte do SIORG": (str(siorg_csv), sha256(siorg_csv))}
    return Resultado(arquivos, meta, sorted(orgaos.values(), key=lambda o: o.nome), aliases, len(por_chave))
