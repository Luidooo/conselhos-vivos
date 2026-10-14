"""Testes do oltp (#55), portados de internal/oltp/oltp_test.go. Cada um numa
transação desfeita (dbtest.CasoComBanco)."""

import datetime as dt
import io
import zipfile
from pathlib import Path

from conselhos.identidade import chave
from dbtest import CasoComBanco
from dou.materia import Materia, ler
from dou.oltp import Desfecho, Gravador, SemConteudo

AMOSTRAS = Path(__file__).parent.parent / "dou" / "amostras"


def construida(id, *categoria):
    """Matéria montada à mão: a persistência é exercitada sem ZIP e sem
    extração. O id começa em 900000000, como a amostra construída."""
    return Materia(entry=f"{id}.xml", id=id, pubDate=dt.date(2026, 10, 2), artCategory=list(categoria),
                   html="<p>Matéria construída para teste: não foi publicada.</p>")


def amostra_construida():
    """Lê conselho-construido.xml pelo `ler`, como uma matéria chega ao salvar."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("conselho-construido.xml", (AMOSTRAS / "conselho-construido.xml").read_bytes())
    buf.seek(0)
    for m, e in ler(zipfile.ZipFile(buf)):
        assert e is None, e
        return m


class Caso(CasoComBanco):
    def novo_orgao(self, nome):
        (id,) = self.conn.execute("INSERT INTO orgao DEFAULT VALUES RETURNING id").fetchone()
        self.conn.execute("INSERT INTO orgao_nome (orgao_id, nome) VALUES (%s, %s)", (id, nome))
        return id

    def conta(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()[0]


class Salvar(Caso):
    def test_grava_uma_materia_de_conselho_conhecido(self):
        item = amostra_construida()
        self.assertIs(Gravador(self.conn).salvar(item), Desfecho.GRAVADA)
        # O CONAMA é um dos 5 conselhos do sql/004: está lá só com as migrações.
        origem, versao, data, ementa, conteudo, orgao = self.conn.execute("""
            SELECT a.origem, a.versao, a.data_publicacao, a.ementa, a.conteudo, n.nome
              FROM ato a JOIN orgao_nome n ON n.orgao_id = a.orgao_id AND n.data_fim IS NULL
             WHERE a.id_dou = %s""", ("900000001",)).fetchone()
        self.assertEqual(origem, "DOU")
        self.assertEqual(versao, 1)
        self.assertEqual(data, dt.date(2026, 10, 2))
        self.assertEqual(orgao, "Conselho Nacional do Meio Ambiente")
        self.assertEqual(ementa, "Matéria construída para teste: não foi publicada.")
        self.assertEqual(conteudo, item.html)  # <Texto> como publicado, marcadores e tudo
        self.assertIn('<p class="assina">', conteudo)

    def test_ementa_vazia_fica_null(self):
        self.novo_orgao("Conselho Nacional de Teste da Persistência")
        self.assertIs(Gravador(self.conn).salvar(construida("900000010", "Ministério de Teste", "Conselho Nacional de Teste da Persistência")), Desfecho.GRAVADA)
        self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = '900000010' AND ementa IS NULL"), 1)

    def test_ementa_em_branco_fica_null(self):
        # Só espaços ou quebras de linha é tão vazia quanto nenhuma <Ementa>.
        self.novo_orgao("Conselho Nacional de Teste da Persistência")
        item = construida("900000012", "Ministério de Teste", "Conselho Nacional de Teste da Persistência")
        item.ementa = " \n\t "
        self.assertIs(Gravador(self.conn).salvar(item), Desfecho.GRAVADA)
        self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = '900000012' AND ementa IS NULL"), 1)

    def test_recusa_materia_sem_conteudo(self):
        item = construida("900000040", "Ministério de Teste", "Conselho de Teste")
        item.html = " \n"
        with self.assertRaises(SemConteudo):
            Gravador(self.conn).salvar(item)


class AchaOOrgao(Caso):
    PUBLICADO = "CONSELHO  NACIONAL DE TESTE DA PERSISTÊNCIA (CNTP)"

    def _confere(self, esperado):
        self.assertIs(Gravador(self.conn).salvar(construida("900000011", "Ministério de Teste", self.PUBLICADO)), Desfecho.GRAVADA)
        (got,) = self.conn.execute("SELECT orgao_id FROM ato WHERE id_dou = '900000011'").fetchone()
        self.assertEqual(got, esperado)

    def test_pelo_nome_atual_seja_qual_for_a_grafia(self):
        self._confere(self.novo_orgao("Conselho Nacional de Teste da Persistência"))

    def test_por_um_nome_que_ja_teve(self):
        id = self.novo_orgao("Conselho Nacional de Outro Nome")
        self.conn.execute("""INSERT INTO orgao_nome (orgao_id, nome, data_inicio, data_fim)
                             VALUES (%s, 'Conselho Nacional de Teste da Persistência', '2000-01-01', '2010-01-01')""", (id,))
        self._confere(id)

    def test_por_um_alias_resolvido(self):
        id = self.novo_orgao("Conselho Nacional de Outro Nome")
        self.conn.execute("""INSERT INTO orgao_alias (nome, chave, fonte, orgao_id, status)
                             VALUES ('Conselho Nacional de Teste da Persistencia', 'x', 'PLANILHA', %s, 'RESOLVIDO')""", (id,))
        self._confere(id)


class OrgaoDesconhecido(Caso):
    def test_enfileira_uma_vez(self):
        orgao = "Coordenação de Teste Que Não Existe"
        g = Gravador(self.conn)
        atos = self.conta("SELECT count(*) FROM ato")
        # Duas matérias do mesmo órgão, a segunda com o nome espaçado.
        for id, nome in [("900000020", orgao), ("900000021", "Coordenação de Teste  Que Não Existe")]:
            self.assertIs(g.salvar(construida(id, "Ministério de Teste", nome)), Desfecho.ORGAO_DESCONHECIDO)
        self.assertEqual(self.conta("SELECT count(*) FROM ato"), atos, "nada entra em ato")
        linhas = self.conn.execute("SELECT chave, status, motivo, orgao_id FROM orgao_alias WHERE fonte = 'DOU' AND nome = %s", (orgao,)).fetchall()
        self.assertEqual(len(linhas), 1, "uma linha para as duas")
        k, status, motivo, orgao_id = linhas[0]
        self.assertEqual(self.conta("SELECT count(*) FROM orgao_alias WHERE fonte = 'DOU' AND chave = %s", k), 1)
        self.assertEqual(k, chave(orgao))
        self.assertEqual(status, "INDEFINIDO")
        self.assertIsNone(orgao_id)
        self.assertIn("Ministério de Teste/" + orgao, motivo)

    def test_deixa_em_paz_um_nome_ja_a_espera(self):
        # Nome que a planilha deixou à espera aparece no DOU: continua fora de
        # ato, e a decisão que espera fica sendo a única, com seu status e motivo.
        esperando = "Conselho de Teste à Espera de Decisão"
        self.conn.execute("""INSERT INTO orgao_alias (nome, chave, fonte, status, motivo)
                             VALUES (%s, %s, 'PLANILHA', 'AMBIGUO', 'dois conselhos possíveis: perguntar à pesquisadora')""",
                          (esperando, chave(esperando)))
        atos = self.conta("SELECT count(*) FROM ato")
        self.assertIs(Gravador(self.conn).salvar(construida("900000030", "Ministério de Teste", "CONSELHO DE TESTE À ESPERA DE DECISÃO (CTED)")), Desfecho.ORGAO_DESCONHECIDO)
        self.assertEqual(self.conta("SELECT count(*) FROM ato"), atos)
        self.assertEqual(self.conta("SELECT count(*) FROM orgao_alias WHERE chave = %s", chave(esperando)), 1, "nenhuma segunda linha ao lado da planilha")
        self.assertEqual(self.conta("SELECT count(*) FROM orgao_alias WHERE chave = %s AND fonte = 'PLANILHA' AND status = 'AMBIGUO'", chave(esperando)), 1)

    def test_nao_escolhe_entre_dois_orgaos(self):
        self.novo_orgao("Conselho de Teste Repetido")
        self.novo_orgao("CONSELHO DE TESTE REPETIDO (CTR)")
        self.assertIs(Gravador(self.conn).salvar(construida("900000030", "Ministério de Teste", "Conselho de Teste Repetido")), Desfecho.ORGAO_DESCONHECIDO)
        self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = '900000030'"), 0)
        self.assertEqual(self.conta("""SELECT count(*) FROM orgao_alias
                                       WHERE fonte = 'DOU' AND nome = 'Conselho de Teste Repetido' AND status = 'AMBIGUO' AND orgao_id IS NULL"""), 1)


class Reexecucao(Caso):
    def test_salvar_de_novo_nao_escreve(self):
        item = amostra_construida()
        g = Gravador(self.conn)
        self.assertIs(g.salvar(item), Desfecho.GRAVADA)
        self.assertIs(g.salvar(item), Desfecho.INALTERADA)
        self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = %s", item.id), 1)

    def test_nao_alterna_entre_duas_versoes_conhecidas(self):
        # O mesmo id com dois textos, de dois ZIPs (DO1 e DO1E, ou dois dias da
        # janela): com os dois dentro, rodar de novo não escreve nada.
        a = amostra_construida()
        b = amostra_construida()
        b.html += "<p>Texto da outra edição.</p>"
        g = Gravador(self.conn)
        esperados = [Desfecho.GRAVADA, Desfecho.VERSAO_NOVA, Desfecho.INALTERADA, Desfecho.INALTERADA]
        for i, esperado in enumerate(esperados):
            self.assertIs(g.salvar(b if i % 2 else a), esperado, f"save {i + 1}")
        self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = %s", a.id), 2)

    def test_mudanca_so_de_orgao_nao_gera_versao(self):
        # O órgão é a decisão de identidade (ADR 0004), não o que o DOU publicou.
        nome = "Conselho Nacional de Teste da Persistência"
        primeiro = self.novo_orgao(nome)
        item = construida("900000050", "Ministério de Teste", nome)
        self.assertIs(Gravador(self.conn).salvar(item), Desfecho.GRAVADA)
        self.conn.execute("UPDATE orgao_nome SET nome = 'Conselho de Outro Nome' WHERE orgao_id = %s", (primeiro,))
        self.novo_orgao(nome)
        self.assertIs(Gravador(self.conn).salvar(item), Desfecho.INALTERADA)
        self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = '900000050'"), 1)

    def test_republicada_vira_versao_nova(self):
        mudancas = {
            "o texto": lambda m: setattr(m, "html", m.html + "<p>Republicada por incorreção.</p>"),
            "a ementa": lambda m: setattr(m, "ementa", "Ementa republicada."),
            "a data": lambda m: setattr(m, "pubDate", m.pubDate + dt.timedelta(days=1)),
        }
        for nome, muda in mudancas.items():
            with self.subTest(nome):
                self.conn.rollback()  # cada caso parte do banco limpo
                original = amostra_construida()
                g = Gravador(self.conn)
                g.salvar(original)
                republicada = amostra_construida()
                muda(republicada)
                self.assertIs(g.salvar(republicada), Desfecho.VERSAO_NOVA)
                self.assertIs(g.salvar(republicada), Desfecho.INALTERADA)
                (versoes,) = self.conn.execute("SELECT string_agg(versao::text, ',' ORDER BY versao) FROM ato WHERE id_dou = %s", (original.id,)).fetchone()
                self.assertEqual(versoes, "1,2")
                self.assertEqual(self.conta("SELECT count(*) FROM ato WHERE id_dou = %s AND versao = 1 AND conteudo = %s", original.id, original.html), 1, "a primeira versão fica como estava")


class ChaveDoOrgao(Caso):
    def test_a_chave_bate_com_todas_as_de_orgao_alias(self):
        # O risco Unicode do #40: parte das chaves em orgao_alias foi gravada
        # pelo Go. Recalcular todas em Python e conferir é a verificação da #55.
        linhas = self.conn.execute("SELECT nome, chave, fonte FROM orgao_alias").fetchall()
        self.assertGreater(len(linhas), 0, "rode make carga")
        for nome, k, fonte in linhas:
            with self.subTest(nome=nome, fonte=fonte):
                self.assertEqual(chave(nome), k)
