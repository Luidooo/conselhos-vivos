"""As matérias de uma edição do DOU: um ZIP entra, uma Materia por XML sai (o
par do internal/article do Go). Não fala com rede nem com banco, então se
testa com arquivos de amostra e sem credencial.
"""

import datetime as dt
import html.parser
import posixpath
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field


class NaoEXML(Exception):
    """Entrada do ZIP que não é uma matéria. O INLABS põe as imagens de cada
    matéria no mesmo ZIP, então isto é rotina: conta-se, loga-se, segue-se.
    Uma entrada de diretório também recebe isto: não deveria acontecer, e
    assim quem chama loga em vez de a caminhada esconder."""


class Malformada(Exception):
    """XML que não lê como uma matéria do DOU."""


class ErroDeEntrada(Exception):
    """Falha confinada a uma entrada do ZIP. Diz qual, para um arquivo ruim
    ser achado sem abrir a edição à mão. A causa fica em __cause__."""

    def __init__(self, entrada, causa):
        super().__init__(f"{entrada}: {causa}")
        self.entrada = entrada
        self.__cause__ = causa


@dataclass
class Materia:
    """Uma matéria, com os atributos do <article> e os campos do <body>, sob
    os nomes do XML. Os identificadores ficam como texto: ato.id_dou é
    VARCHAR. editionNumber é texto porque edição extra se numera "185-A"."""

    entry: str = ""
    id: str = ""
    idMateria: str = ""
    pubName: str = ""
    artType: str = ""
    pubDate: dt.date = None
    numberPage: str = ""
    editionNumber: str = ""
    artClass: str = ""
    # artCategory partido em "/": a hierarquia do órgão, do ministério para
    # baixo. O conselho, quando há, é o último nível.
    artCategory: list = field(default_factory=list)
    identifica: str = ""
    ementa: str = ""
    titulo: str = ""
    subTitulo: str = ""
    # <Texto> como publicado, a fonte da verdade: os <p class="assina"> e
    # <p class="identifica"> só sobrevivem aqui. texto é o mesmo conteúdo
    # como texto puro, derivado por extrair_texto.
    html: str = ""
    texto: str = ""

    def orgao(self):
        """O último nível da hierarquia: quem publicou. Casá-lo com um
        conselho é trabalho da persistência."""
        return self.artCategory[-1] if self.artCategory else ""

    def como_json(self, com_html=False):
        """O dicionário que o extract imprime, na ordem e com os nomes do Go."""
        d = {
            "entry": self.entry, "id": self.id, "idMateria": self.idMateria, "pubName": self.pubName,
            "artType": self.artType, "pubDate": self.pubDate.isoformat(), "numberPage": self.numberPage,
            "editionNumber": self.editionNumber, "artClass": self.artClass, "artCategory": self.artCategory,
            "identifica": self.identifica, "ementa": self.ementa, "titulo": self.titulo,
            "subTitulo": self.subTitulo,
        }
        if com_html and self.html:
            d["html"] = self.html
        d["texto"] = self.texto
        return d


def ler(edicao):
    """Percorre a edição (um zipfile.ZipFile) e produz (Materia, None) por XML,
    abrindo uma entrada de cada vez: um dia tem ~300, um mês ~9.000.

    Uma falha numa entrada sai como (None, ErroDeEntrada) e a caminhada segue:
    um arquivo ruim nunca custa o resto da edição.
    """
    for info in edicao.infolist():
        try:
            yield _ler_entrada(edicao, info), None
        except (NaoEXML, Malformada) as e:
            yield None, ErroDeEntrada(info.filename, e)


def _ler_entrada(edicao, info):
    # Em qualquer profundidade, como o Ro-dou lê: nada promete um ZIP plano.
    if info.is_dir() or posixpath.splitext(info.filename)[1].lower() != ".xml":
        raise NaoEXML("not an XML file")
    with edicao.open(info) as f:
        materia = parse(f)
    materia.entry = info.filename
    return materia


def parse(fonte):
    """Lê o XML de uma matéria. Recusa o que a persistência não conseguiria
    chavear nem atribuir: sem id, sem data de publicação, sem artCategory."""
    try:
        raiz = ET.parse(fonte).getroot()
    except ET.ParseError as e:
        raise Malformada(f"not a DOU article: {e}") from e
    # A raiz não é conferida; tem de haver exatamente um <article> sob ela.
    artigos = raiz.findall("article")
    if len(artigos) != 1:
        raise Malformada(f"not a DOU article: want one <article>, found {len(artigos)}")
    a = artigos[0]
    attr = lambda nome: (a.get(nome) or "").strip()
    campo = lambda nome: ((a.findtext(f"body/{nome}")) or "").strip()

    if not attr("id"):
        raise Malformada("not a DOU article: <article> has no id")
    try:
        publicada = dt.datetime.strptime(attr("pubDate"), "%d/%m/%Y").date()
    except ValueError:
        raise Malformada(f"not a DOU article: pubDate {a.get('pubDate')!r} is not DD/MM/YYYY") from None
    categoria = partir_categoria(a.get("artCategory") or "")
    if not categoria:
        raise Malformada("not a DOU article: <article> has no artCategory")

    texto_html = a.findtext("body/Texto") or ""
    return Materia(
        id=attr("id"), idMateria=attr("idMateria"), pubName=attr("pubName"), artType=attr("artType"),
        pubDate=publicada, numberPage=attr("numberPage"), editionNumber=attr("editionNumber"),
        artClass=attr("artClass"), artCategory=categoria,
        identifica=campo("Identifica"), ementa=campo("Ementa"), titulo=campo("Titulo"),
        subTitulo=campo("SubTitulo"),
        html=texto_html, texto=extrair_texto(texto_html),
    )


def partir_categoria(bruto):
    """Toda a resolução de órgão que há aqui: partir em "/", sem PLN. Níveis
    vazios — barra dupla ou final — caem."""
    return [n.strip() for n in bruto.split("/") if n.strip()]


_QUEBRAM_LINHA = {"p", "br", "div", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"}
_CELULAS = {"td", "th"}


class _Texto(html.parser.HTMLParser):
    """Uma linha por parágrafo, entidades decodificadas, brancos colapsados;
    uma linha da tabela fica numa linha, células separadas por " | ". Nunca
    falha: HTML malformado ainda rende as palavras."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.linhas = []
        self.atual = []

    def _quebra(self):
        texto = " ".join("".join(self.atual).split())
        if texto:
            self.linhas.append(texto)
        self.atual = []

    def handle_starttag(self, tag, attrs):
        if tag in _QUEBRAM_LINHA:
            self._quebra()
        elif tag in _CELULAS and "".join(self.atual).strip():
            self.atual.append(" | ")

    def handle_startendtag(self, tag, attrs):
        if tag in _QUEBRAM_LINHA:
            self._quebra()

    def handle_endtag(self, tag):
        if tag in _QUEBRAM_LINHA:
            self._quebra()

    def handle_data(self, data):
        self.atual.append(data)

    def resultado(self):
        self._quebra()
        return "\n".join(self.linhas)


def extrair_texto(fragmento):
    p = _Texto()
    p.feed(fragmento)
    p.close()
    return p.resultado()
