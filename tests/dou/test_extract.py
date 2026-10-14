"""Testes do extract (#54), portados de cmd/extract/main_test.go."""

import io
import json
import logging
import tempfile
import unittest
import zipfile
from pathlib import Path

from dou.extract import Resumo, extrair

AMOSTRAS = Path(__file__).parent / "amostras"


def escreve_edicao(dir, amostras, extras=None):
    """Um ZIP em disco, com as amostras e entradas extras, como o fetch deixa."""
    caminho = Path(dir) / "2026-10-02-DO1.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        for nome in amostras:
            z.writestr(nome, (AMOSTRAS / nome).read_bytes())
        for nome, conteudo in (extras or {}).items():
            z.writestr(nome, conteudo)
    return str(caminho)


def linhas(texto):
    return [json.loads(l) for l in texto.splitlines() if l]


class Extract(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)
        self._tmp.cleanup()

    def test_imprime_uma_linha_por_materia(self):
        caminho = escreve_edicao(self.dir, ["515_20190507_11615606.xml", "malformado.xml", "conselho-construido.xml"],
                                 {"figura.jpg": "not an article"})
        out = io.StringIO()
        resumo = extrair(out, caminho, com_html=False)
        self.assertEqual(resumo, Resumo(lidas=2, ignoradas=1, falhou=1))
        impressas = linhas(out.getvalue())
        self.assertEqual(len(impressas), 2)
        self.assertEqual(impressas[0]["id"], "8724946")
        self.assertEqual(impressas[0]["pubDate"], "2019-05-07")
        self.assertNotIn("html", impressas[0], "o HTML fica de fora a menos que se peça")
        self.assertEqual(impressas[1]["artCategory"],
                         ["Ministério do Meio Ambiente e Mudança do Clima", "Conselho Nacional do Meio Ambiente"])

    def test_imprime_o_html_quando_pedido(self):
        caminho = escreve_edicao(self.dir, ["conselho-construido.xml"])
        out = io.StringIO()
        extrair(out, caminho, com_html=True)
        impressas = linhas(out.getvalue())
        self.assertIn('<p class="assina">FULANO DE TAL</p>', impressas[0]["html"], "impresso como está, sem escapar")

    def test_para_num_zip_que_nao_abre(self):
        # Um ZIP que não abre não é entrada ruim: não há com o que seguir.
        caminho = Path(self.dir) / "login.zip"
        caminho.write_bytes(b"<html>faca login</html>")
        with self.assertRaises(zipfile.BadZipFile):
            extrair(io.StringIO(), str(caminho))


if __name__ == "__main__":
    unittest.main()
