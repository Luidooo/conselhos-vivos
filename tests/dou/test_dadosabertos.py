"""Testes dos dados abertos (#53), portados de internal/dadosabertos/dadosabertos_test.go.

Um servidor HTTP de teste numa thread em 127.0.0.1 faz o papel do httptest do
Go: o loopback existe mesmo com network_mode: none, então roda no serviço
carga, sem rede externa.
"""

import http.server
import io
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from dou.bronze import Bronze, NaoEZip
from dou.dadosabertos import (Cliente, HostDiferente, LISTAGEM, Mes, NaoPublicado,
                              StatusInesperado, nome_do_zip)

AGOSTO = Mes(2026, 8)

# Onde o servidor de teste serve a Seção 1 de agosto, no formato real: o nome,
# depois o UUID do documento.
ZIP_PATH = "/documents/49035712/731891581/S01082026.zip/1a3dbffa-ed49-13ee-86d6-31bba2c02658"

# A página de agosto como o site a serve, reduzida aos links: as três seções,
# a query escapada como HTML.
LISTING = """<html><body>
<a href="/documents/49035712/731891581/S01082026.zip/1a3dbffa-ed49-13ee-86d6-31bba2c02658?version=1.0&amp;download=t">S01082026.zip</a>
<a href="/documents/49035712/731891581/S02082026.zip/0facf097-be09-0968-33ae-258f1554478e?version=1.0&amp;download=t">S02082026.zip</a>
<a href="/documents/49035712/731891581/S03082026.zip/7eefd17d-4eb4-8d76-2520-09bf7f48a0bc?version=1.0&amp;download=t">S03082026.zip</a>
</body></html>"""


def zip_body():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("515_20260803_24176216.xml", '<xml><article id="1"/></xml>')
    return buf.getvalue()


def servidor(pagina, zip_handler):
    """Serve a listagem e entrega qualquer outro caminho a zip_handler. Conta
    os pedidos e recusa, com o 403 do site real, um pedido sem o Accept que
    o site real exige."""
    contagem = {"n": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            contagem["n"] += 1
            if self.headers.get("Accept") != "*/*":
                self.send_response(403); self.end_headers(); return
            from urllib.parse import urlsplit, parse_qs
            u = urlsplit(self.path)
            if u.path == LISTAGEM:
                q = parse_qs(u.query)
                assert q.get("ano") == ["2026"] and q.get("mes") == ["Agosto"], q
                corpo = pagina.encode()
                self.send_response(200); self.send_header("Content-Length", str(len(corpo))); self.end_headers()
                self.wfile.write(corpo); return
            zip_handler(self)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, contagem


def responde(status, corpo=b"", tipo=None):
    def h(self):
        self.send_response(status)
        if tipo:
            self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)
    return h


class CasoComServidor(unittest.TestCase):
    pagina = LISTING
    zip_handler = staticmethod(responde(500))

    def setUp(self):
        self.srv, self.contagem = servidor(self.pagina, self.zip_handler)
        self.cliente = Cliente(base_url=f"http://127.0.0.1:{self.srv.server_address[1]}")
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.bronze = Bronze(self.dir)

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close(); self._tmp.cleanup()

    def entradas(self):
        return sorted(p.name for p in self.dir.iterdir())


class Nomes(unittest.TestCase):
    def test_o_nome_do_zip_e_o_publicado(self):
        self.assertEqual(nome_do_zip(AGOSTO), "S01082026.zip")
        self.assertEqual(nome_do_zip(Mes(2010, 3)), "S01032010.zip")

    def test_mes_so_aceita_aaaa_mm(self):
        self.assertEqual(Mes.parse("2026-08"), AGOSTO)
        for raw in ["2026-8", "08/2026", "2026-13", "2026-08-01", "", None]:
            with self.assertRaises(ValueError, msg=raw):
                Mes.parse(raw)


CORPO = zip_body()


def _so_a_secao_1(handler):
    assert handler.path.split("?")[0] == ZIP_PATH, "só a Seção 1 é buscada"
    responde(200, CORPO)(handler)


class BaixaSecao1(CasoComServidor):
    corpo = CORPO
    zip_handler = staticmethod(_so_a_secao_1)

    def test_salva_a_secao_1(self):
        self.assertEqual(self.cliente.baixar_mes(AGOSTO, self.bronze), "baixada")
        self.assertEqual((self.dir / "S01082026.zip").read_bytes(), self.corpo)


class MesEmDisco(CasoComServidor):
    def test_nao_faz_nenhum_pedido(self):
        (self.dir / "S01082026.zip").write_bytes(zip_body())
        self.assertEqual(self.cliente.baixar_mes(AGOSTO, self.bronze), "ja-baixada")
        self.assertEqual(self.contagem["n"], 0)


class MesNaoPublicado(CasoComServidor):
    pagina = "<html><body>nenhum arquivo</body></html>"

    def test_diz_que_o_mes_nao_saiu(self):
        with self.assertRaises(NaoPublicado):
            self.cliente.baixar_mes(AGOSTO, self.bronze)
        self.assertEqual(self.contagem["n"], 1, "só a listagem é pedida")
        self.assertEqual(self.entradas(), [])


class DownloadFalha(CasoComServidor):
    def test_nao_deixa_nada(self):
        with self.assertRaises(StatusInesperado) as ctx:
            self.cliente.baixar_mes(AGOSTO, self.bronze)
        self.assertIn("500", str(ctx.exception))
        self.assertEqual(self.entradas(), [])


class PaginaNoLugarDoZip(CasoComServidor):
    zip_handler = staticmethod(responde(200, b"<html>manuten\xc3\xa7\xc3\xa3o</html>", "text/html"))

    def test_recusa(self):
        with self.assertRaises(NaoEZip) as ctx:
            self.cliente.baixar_mes(AGOSTO, self.bronze)
        self.assertIn("not a zip", str(ctx.exception))
        self.assertEqual(self.entradas(), [])


class LinkParaOutroHost(CasoComServidor):
    pagina = '<a href="https://outro.exemplo/documents/1/2/S01082026.zip/uuid?download=t">S01082026.zip</a>'

    def test_recusa(self):
        with self.assertRaises(HostDiferente) as ctx:
            self.cliente.baixar_mes(AGOSTO, self.bronze)
        self.assertIn("outro.exemplo", str(ctx.exception))
        self.assertEqual(self.contagem["n"], 1)
        self.assertEqual(self.entradas(), [])


if __name__ == "__main__":
    unittest.main()
