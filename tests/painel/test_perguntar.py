"""A resposta do RAG (src/painel/perguntar.py) com um cliente falso: nenhum teste chama a API de verdade."""

import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

from streamlit.testing.v1 import AppTest

from busca import Ato
from perguntar import CitacaoInvalida, Recusada, responder

ATOS = [Ato(1, "DOU-1", date(2026, 8, 12), "Conselho Um", "Aprova o licenciamento", "o **licenciamento** ambiental"),
        Ato(2, "DOU-2", date(2026, 9, 1), "Conselho Dois", None, "o regimento interno")]


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


if __name__ == "__main__":
    unittest.main()
