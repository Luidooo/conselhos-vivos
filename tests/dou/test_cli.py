"""Fumaça do pacote dou (#52): o pacote importa e a porta de entrada responde.

Roda no serviço carga do compose (make test-py-dou), sem rede e sem banco, ou
no host: PYTHONPATH=src python3 -m unittest discover -s tests/dou
(sem __init__.py aqui, como nos outros tests/*: senão o discover da raiz
confundiria tests/dou com o pacote src/dou).
"""

import contextlib
import io
import unittest

from dou import __main__ as cli


class PortaDeEntrada(unittest.TestCase):
    def saida(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cli.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_sem_argumento_mostra_o_uso_no_stderr_e_sai_com_2(self):
        rc, out, err = self.saida([])
        self.assertEqual(rc, 2)
        self.assertIn("uso: python -m dou", err)
        self.assertEqual(out, "")

    def test_help_vai_para_o_stdout_e_sai_com_0(self):
        rc, out, err = self.saida(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("subcomandos:", out)
        self.assertEqual(err, "")

    def test_subcomando_desconhecido_sai_com_2(self):
        rc, out, err = self.saida(["inexistente"])
        self.assertEqual(rc, 2)
        self.assertIn("desconhecido: inexistente", err)
