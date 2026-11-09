"""Código de saída do fetch-mensal e do persist (#83, #84): 3 quando o problema está no dado, 1 quando
está na infraestrutura. A orquestração não repete o 3.

Sem rede e sem banco: o download e a gravação são trocados por dublês.
Roda com make test-py-dou, ou no host: PYTHONPATH=src python3 -m unittest discover -s tests/dou
"""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from dou import SAIDA_DE_DADO, dadosabertos, fetch_mensal, persist


def silencioso(funcao, *args):
    with contextlib.redirect_stderr(io.StringIO()):
        return funcao(*args)


class FetchMensal(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        ambiente = mock.patch.dict(os.environ, {"DADOS_ABERTOS_OUTPUT_DIR": self._tmp.name})
        ambiente.start()
        self.addCleanup(ambiente.stop)

    def com_download(self, efeito):
        with mock.patch.object(dadosabertos.Cliente, "baixar_mes", side_effect=efeito):
            return silencioso(fetch_mensal.main, ["--month", "2026-10"])

    def test_mes_nao_publicado_sai_com_o_codigo_de_dado(self):
        self.assertEqual(self.com_download(dadosabertos.NaoPublicado("sem link")), SAIDA_DE_DADO)

    def test_outra_falha_sai_com_1(self):
        self.assertEqual(self.com_download(OSError("rede fora")), 1)

    def test_mes_baixado_sai_com_0(self):
        self.assertEqual(self.com_download(None), 0)


class Persist(unittest.TestCase):
    def com_resultado(self, efeito):
        with mock.patch.object(persist.db, "conectar", return_value=contextlib.nullcontext()), \
             mock.patch.object(persist, "persistir", side_effect=efeito):
            return silencioso(persist.main, ["edicao.zip"])

    def test_entrada_que_nao_le_sai_com_o_codigo_de_dado(self):
        self.assertEqual(self.com_resultado(lambda conn, caminho: persist.Resumo(gravadas=2, falhou=1)), SAIDA_DE_DADO)

    def test_banco_que_recusa_sai_com_1(self):
        self.assertEqual(self.com_resultado(RuntimeError("conexão recusada")), 1)

    def test_tudo_gravado_sai_com_0(self):
        self.assertEqual(self.com_resultado(lambda conn, caminho: persist.Resumo(gravadas=2)), 0)


if __name__ == "__main__":
    unittest.main()
