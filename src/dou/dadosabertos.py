"""Um mês inteiro do Diário Oficial pelos dados abertos da Imprensa Nacional
(o par do internal/dadosabertos do Go): um ZIP por mês e seção, público (CC0),
sem login, com o mesmo XML do INLABS dentro, edições extras incluídas. O mês
sai cerca de duas semanas depois de acabar.

Só a Seção 1 é buscada: é onde saem os atos dos conselhos. Só biblioteca
padrão: urllib honra os proxies do ambiente, como o Go fazia.
"""

import datetime as dt
import html
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE_URL = "https://www.in.gov.br"

# A página que lista os ZIPs de um mês. Cada link leva o UUID do documento,
# então o endereço do ZIP não se monta: só se encontra.
LISTAGEM = "/acesso-a-informacao/dados-abertos/base-de-dados"

USER_AGENT = "conselhos-vivos-ingest/0.1"

# Teto do que se lê da página de listagem; ela tem ~150 KB.
MAX_LISTAGEM = 5 << 20

# Por operação de socket (conexão, cabeçalhos, cada bloco do corpo). O Go
# tinha também um teto de 10 min no mês inteiro; aqui não há teto global.
TIMEOUT = 30

# O mês do `mes` da listagem. A página aceita "Marco", mas é assim que ela
# mesma grafa.
MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

HREF = re.compile(r'href="([^"]+)"')

logger = logging.getLogger("dou.dadosabertos")


class NaoPublicado(Exception):
    """A listagem ainda não traz o ZIP do mês: o corrente, ou o anterior
    antes de meados do mês."""


class HostDiferente(Exception):
    """A página aponta o ZIP para outro site. Ela decide o que se baixa, então
    só pode apontar de volta para o site de onde veio."""


class StatusInesperado(Exception):
    pass


@dataclass(frozen=True)
class Mes:
    ano: int
    mes: int

    @classmethod
    def parse(cls, texto):
        """Aceita uma grafia e nenhuma outra: AAAA-MM."""
        # strptime aceitaria "2026-8"; o Go, não. A regex fixa os dígitos e o
        # strptime valida o mês.
        if not isinstance(texto, str) or not re.fullmatch(r"\d{4}-\d{2}", texto):
            raise ValueError("want a month as YYYY-MM, like 2026-08")
        try:
            d = dt.datetime.strptime(texto, "%Y-%m")
        except ValueError:
            raise ValueError("want a month as YYYY-MM, like 2026-08") from None
        return cls(d.year, d.month)

    def __str__(self):
        return f"{self.ano:04d}-{self.mes:02d}"


def nome_do_zip(mes):
    """O nome como a Imprensa Nacional publica, mantido em disco: a Seção 1 de
    agosto de 2026 é S01082026.zip."""
    return f"S01{mes.mes:02d}{mes.ano:04d}.zip"


def link_para(pagina, nome, base):
    """Entre os links da página, o do ZIP chamado `nome`: o nome é um segmento
    do caminho, seguido do UUID do documento."""
    base_host = urllib.parse.urlsplit(base).netloc
    for m in HREF.finditer(pagina):
        href = html.unescape(m.group(1))
        caminho = urllib.parse.urlsplit(href).path
        if f"/{nome}/" not in caminho + "/":
            continue
        link = urllib.parse.urljoin(base, href)
        host = urllib.parse.urlsplit(link).netloc
        if host != base_host:
            raise HostDiferente(f"the link to {nome} points at {host}, not at {base_host}")
        return link
    raise NaoPublicado(f"{nome}: the month is not published in the open data yet")


class Cliente:
    """Fala com www.in.gov.br. `base_url` é parâmetro para um teste apontar
    um cliente de verdade a um servidor de teste."""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url

    def baixar_mes(self, mes, bronze):
        """Põe o ZIP da Seção 1 do mês no bronze, a menos que já esteja lá.
        Uma falha não deixa nada sob o nome do ZIP (o bronze só publica um ZIP
        inteiro), então rodar de novo é a retentativa.

        Devolve "baixada" ou "ja-baixada".
        """
        nome = nome_do_zip(mes)
        if bronze.tem(nome):
            logger.info("mes=%s zip=%s desfecho=ja-baixada", mes, nome)
            return "ja-baixada"

        link = self._achar_link(mes, nome)
        try:
            with self._get(link) as resp:
                if resp.status != 200:
                    raise StatusInesperado(f"downloading {nome}: unexpected status {resp.status}")
                recibo = bronze.salvar(nome, resp)
        except urllib.error.HTTPError as e:
            raise StatusInesperado(f"downloading {nome}: unexpected status {e.code}") from e
        logger.info("mes=%s zip=%s desfecho=baixada bytes=%d", mes, nome, recibo.tamanho)
        return "baixada"

    def _achar_link(self, mes, nome):
        query = urllib.parse.urlencode({"ano": str(mes.ano), "mes": MESES[mes.mes]})
        listagem = f"{self.base_url}{LISTAGEM}?{query}"
        try:
            with self._get(listagem) as resp:
                if resp.status != 200:
                    raise StatusInesperado(f"reading the listing of {mes}: unexpected status {resp.status}")
                pagina = resp.read(MAX_LISTAGEM).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raise StatusInesperado(f"reading the listing of {mes}: unexpected status {e.code}") from e
        return link_para(pagina, nome, listagem)

    def _get(self, endereco):
        # Sem Accept o www.in.gov.br responde 403; "*/*" é o que um cliente que
        # aceita qualquer tipo manda, e o User-Agent continua sendo o nosso.
        req = urllib.request.Request(endereco, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        return urllib.request.urlopen(req, timeout=TIMEOUT)
