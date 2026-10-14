"""Testes do bronze (#53), portados um a um de internal/store/store_test.go.

Só unittest e stdlib; nada de rede nem de banco.
"""

import io
import os
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from dou.bronze import Bronze, NaoEZip


def zip_com(entrada, conteudo):
    """Um arquivo de verdade, para a validação sob teste ser a mesma que o
    leitor vai exigir."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(entrada, conteudo)
    return buf.getvalue()


class CasoComDiretorio(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.bronze = Bronze(self.dir)

    def tearDown(self):
        self._tmp.cleanup()

    def entradas(self):
        return sorted(p.name for p in self.dir.iterdir())


class Salvar(CasoComDiretorio):
    def test_grava_um_zip_valido(self):
        arquivo = zip_com("DO1.xml", "<article/>")
        recibo = self.bronze.salvar("2026-10-02-DO1.zip", io.BytesIO(arquivo))
        self.assertEqual(recibo.caminho, self.dir / "2026-10-02-DO1.zip")
        self.assertEqual(recibo.tamanho, len(arquivo))
        self.assertEqual(self.entradas(), ["2026-10-02-DO1.zip"], "nenhum temporário sobrou")
        self.assertEqual(recibo.caminho.read_bytes(), arquivo)

    def test_recusa_um_corpo_html(self):
        # A falha que a ordem inteira existe para impedir: a página de login
        # salva sob um nome que todo o resto lê como edição.
        with self.assertRaises(NaoEZip) as ctx:
            self.bronze.salvar("2026-10-02-DO1.zip", io.BytesIO(b"<html>faca login</html>"))
        self.assertIn("is not a zip", str(ctx.exception))
        self.assertEqual(self.entradas(), [], "nem o nome final nem um temporário")

    def test_nao_deixa_nada_quando_o_fluxo_quebra(self):
        class Quebrado:
            def __init__(self):
                self.primeiro = True

            def read(self, n=-1):
                if self.primeiro:
                    self.primeiro = False
                    return b"PK\x03\x04"
                raise ConnectionError("the connection died mid-transfer")

        with self.assertRaises(ConnectionError):
            self.bronze.salvar("2026-10-02-DO1.zip", Quebrado())
        self.assertEqual(self.entradas(), [])

    def test_substitui_um_arquivo_existente(self):
        nome = "2026-10-02-DO1.zip"
        self.bronze.salvar(nome, io.BytesIO(zip_com("old.xml", "old")))
        novo = zip_com("new.xml", "new")
        self.bronze.salvar(nome, io.BytesIO(novo))
        self.assertEqual((self.dir / nome).read_bytes(), novo)
        self.assertEqual(self.entradas(), [nome])

    def test_e_seguro_quando_duas_execucoes_disputam_o_mesmo_nome(self):
        nome = "2026-10-02-DO1.zip"
        arquivo = zip_com("DO1.xml", "<article/>")
        erros = []

        def grava():
            try:
                self.bronze.salvar(nome, io.BytesIO(arquivo))
            except Exception as e:  # pragma: no cover - só para reportar
                erros.append(e)

        fios = [threading.Thread(target=grava) for _ in range(2)]
        for f in fios:
            f.start()
        for f in fios:
            f.join()
        self.assertEqual(erros, [])
        self.assertEqual(self.entradas(), [nome], "o temporário do perdedor não pode sobreviver")
        self.assertEqual((self.dir / nome).read_bytes(), arquivo)


class Abrir(unittest.TestCase):
    def test_recusa_um_diretorio_que_nao_existe(self):
        # Criar o diretório esconderia o que isto reporta: a variável de saída
        # apontando para onde o volume não está montado.
        with tempfile.TemporaryDirectory() as tmp:
            faltando = Path(tmp) / "bronze" / "inlabs"
            with self.assertRaises(FileNotFoundError) as ctx:
                Bronze(faltando)
            self.assertIn(str(faltando), str(ctx.exception))

    def test_recusa_um_caminho_que_e_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "inlabs"
            caminho.write_bytes(b"")
            with self.assertRaises(NotADirectoryError) as ctx:
                Bronze(caminho)
            self.assertIn("não é um diretório", str(ctx.exception))


class Marcadores(CasoComDiretorio):
    def test_sem_edicao_deixa_um_marcador_vazio(self):
        self.bronze.marcar_sem_edicao("2026-10-04-DO1E.zip")
        self.assertEqual(self.entradas(), ["2026-10-04-DO1E.sem-edicao"])
        self.assertEqual((self.dir / "2026-10-04-DO1E.sem-edicao").stat().st_size, 0)

    def test_sem_edicao_duas_vezes_e_igual_a_uma(self):
        self.bronze.marcar_sem_edicao("2026-10-04-DO1.zip")
        self.bronze.marcar_sem_edicao("2026-10-04-DO1.zip")
        self.assertEqual(self.entradas(), ["2026-10-04-DO1.sem-edicao"])

    def test_sem_edicao_deixa_em_paz_um_zip_que_ja_esta_la(self):
        # Uma edição baixada uma vez existiu: um "não encontrada" posterior
        # não a despublica.
        self.bronze.salvar("2026-10-02-DO1.zip", io.BytesIO(zip_com("DO1.xml", "<article/>")))
        self.bronze.marcar_sem_edicao("2026-10-02-DO1.zip")
        self.assertEqual(self.entradas(), ["2026-10-02-DO1.zip"], "nenhum marcador ao lado do zip")

    def test_salvar_remove_o_marcador_da_sua_edicao(self):
        # A edição extra sai à tarde: a busca da manhã a marca como ausente, a
        # da noite a encontra.
        self.bronze.marcar_sem_edicao("2026-10-02-DO1E.zip")
        self.bronze.marcar_sem_edicao("2026-10-02-DO1.zip")
        self.bronze.salvar("2026-10-02-DO1E.zip", io.BytesIO(zip_com("DO1E.xml", "<article/>")))
        self.assertEqual(self.entradas(), ["2026-10-02-DO1.sem-edicao", "2026-10-02-DO1E.zip"], "só o próprio marcador sai")

    def test_falhou_deixa_um_marcador_vazio(self):
        self.bronze.marcar_falhou("2026-10-02-DO1.zip")
        self.assertEqual(self.entradas(), ["2026-10-02-DO1.falhou"])
        self.assertEqual((self.dir / "2026-10-02-DO1.falhou").stat().st_size, 0)

    def test_o_ultimo_marcador_e_o_que_fica(self):
        # O registro é o que a última busca encontrou: um marcador por edição, nunca os dois.
        self.bronze.marcar_sem_edicao("2026-10-02-DO1E.zip")
        self.bronze.marcar_falhou("2026-10-02-DO1E.zip")
        self.assertEqual(self.entradas(), ["2026-10-02-DO1E.falhou"])
        self.bronze.marcar_sem_edicao("2026-10-02-DO1E.zip")
        self.assertEqual(self.entradas(), ["2026-10-02-DO1E.sem-edicao"])

    def test_falhou_deixa_em_paz_um_zip_que_ja_esta_la(self):
        self.bronze.salvar("2026-10-02-DO1.zip", io.BytesIO(zip_com("DO1.xml", "<article/>")))
        self.bronze.marcar_falhou("2026-10-02-DO1.zip")
        self.assertEqual(self.entradas(), ["2026-10-02-DO1.zip"], "nenhum marcador ao lado do zip")

    def test_salvar_remove_o_marcador_de_falha_da_sua_edicao(self):
        self.bronze.marcar_falhou("2026-10-02-DO1.zip")
        self.bronze.salvar("2026-10-02-DO1.zip", io.BytesIO(zip_com("DO1.xml", "<article/>")))
        self.assertEqual(self.entradas(), ["2026-10-02-DO1.zip"])

    def test_tem_so_enxerga_o_zip(self):
        self.assertFalse(self.bronze.tem("S01082026.zip"))
        self.bronze.marcar_falhou("S01082026.zip")
        self.assertFalse(self.bronze.tem("S01082026.zip"), "um marcador não é o zip")
        self.bronze.salvar("S01082026.zip", io.BytesIO(zip_com("a.xml", "<xml/>")))
        self.assertTrue(self.bronze.tem("S01082026.zip"))


class Permissoes(CasoComDiretorio):
    def test_o_zip_fica_legivel_pelo_dono(self):
        # O temporário nasce 0600 e o rename mantém, como no Go.
        self.bronze.salvar("S01082026.zip", io.BytesIO(zip_com("a.xml", "<xml/>")))
        modo = (self.dir / "S01082026.zip").stat().st_mode & 0o777
        self.assertEqual(modo & 0o600, 0o600)


if __name__ == "__main__":
    unittest.main()
