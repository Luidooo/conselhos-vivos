"""Testes do parser de matérias (#54), portados de internal/article/article_test.go.

As amostras estão em tests/dou/amostras/ (ver o README de lá).
"""

import datetime as dt
import io
import unittest
import zipfile
from pathlib import Path

from dou.materia import (ErroDeEntrada, Malformada, Materia, NaoEXML, extrair_texto, ler, parse,
                         partir_categoria)

AMOSTRAS = Path(__file__).parent / "amostras"


def amostra(nome):
    return nome, (AMOSTRAS / nome).read_bytes()


def edicao(*entradas):
    """Um ZIP de verdade, em memória, para `ler` ser exercitado nas mesmas
    estruturas que uma edição baixada lhe dá."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for nome, conteudo in entradas:
            z.writestr(nome, conteudo)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def coleta(z):
    materias, erros = [], []
    for m, e in ler(z):
        (erros if e is not None else materias).append(e if e is not None else m)
    return materias, erros


class ParseAmostraReal(unittest.TestCase):
    def test_campo_a_campo_com_bom_e_crlf(self):
        materias, erros = coleta(edicao(amostra("515_20190507_11615606.xml")))
        self.assertEqual(erros, [])
        self.assertEqual(len(materias), 1)
        m = materias[0]
        self.assertEqual(m.entry, "515_20190507_11615606.xml")
        self.assertEqual(m.id, "8724946")
        self.assertEqual(m.idMateria, "11615606")
        self.assertEqual(m.pubName, "DO1")
        self.assertEqual(m.artType, "Alvará")
        self.assertEqual(m.pubDate, dt.date(2019, 5, 7))
        self.assertEqual(m.numberPage, "25")
        self.assertEqual(m.editionNumber, "86")
        self.assertEqual(m.artClass, "00018:00027:00002:00107:00000:00000:00000:00000:00000:00000:00004:00001")
        self.assertEqual(m.artCategory, [
            "Ministério da Justiça e Segurança Pública", "Polícia Federal", "Diretoria Executiva",
            "Coordenação-Geral de Controle de Serviços e Produtos"])
        self.assertEqual(m.orgao(), "Coordenação-Geral de Controle de Serviços e Produtos")
        self.assertEqual(m.identifica, "ALVARÁ Nº 2.282, DE 15 DE ABRIL DE 2019")
        self.assertEqual(m.ementa, "")
        self.assertEqual(m.titulo, "")
        self.assertEqual(m.subTitulo, "")
        self.assertTrue(m.html.startswith('<p></p><p class="identifica">'), "o HTML fica como publicado")
        self.assertIn('<p class="assina">LICINIO NUNES DE MORAES NETTO</p>', m.html)
        self.assertTrue(m.texto.startswith("ALVARÁ Nº 2.282, DE 15 DE ABRIL DE 2019\nO(A) COORDENADOR(A)-GERAL"))
        self.assertTrue(m.texto.endswith("\nLICINIO NUNES DE MORAES NETTO"))


class ParseConselho(unittest.TestCase):
    def test_conselho_construido(self):
        materias, erros = coleta(edicao(amostra("conselho-construido.xml")))
        self.assertEqual(erros, [])
        m = materias[0]
        self.assertEqual(m.artCategory, ["Ministério do Meio Ambiente e Mudança do Clima", "Conselho Nacional do Meio Ambiente"])
        self.assertEqual(m.orgao(), "Conselho Nacional do Meio Ambiente")
        self.assertEqual(m.editionNumber, "187-A", "o número de uma edição extra não é inteiro")
        self.assertEqual(m.ementa, "Matéria construída para teste: não foi publicada.")
        self.assertEqual(m.texto, "\n".join([
            "RESOLUÇÃO Nº 0, DE 1º DE OUTUBRO DE 2026",
            "O CONSELHO NACIONAL DO MEIO AMBIENTE & seus membros, resolve:",
            "Art. | Prazo",
            "1º | 30 dias",
            "Art. 2º Esta Resolução entra em vigor",
            "na data de sua publicação.",
            "FULANO DE TAL",
        ]))


class Ler(unittest.TestCase):
    def test_sobrevive_a_entradas_ruins(self):
        # A edição segue além do que não consegue ler, e diz qual arquivo foi.
        materias, erros = coleta(edicao(
            amostra("515_20190507_11615606.xml"), amostra("malformado.xml"),
            ("imagens/figura.jpg", b"\xff\xd8\xff"), amostra("529_20210601_13490090.xml")))
        self.assertEqual([m.id for m in materias], ["8724946", "20001323"], "as entradas em volta das ruins são lidas")
        self.assertEqual(len(erros), 2)
        self.assertIsInstance(erros[0], ErroDeEntrada)
        self.assertEqual(erros[0].entrada, "malformado.xml")
        self.assertIsInstance(erros[0].__cause__, Malformada)
        self.assertIn("malformado.xml", str(erros[0]))
        self.assertEqual(erros[1].entrada, "imagens/figura.jpg")
        self.assertIsInstance(erros[1].__cause__, NaoEXML)

    def test_acha_xml_em_qualquer_profundidade(self):
        nome, conteudo = amostra("529_20210601_13490090.xml")
        materias, erros = coleta(edicao(("2021-06-01-DO2/" + nome, conteudo)))
        self.assertEqual(erros, [])
        self.assertEqual(materias[0].entry, "2021-06-01-DO2/529_20210601_13490090.xml")

    def test_reporta_um_diretorio(self):
        # Um diretório não deveria estar numa edição; quando está, é reportado
        # como qualquer entrada que não é matéria, para quem chama logar.
        materias, erros = coleta(edicao(("2021-06-01-DO2/", b""), amostra("529_20210601_13490090.xml")))
        self.assertEqual(len(materias), 1, "o diretório não para a caminhada")
        self.assertEqual(len(erros), 1)
        self.assertEqual(erros[0].entrada, "2021-06-01-DO2/")
        self.assertIsInstance(erros[0].__cause__, NaoEXML)

    def test_para_quando_quem_chama_para(self):
        z = edicao(amostra("515_20190507_11615606.xml"), amostra("529_20210601_13490090.xml"))
        vistas = 0
        for _ in ler(z):
            vistas += 1
            break
        self.assertEqual(vistas, 1)


class ParseRecusa(unittest.TestCase):
    # O que a persistência não conseguiria chavear nem atribuir é recusado,
    # não passado adiante em branco.
    casos = {
        "sem id": '<xml><article pubDate="02/10/2026" artCategory="A/B"/></xml>',
        "sem artCategory": '<xml><article id="1" pubDate="02/10/2026"/></xml>',
        "só barras": '<xml><article id="1" pubDate="02/10/2026" artCategory=" / "/></xml>',
        "pubDate mês primeiro": '<xml><article id="1" pubDate="10/31/2026" artCategory="A/B"/></xml>',
        "dois articles": '<xml><article id="1" pubDate="02/10/2026" artCategory="A"/><article id="2" pubDate="02/10/2026" artCategory="A"/></xml>',
        "nenhum article": "<xml></xml>",
        "cortado": "<xml><article id=",
    }

    def test_recusa_incompletas(self):
        for nome, xml in self.casos.items():
            with self.subTest(nome):
                with self.assertRaises(Malformada):
                    parse(io.BytesIO(xml.encode()))


class Miudos(unittest.TestCase):
    def test_partir_categoria_descarta_niveis_vazios(self):
        self.assertEqual(partir_categoria(" Ministério // Conselho/ "), ["Ministério", "Conselho"])

    def test_orgao_sem_categoria(self):
        self.assertEqual(Materia().orgao(), "")

    def test_erro_de_entrada_guarda_a_causa(self):
        e = ErroDeEntrada("a.xml", Malformada("not a DOU article"))
        self.assertIsInstance(e.__cause__, Malformada)
        self.assertEqual(str(e), "a.xml: not a DOU article")

    def test_extrair_texto_nunca_falha(self):
        self.assertEqual(extrair_texto("<p>a<b>b</p><p"), "ab")
        self.assertEqual(extrair_texto(""), "")


if __name__ == "__main__":
    unittest.main()
