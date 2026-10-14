"""Grava uma matéria do DOU no banco de curadoria: uma linha em `ato`,
insert-only (ADR 0001), sob o órgão que o artCategory nomeia (o par do
internal/oltp do Go).

Não decide nada sobre a classificação: isso fica com a planilha e a curadoria
humana (ADR 0003). A chave do órgão é a mesma da carga: `conselhos.identidade`
— um lugar só, e não mais dois (#55).
"""

import enum

from conselhos.identidade import chave, espacos


class SemConteudo(Exception):
    """Matéria com <Texto> vazio. `ato` só aceita uma linha do DOU com o
    conteúdo, e uma string vazia satisfaria a restrição sem honrá-la."""


class Desfecho(enum.Enum):
    GRAVADA = "gravada"              # vista pela primeira vez: versão 1
    VERSAO_NOVA = "versao-nova"      # já estava e voltou diferente: republicada
    INALTERADA = "inalterada"        # já estava como está: nada é escrito
    ORGAO_DESCONHECIDO = "orgao-desconhecido"  # fora de ato; o órgão vai para a fila


# Um statement só, para a conferência e o insert verem as mesmas linhas. Duas
# execuções disputando a mesma matéria ainda não ganham as duas: a
# uq_ato_dou_versao recusa a segunda, que falha e é rodada de novo. Copiado
# literal do Go; só o placeholder muda ($n -> %(nome)s).
_GRAVAR = """
    WITH versions AS (
        SELECT versao,
               data_publicacao = %(data)s AND ementa IS NOT DISTINCT FROM NULLIF(%(ementa)s, '')
                 AND conteudo = %(conteudo)s AS same
          FROM ato
         WHERE origem = 'DOU' AND id_dou = %(id)s
    )
    INSERT INTO ato (origem, id_dou, versao, orgao_id, data_publicacao, ementa, conteudo)
    SELECT 'DOU', %(id)s, COALESCE((SELECT max(versao) FROM versions), 0) + 1, %(orgao)s, %(data)s,
           NULLIF(%(ementa)s, ''), %(conteudo)s
     WHERE NOT EXISTS (SELECT 1 FROM versions WHERE same)
    RETURNING versao
"""

_ENFILEIRAR = """
    INSERT INTO orgao_alias (nome, chave, fonte, status, motivo)
    VALUES (%s, %s, 'DOU', %s, %s)
    ON CONFLICT (fonte, nome) DO NOTHING
"""


class Gravador:
    """Grava matérias contra os órgãos conhecidos quando foi aberto."""

    def __init__(self, conn):
        self.conn = conn
        # chave -> orgao.id. Uma chave que nomeia mais de um órgão vai para
        # `ambiguos`: nunca se resolve sozinha.
        self.orgaos = {}
        self.ambiguos = set()
        # Chaves já em orgao_alias sem órgão, de qualquer fonte: as achadas na
        # abertura e as enfileiradas desde então. Nome à espera de decisão não
        # é enfileirado duas vezes.
        self.espera = set()
        self._abrir()

    def _abrir(self):
        """Lê a identidade dos órgãos: todo nome que um órgão tem ou teve
        (orgao_nome), toda grafia resolvida e toda grafia ainda à espera de
        decisão (orgao_alias)."""
        linhas = self.conn.execute("""
            SELECT orgao_id, nome FROM orgao_nome
            UNION
            SELECT orgao_id, nome FROM orgao_alias WHERE status = 'RESOLVIDO'""").fetchall()
        for orgao_id, nome in linhas:
            k = chave(nome)
            if k in self.orgaos and self.orgaos[k] != orgao_id:
                self.ambiguos.add(k)
            self.orgaos[k] = orgao_id
        for k in self.ambiguos:
            self.orgaos.pop(k, None)
        pendentes = self.conn.execute("SELECT nome FROM orgao_alias WHERE status <> 'RESOLVIDO'").fetchall()
        self.espera = {chave(nome) for (nome,) in pendentes}

    def salvar(self, m):
        """Grava uma matéria. Com órgão conhecido vira uma linha em ato: origem
        DOU, o id do article como id_dou e o <Texto> como publicado em
        conteudo; <Ementa> só com brancos é guardada como NULL, como uma vazia.
        Com órgão desconhecido fica de fora e o órgão é enfileirado.

        Pode rodar de novo. A matéria é comparada com TODAS as versões já
        gravadas, no que o DOU publicou: data, ementa e conteúdo. Igual a
        alguma, nada acontece; diferente de todas, entra como a versão
        seguinte. Comparar só com a última alternaria entre dois ZIPs que
        trazem o mesmo id com dois textos (DO1 e DO1E, ou dois dias da janela),
        somando duas versões a cada execução. O órgão não entra na comparação:
        é a decisão de identidade (ADR 0004), e resolver um nome não é
        republicação.
        """
        if not m.html.strip():
            raise SemConteudo(f"{m.entry}: matéria has no <Texto>")

        orgao = espacos(m.orgao())
        k = chave(orgao)
        if k not in self.orgaos:
            self._enfileirar(m, orgao, k)
            return Desfecho.ORGAO_DESCONHECIDO

        linha = self.conn.execute(_GRAVAR, {
            "id": m.id, "orgao": self.orgaos[k], "data": m.pubDate,
            "ementa": m.ementa.strip(), "conteudo": m.html,
        }).fetchone()
        if linha is None:
            return Desfecho.INALTERADA
        return Desfecho.VERSAO_NOVA if linha[0] > 1 else Desfecho.GRAVADA

    def _enfileirar(self, m, orgao, k):
        """Registra o nome do órgão em orgao_alias, sem órgão e com o motivo.
        Uma vez por chave: um nome já à espera de decisão, venha de onde vier,
        mantém o status e o motivo que recebeu. O "ambíguo, perguntar à
        pesquisadora" da planilha não é respondido por uma segunda linha
        dizendo "não reconhecido"."""
        if k in self.espera:
            return
        status, motivo = "INDEFINIDO", "órgão não reconhecido na ingestão do DOU"
        if k in self.ambiguos:
            status, motivo = "AMBIGUO", "a chave casa com mais de um órgão"
        motivo += "; artCategory: " + "/".join(m.artCategory)
        self.conn.execute(_ENFILEIRAR, (orgao, k, status, motivo))
        self.espera.add(k)
