"""A página Revisar (E4) sem banco: ela avisa, não quebra. O caminho com banco é provado à mão, com print, e as
permissões do papel app_curadoria, pelo tests/db/test_acesso.sh."""

import os
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

PAGINA = "/app/pages/1_Revisar.py"


class Revisar(unittest.TestCase):
    # no container de teste não há banco nesta porta
    @mock.patch.dict(os.environ, {"PGHOST": "127.0.0.1", "PGPORT": "1"})
    def test_sem_banco_avisa(self):
        at = AppTest.from_file(PAGINA).run(timeout=30)
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("make up" in e.value for e in at.error), [e.value for e in at.error])


if __name__ == "__main__":
    unittest.main()
