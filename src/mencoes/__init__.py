"""Menções aos conselhos em matérias do DOU publicadas por outros órgãos: um segundo sinal de vida de cada
conselho, além do que ele mesmo publica (plano docs/planos/2026-11-09-mencoes-de-terceiros.md).

Só biblioteca padrão: a leitura das matérias é do dou.materia, a gravação na silver fica em mencoes.silver.
"""

import re
import unicodedata

# A janela onde o nome é procurado: título, ementa, identificação e o começo do texto. No texto inteiro o nome
# aparece de passagem (uma portaria de carreira que cita o conselho numa lista); no começo, é o assunto do ato.
JANELA_TEXTO = 600

# O assunto, pela mesma janela, na ordem de prioridade: o primeiro que casa vale.
ASSUNTOS = [
    ("extinção", r"\bextin(gue|guir|cao|to|ta)\b|\brevoga\b.{0,80}\b(institui|cria)"),
    ("criação", r"\b(institui|cria|instituir|criar)\b.{0,40}\bconselho\b"),
    ("estrutura", r"\bestrutura regimental\b"),
    ("regimento", r"\bregimento interno\b"),
    ("homologação", r"\bhomolog\w*"),
    ("composição", r"\b(designa\w*|nomeia|nomear|dispens\w*|composicao|membros?|conselheir\w*|eleicao|eleitoral|mandatos?)\b"),
]


def normalizar(texto):
    """Minúsculas, sem acento e sem pontuação, com um espaço só entre as palavras."""
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", texto)).strip()


def janela(materia):
    """O trecho onde o nome conta como assunto do ato, normalizado."""
    return normalizar(" ".join([materia.titulo, materia.ementa, materia.identifica, materia.texto[:JANELA_TEXTO]]))


def assunto(trecho):
    for nome, regra in ASSUNTOS:
        if re.search(regra, trecho):
            return nome
    return "outro"


class Casador:
    """Acha, num trecho normalizado, quais órgãos são citados pelo nome. Recebe (orgao_id, nome) de todos os
    nomes que o órgão já teve: o nome antigo também conta."""

    def __init__(self, nomes):
        self.orgao_de = {}
        for orgao_id, nome in nomes:
            chave = normalizar(nome)
            if chave:
                self.orgao_de[chave] = orgao_id
        # o nome mais longo primeiro: "conselho nacional de saude" não pode engolir "conselho nacional de saude suplementar"
        alternativas = sorted(self.orgao_de, key=len, reverse=True)
        self.padrao = re.compile(r"\b(" + "|".join(re.escape(a) for a in alternativas) + r")\b") if alternativas else None

    def citados(self, trecho):
        """{orgao_id: nome citado}, um por órgão."""
        if not self.padrao:
            return {}
        achados = {}
        for nome in self.padrao.findall(trecho):
            achados.setdefault(self.orgao_de[nome], nome)
        return achados

    def publicadores(self, materia):
        """Os orgao_id de todos os níveis da hierarquia de quem publicou: a câmara de um conselho
        ("Ministério/Conselho/Câmara") também é o próprio conselho."""
        return {self.orgao_de[n] for n in map(normalizar, materia.artCategory) if n in self.orgao_de}


def mencoes(materia, casador):
    """As menções de uma matéria: uma por órgão citado que não seja o próprio publicador."""
    trecho = janela(materia)
    citados = casador.citados(trecho)
    if not citados:
        return []
    proprios = casador.publicadores(materia)
    tema = assunto(trecho)
    return [
        {
            "id_dou": materia.id,
            "orgao_id": orgao_id,
            "nome_citado": nome,
            "data_publicacao": materia.pubDate,
            "tipo_ato": materia.artType,
            "publicador": "/".join(materia.artCategory),
            "titulo": materia.identifica or materia.titulo,
            "ementa": materia.ementa,
            "assunto": tema,
        }
        for orgao_id, nome in sorted(citados.items())
        if orgao_id not in proprios
    ]
