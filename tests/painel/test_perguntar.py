"""A resposta do RAG (src/painel/perguntar.py) com um cliente falso: nenhum teste chama a API de verdade."""

import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

from streamlit.testing.v1 import AppTest

from busca import Ato, link_dou
from perguntar import CitacaoInvalida, Recusada, Resposta, responder

ATOS = [Ato(1, "DOU-1", date(2026, 8, 12), "Conselho Um", "Aprova o licenciamento", "o **licenciamento** ambiental"),
        Ato(2, "DOU-2", date(2026, 9, 1), "Conselho Dois", None, "o regimento interno")]


class LinkDoDou(unittest.TestCase):
    def ato(self, id_dou, titulo):
        return Ato(1, id_dou, date(2026, 7, 10), "Conselho", None, "trecho", titulo)

    def test_titulo_numerado_vai_para_a_busca_do_dia(self):
        link = link_dou(self.ato("50247338", "RESOLUÇÃO CONAMA Nº 516, DE 8 DE JULHO DE 2026"))
        self.assertTrue(link.startswith("https://www.in.gov.br/consulta/-/buscar/dou?q=%22RESOLU%C3%87%C3%83O%20CONAMA%20N%C2%BA%20516%2C"), link)
        self.assertTrue(link.endswith("&publishFrom=10-07-2026&publishTo=10-07-2026"), link)

    def test_sem_titulo_ou_titulo_generico_vai_para_a_edicao_do_dia(self):
        for titulo in (None, "", "RETIFICAÇÃO"):
            self.assertEqual(link_dou(self.ato("1", titulo)), "https://www.in.gov.br/leiturajornal?data=10-07-2026")

    def test_ato_da_planilha_nao_tem_link(self):
        self.assertIsNone(link_dou(self.ato(None, None)))


class Cliente:
    """Imita só o que o responder usa do SDK: cliente.beta.messages.create(**pedido)."""

    def __init__(self, texto, stop_reason="end_turn"):
        self.pedidos = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.texto, self.stop_reason = texto, stop_reason

    def _create(self, **pedido):
        self.pedidos.append(pedido)
        # O bloco de raciocínio vem antes do texto, com o texto vazio, como na API de verdade.
        return SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking=""),
                                        SimpleNamespace(type="text", text=self.texto)],
                               stop_reason=self.stop_reason,
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20))


class Responder(unittest.TestCase):
    def test_cita_os_atos_enviados(self):
        cliente = Cliente("O Conselho Um aprovou o licenciamento [1].")
        r = responder("o que aprovaram sobre licenciamento?", ATOS, cliente, modelo="claude-sonnet-5-5")
        self.assertEqual((r.texto, r.citados, r.tokens), ("O Conselho Um aprovou o licenciamento [1].", [1], 120))
        pedido = cliente.pedidos[0]
        self.assertEqual(pedido["model"], "claude-sonnet-5-5")
        self.assertIn("[1] Conselho Um, 12/08/2026, DOU DOU-1", pedido["messages"][0]["content"])
        self.assertIn("só os atos", pedido["system"])
        # contagem e "quem está ativo" são do painel: aqui a IA vê só os atos que a busca achou
        self.assertIn("painel", pedido["system"])

    def test_citacao_de_ato_que_nao_foi_enviado(self):
        with self.assertRaises(CitacaoInvalida):
            responder("?", ATOS, Cliente("Segundo o ato [3], sim."))

    def test_lista_e_intervalo_com_ato_que_nao_foi_enviado(self):
        for texto in ("Sim [1, 9].", "Sim [1-9].", "Sim [1–9].", "Sim [1; 9].", "Sim [1 e 9]."):
            with self.subTest(texto), self.assertRaises(CitacaoInvalida):
                responder("?", ATOS, Cliente(texto))

    def test_lista_de_atos_enviados(self):
        self.assertEqual(responder("?", ATOS, Cliente("Sim [1, 2]. E de novo [2].")).citados, [1, 2])

    def test_sem_atos_nao_chama_a_api(self):
        cliente = Cliente("não deveria ser chamado")
        r = responder("?", [], cliente)
        self.assertEqual(cliente.pedidos, [])
        self.assertIn("Não encontrei", r.texto)

    def test_recusa_do_modelo_nao_vira_resposta(self):
        with self.assertRaises(Recusada):
            responder("?", ATOS, Cliente("", stop_reason="refusal"))

    def test_resposta_cortada_avisa(self):
        r = responder("?", ATOS, Cliente("O Conselho Um aprovou [1] e", stop_reason="max_tokens"))
        self.assertTrue(r.cortada)
        self.assertEqual(r.citados, [1])

    def test_nao_manda_o_que_o_modelo_recusa(self):
        cliente = Cliente("ok [1]")
        responder("?", ATOS, cliente)
        pedido = cliente.pedidos[0]
        for proibido in ("temperature", "top_p", "top_k", "tool_choice"):
            self.assertNotIn(proibido, pedido)
        self.assertNotIn("thinking", pedido, "no Sonnet 5.5, thinking desligado dá 400: o padrão é o adaptativo")


class Pagina(unittest.TestCase):
    def test_sem_banco_avisa(self):
        # Uma porta em que ninguém escuta: a conexão é recusada na hora, sem depender do banco de verdade.
        with mock.patch.dict(os.environ, {"PGHOST": "127.0.0.1", "PGPORT": "1"}):
            at = AppTest.from_file("/app/pages/2_Perguntar.py").run(timeout=30)
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("make up" in e.value for e in at.error))

    def _pergunta(self, resposta):
        """A página com o banco, a busca e a resposta falsos: só a tela é exercitada."""
        conn = mock.MagicMock()
        conn.__enter__.return_value.execute.return_value.fetchall.return_value = [(1, "Conselho Um")]
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "falsa"}), mock.patch("psycopg.connect", return_value=conn), \
                mock.patch("busca.buscar", return_value=ATOS), mock.patch("perguntar.responder", return_value=resposta):
            at = AppTest.from_file("/app/pages/2_Perguntar.py").run(timeout=30)
            at.text_input[0].set_value("o que aprovaram?").run()
            at.button[0].click().run()
        self.assertEqual(len(at.exception), 0)
        return at

    def test_resposta_sem_citacao_avisa(self):
        at = self._pergunta(Resposta("Sim, aprovou.", [], 120))
        self.assertTrue(any("não cita nenhum ato" in w.value for w in at.warning))

    def test_resposta_com_citacao_nao_avisa(self):
        self.assertEqual(len(self._pergunta(Resposta("Sim [1].", [1], 120)).warning), 0)

    def test_resposta_traz_o_link_de_cada_ato_citado(self):
        at = self._pergunta(Resposta("Sim [2].", [2], 120))
        links = [m.value for m in at.markdown if "in.gov.br" in m.value]
        self.assertEqual(len(links), 1)
        self.assertIn("[ato 2](https://www.in.gov.br/leiturajornal?data=01-09-2026)", links[0])
        self.assertNotIn("[ato 1]", links[0])


if __name__ == "__main__":
    unittest.main()
