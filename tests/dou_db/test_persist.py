"""Testes do persist (#55), portados de cmd/persist/main_test.go. Cada um numa
transação desfeita."""

import logging
import tempfile
import zipfile
from pathlib import Path

from dbtest import CasoComBanco
from dou.persist import Resumo, persistir

AMOSTRAS = Path(__file__).parent.parent / "dou" / "amostras"


def amostra(nome):
    return (AMOSTRAS / nome).read_text(encoding="utf-8")


def uma_edicao():
    """Um dia em pequeno: uma matéria de conselho conhecido, uma real de órgão
    que não é conselho, um XML quebrado e uma imagem."""
    return {
        "conselho-construido.xml": amostra("conselho-construido.xml"),
        "515_20190507_11615606.xml": amostra("515_20190507_11615606.xml"),
        "malformado.xml": amostra("malformado.xml"),
        "figura.jpg": "not an article",
    }


class Caso(CasoComBanco):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)
        self._tmp.cleanup()
        super().tearDown()

    def escreve(self, entradas, nome="2026-10-02-DO1.zip"):
        """ZIP em disco como o fetch deixa; entradas em ordem de nome, para o
        teste saber qual vem primeiro."""
        caminho = Path(self._tmp.name) / nome
        with zipfile.ZipFile(caminho, "w") as z:
            for n in sorted(entradas):
                z.writestr(n, entradas[n])
        return str(caminho)

    def estado(self):
        """Tudo o que o persist pode escrever, linha a linha e em ordem, para
        dois estados serem comparados como texto. id e criado_em entram de
        propósito: uma linha reescrita no lugar os mudaria."""
        return [r[0] for r in self.conn.execute("""
            SELECT 'ato ' || row_to_json(a)::text FROM ato a
            UNION ALL
            SELECT 'orgao_alias ' || row_to_json(o)::text FROM orgao_alias o
            ORDER BY 1""").fetchall()]


class Persistir(Caso):
    def test_grava_a_edicao(self):
        antes = self.estado()
        # O órgão desconhecido do teste pode já estar na fila: uma ingestão real
        # neste banco (make ingest-mensal) também o encontra, e a fila aceita um
        # nome uma vez.
        (ja,) = self.conn.execute("SELECT EXISTS (SELECT 1 FROM orgao_alias WHERE nome = %s)",
                                  ("Coordenação-Geral de Controle de Serviços e Produtos",)).fetchone()
        resumo = persistir(self.conn, self.escreve(uma_edicao()))
        self.assertEqual(resumo, Resumo(gravadas=1, orgao_desconhecido=1, ignoradas=1, falhou=1))
        self.assertEqual(len(self.estado()), len(antes) + (1 if ja else 2))

    def test_duas_vezes_deixa_o_banco_identico(self):
        # O aceite da #24: o mesmo dia duas vezes deixa o banco idêntico.
        caminho = self.escreve(uma_edicao())
        persistir(self.conn, caminho)
        depois_da_primeira = self.estado()
        resumo = persistir(self.conn, caminho)
        self.assertEqual(resumo, Resumo(inalteradas=1, orgao_desconhecido=1, ignoradas=1, falhou=1))
        self.assertEqual(self.estado(), depois_da_primeira)

    def test_edicao_republicada_vira_versoes_novas(self):
        persistir(self.conn, self.escreve(uma_edicao()))
        depois_da_primeira = self.estado()
        republicada = uma_edicao()
        republicada["conselho-construido.xml"] = republicada["conselho-construido.xml"].replace("30 dias", "60 dias", 1)
        resumo = persistir(self.conn, self.escreve(republicada, "republicada.zip"))
        self.assertEqual(resumo, Resumo(versoes_novas=1, orgao_desconhecido=1, ignoradas=1, falhou=1))
        depois = self.estado()
        self.assertEqual(len(depois), len(depois_da_primeira) + 1)
        self.assertTrue(set(depois_da_primeira) <= set(depois), "toda linha da primeira execução continua lá, intacta")
        (versoes,) = self.conn.execute("""SELECT string_agg(versao || ':' || (conteudo LIKE '%%60 dias%%'), ',' ORDER BY versao)
                                          FROM ato WHERE id_dou = '900000001'""").fetchone()
        self.assertEqual(versoes, "1:false,2:true")

    def test_so_a_primeira_de_um_id_repetido(self):
        # O mesmo id duas vezes no ZIP, dizendo coisas diferentes: a primeira é
        # a matéria, a outra fica de fora, e o resto do ZIP segue. De novo,
        # nada é escrito.
        edicao = uma_edicao()
        edicao["repetida.xml"] = edicao["conselho-construido.xml"].replace("30 dias", "60 dias", 1)
        caminho = self.escreve(edicao)
        resumo = persistir(self.conn, caminho)
        self.assertEqual(resumo, Resumo(gravadas=1, orgao_desconhecido=1, repetidas=1, ignoradas=1, falhou=1))
        depois_da_primeira = self.estado()
        (versoes,) = self.conn.execute("""SELECT string_agg(versao || ':' || (conteudo LIKE '%%30 dias%%'), ',' ORDER BY versao)
                                          FROM ato WHERE id_dou = '900000001'""").fetchone()
        self.assertEqual(versoes, "1:true", "a entrada que vem primeiro no ZIP é a gravada")
        resumo = persistir(self.conn, caminho)
        self.assertEqual(resumo, Resumo(inalteradas=1, orgao_desconhecido=1, repetidas=1, ignoradas=1, falhou=1))
        self.assertEqual(self.estado(), depois_da_primeira)

    def test_pega_uma_materia_que_chegou_atrasada(self):
        # Dado atrasado: a edição de um dia já gravado volta com uma matéria
        # que não tinha. Rodar o dia de novo pega a nova e deixa o resto em paz,
        # e a nova fica no dia em que foi publicada, não no dia em que chegou.
        persistir(self.conn, self.escreve(uma_edicao()))
        depois_da_primeira = self.estado()
        tarde = uma_edicao()
        tarde["conselho-atrasada.xml"] = tarde["conselho-construido.xml"].replace('id="900000001"', 'id="900000777"', 1)
        self.assertNotEqual(tarde["conselho-construido.xml"], tarde["conselho-atrasada.xml"])
        resumo = persistir(self.conn, self.escreve(tarde, "tarde.zip"))
        self.assertEqual(resumo, Resumo(gravadas=1, inalteradas=1, orgao_desconhecido=1, ignoradas=1, falhou=1))
        depois = self.estado()
        self.assertEqual(len(depois), len(depois_da_primeira) + 1)
        self.assertTrue(set(depois_da_primeira) <= set(depois), "o que estava lá fica intacto")
        (publicada,) = self.conn.execute("SELECT data_publicacao::text FROM ato WHERE id_dou = '900000777'").fetchone()
        self.assertEqual(publicada, "2026-10-02")

    def test_para_num_zip_que_nao_abre(self):
        # Um ZIP que não abre não é entrada ruim: não há com o que seguir. É
        # recusado antes de o banco ser consultado.
        caminho = Path(self._tmp.name) / "login.zip"
        caminho.write_bytes(b"<html>faca login</html>")
        with self.assertRaises(zipfile.BadZipFile):
            persistir(None, str(caminho))
