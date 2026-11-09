"""A extração das menções (src/mencoes): o casamento do nome na janela, o descarte da matéria do próprio
conselho e o assunto. Sem banco e sem Delta: matérias montadas à mão.
Roda com make test-mencoes, ou no host: PYTHONPATH=src python3 -m unittest discover -s tests/mencoes
"""

import datetime as dt
import unittest

from dou.materia import Materia
from mencoes import JANELA_TEXTO, Casador, assunto, janela, mencoes, normalizar

NOMES = [
    (1, "Conselho Nacional de Educação"),
    (2, "Conselho Nacional de Saúde"),
    (3, "Conselho Nacional de Saúde Suplementar"),
    (4, "Conselho Nacional dos Direitos da Pessoa Idosa"),
    (4, "Conselho Nacional dos Direitos do Idoso"),  # o nome antigo do mesmo órgão
]


def materia(texto="", ementa="", categoria=("Ministério da Educação",), tipo="Portaria", identifica="PORTARIA Nº 1"):
    return Materia(id="900", pubDate=dt.date(2026, 8, 3), artType=tipo, artCategory=list(categoria),
                   identifica=identifica, ementa=ementa, texto=texto)


class Normalizar(unittest.TestCase):
    def test_tira_acento_pontuacao_e_espaco(self):
        self.assertEqual(normalizar("  Conselho  Nacional de Educação - CNE "), "conselho nacional de educacao cne")


class Casamento(unittest.TestCase):
    def setUp(self):
        self.casador = Casador(NOMES)

    def test_acha_o_conselho_na_ementa(self):
        m = materia(ementa="Homologa o Parecer do Conselho Nacional de Educação sobre diretrizes.")
        self.assertEqual([x["orgao_id"] for x in mencoes(m, self.casador)], [1])

    def test_nome_antigo_conta_para_o_mesmo_orgao(self):
        m = materia(ementa="Designa membros do Conselho Nacional dos Direitos do Idoso.")
        self.assertEqual([(x["orgao_id"], x["nome_citado"]) for x in mencoes(m, self.casador)],
                         [(4, "conselho nacional dos direitos do idoso")])

    def test_nome_mais_longo_ganha(self):
        m = materia(ementa="Aprova o regimento do Conselho Nacional de Saúde Suplementar.")
        self.assertEqual([x["orgao_id"] for x in mencoes(m, self.casador)], [3])

    def test_citacao_fora_da_janela_nao_conta(self):
        m = materia(texto="x" * JANELA_TEXTO + " ouvido o Conselho Nacional de Educação")
        self.assertEqual(mencoes(m, self.casador), [])

    def test_materia_do_proprio_conselho_nao_e_mencao(self):
        m = materia(ementa="O Conselho Nacional de Saúde aprova a pauta.", categoria=("Ministério da Saúde", "Conselho Nacional de Saúde"))
        self.assertEqual(mencoes(m, self.casador), [])

    def test_camara_do_proprio_conselho_tambem_e_o_proprio(self):
        # Achado na medição: a Súmula de Pareceres sai em "Ministério da Educação/Conselho Nacional de Educação/Câmara".
        m = materia(ementa="Súmula de pareceres do Conselho Nacional de Educação.",
                    categoria=("Ministério da Educação", "Conselho Nacional de Educação", "Câmara de Educação Superior"))
        self.assertEqual(mencoes(m, self.casador), [])

    def test_conselho_que_cita_outro_conselho_conta(self):
        m = materia(ementa="Recomenda ao Conselho Nacional de Educação a revisão.", categoria=("Ministério da Saúde", "Conselho Nacional de Saúde"))
        self.assertEqual([x["orgao_id"] for x in mencoes(m, self.casador)], [1])

    def test_dois_conselhos_viram_duas_mencoes(self):
        m = materia(ementa="Conselho Nacional de Educação e Conselho Nacional de Saúde em ato conjunto.")
        self.assertEqual(sorted(x["orgao_id"] for x in mencoes(m, self.casador)), [1, 2])


class Assunto(unittest.TestCase):
    def caso(self, texto):
        return assunto(normalizar(texto))

    def test_cada_assunto(self):
        self.assertEqual(self.caso("Extingue o Conselho Nacional de X"), "extinção")
        self.assertEqual(self.caso("Institui o Conselho Nacional de X"), "criação")
        self.assertEqual(self.caso("Aprova a Estrutura Regimental do Ministério"), "estrutura")
        self.assertEqual(self.caso("Aprova o Regimento Interno do Conselho"), "regimento")
        self.assertEqual(self.caso("Homologa o Parecer CNE/CES nº 1"), "homologação")
        self.assertEqual(self.caso("Designa os membros titulares e suplentes"), "composição")
        self.assertEqual(self.caso("Dispõe sobre prazos"), "outro")

    def test_extincao_ganha_de_composicao(self):
        self.assertEqual(self.caso("Extingue o conselho e dispensa os membros"), "extinção")


class Janela(unittest.TestCase):
    def test_junta_titulo_ementa_e_o_comeco_do_texto(self):
        m = materia(ementa="Ementa", texto="Começo do texto" + " fim" * 1000)
        trecho = janela(m)
        self.assertTrue(trecho.startswith("ementa portaria no 1 comeco do texto"))
        self.assertLess(len(trecho), JANELA_TEXTO + 50)


if __name__ == "__main__":
    unittest.main()
