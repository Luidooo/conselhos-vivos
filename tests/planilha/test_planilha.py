"""Testes da leitura da planilha da pesquisadora (#3), só com unittest.

Rodam no serviço carga do compose (make test), ou no host com Python >= 3.11:
    PYTHONPATH=src python3 -m unittest discover -s tests/planilha
Os valores esperados foram conferidos contra o XML e contra o texto do ato, e batem com os
três leitores do benchmark do diário de 26/09 (stdlib, pandas e DuckDB).
"""

import datetime as dt
import pathlib
import re
import tempfile
import unittest
import zipfile

from planilha import xlsx
from planilha.carga import literal
from planilha.normalizar import Descarte, ErroDeEstrutura, data_do_serial, normalizar
from planilha.relatorio import relatorio

PLANILHA = pathlib.Path(__file__).resolve().parents[2] / "data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx"
CNAS_XML = "xl/worksheets/sheet3.xml"


def muta(destino, troca_folha, troca_textos=None):
    """Cópia da planilha com a aba CNAS alterada; cada troca tem que casar exatamente uma vez."""
    def aplica(troca, texto):
        novo, n = troca(texto)
        assert n == 1, "a mutação não casou: a planilha mudou?"
        return novo
    with zipfile.ZipFile(PLANILHA) as zin, zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            dados = zin.read(info.filename)
            if info.filename == CNAS_XML:
                dados = aplica(troca_folha, dados.decode()).encode()
            elif info.filename == "xl/sharedStrings.xml" and troca_textos:
                dados = aplica(troca_textos, dados.decode()).encode()
            zout.writestr(info, dados)
    return destino


class DataDoExcel(unittest.TestCase):
    def test_serial_vira_data(self):
        self.assertEqual(data_do_serial("37671.0"), dt.date(2003, 2, 19))  # exemplo da issue

    def test_hora_do_serial_e_ignorada(self):
        self.assertEqual(data_do_serial("37671.75"), dt.date(2003, 2, 19))

    def test_serial_antes_de_marco_de_1900_e_recusado(self):
        with self.assertRaises(Descarte):  # o Excel trata 1900 como bissexto: o serial 60 não existe
            data_do_serial("60")


class PlanilhaReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = normalizar(PLANILHA)
        cls.atos = {(a.aba, a.linha): a for a in cls.res.atos}

    def confere(self, aba, linha, **esperado):
        ato = self.atos[(aba, linha)]
        for campo, valor in esperado.items():
            obtido = getattr(ato, campo)
            if campo in ("ementa", "conteudo") and valor is not None:
                self.assertTrue(obtido.startswith(valor), f"{campo}: {obtido[:80]!r}")
            else:
                self.assertEqual(obtido, valor, campo)

    def test_215_atos_e_nao_2638(self):
        por_aba = {m: sum(1 for a in self.res.atos if a.aba == m) for m in self.res.contagem}
        self.assertEqual(por_aba, {"CNAS": 53, "CONAMA": 98, "CONCIDADES": 28, "CONDRAF": 24, "CNPIR": 12})
        self.assertEqual(sum(c["no_arquivo"] for c in self.res.contagem.values()), 2637)  # linhas só formatadas

    def test_nada_descartado_e_todo_ato_classificado(self):
        self.assertEqual(self.res.descartes, [])
        self.assertEqual(self.res.sem_classificacao, [])

    def test_cnas(self):
        self.confere("CNAS", 2, id_planilha=1, data_publicacao=dt.date(2003, 2, 19), ref_legal=None,
                     ementa="Elege a Conselheira NELMA AZEREDO", conteudo=None, tipologia="AUTO")

    def test_conama_com_cabecalho_na_linha_2(self):
        self.confere("CONAMA", 3, id_planilha=351, data_publicacao=dt.date(2003, 1, 8), ref_legal="Moção",
                     ementa=None, conteudo="Ministério do Meio Ambiente CONSELHO NACIONAL DO MEIO AMBIENTE-CONAMA MOÇÃO No 049",
                     tipologia="DEF")

    def test_concidades_resumo_e_texto(self):
        self.confere("CONCIDADES", 2, id_planilha=1, data_publicacao=dt.date(2004, 4, 15), ref_legal="Resolução Nº 01",
                     ementa="Aprovação do Regimento Interno do Conselho das Cidades.",
                     conteudo="RESOLVE: Art 1º Aprovar o Regimento Interno", tipologia="AUTO")

    def test_condraf_referencia_fora_do_padrao(self):
        self.confere("CONDRAF", 6, id_planilha=5, data_publicacao=dt.date(2004, 4, 7),
                     ref_legal="Resoluções de 5 de abril de 2004", ementa="Cria o Comitê Permanente de Infra-estrutura",
                     tipologia="AUTO")

    def test_cnpir_tipologia_anotada(self):
        self.confere("CNPIR", 6, id_planilha=5, data_publicacao=dt.date(2013, 4, 8), ref_legal="7/2013 (moção)",
                     tipologia="99", tipologia_original="99 MOÇÃO")

    def test_cnpir_ato_ano_que_o_excel_leu_como_data(self):
        self.assertEqual([a.ref_legal for a in self.res.atos if a.aba == "CNPIR"],
                         ["1/2005", "2/2006", "3/2007", "4/2011", "7/2013 (moção)", "2/2016",
                          "1/2016", "1/2017", "3/2020", "2/2020", "8/2020", "9/2020"])

    def test_99_numerico_vira_sigla(self):
        self.confere("CNAS", 26, id_planilha=47, tipologia="99", tipologia_original="99")
        self.assertEqual(sum(1 for a in self.res.atos if a.tipologia == "99"), 6)

    def test_observacao_fora_do_cabecalho_vira_aviso(self):
        self.assertTrue(any(aba == "CNPIR" and linha == 5 and "G5" in texto for aba, linha, texto in self.res.avisos))

    def test_linha_do_excel_e_unica_por_aba(self):
        self.assertEqual(len(self.atos), len(self.res.atos))


class PlanilhaAlterada(unittest.TestCase):
    """Mutações da planilha: nenhuma linha pode sumir em silêncio."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.original = [(a.aba, a.linha, a.id_planilha) for a in normalizar(PLANILHA).atos]

    def caminho(self, nome):
        return pathlib.Path(self.dir.name) / nome

    def test_data_em_texto_vira_descarte_com_motivo(self):
        with zipfile.ZipFile(PLANILHA) as z:
            n = z.read("xl/sharedStrings.xml").decode().count("<si>")
        arq = muta(self.caminho("s_d.xlsx"),
                   lambda s: re.subn(r'<c r="C3" s="(\d+)"><v>[^<]*</v></c>', rf'<c r="C3" s="\1" t="s"><v>{n}</v></c>', s),
                   lambda s: re.subn(r"</sst>", "<si><t>s/d</t></si></sst>", s))
        res = normalizar(arq)
        self.assertEqual(res.descartes, [("CNAS", 3, "a data não é uma data do Excel: 's/d'")])
        self.assertEqual(len(res.atos), 214)
        self.assertIn("214 + 1 = 215", relatorio(res))

    def test_linha_esvaziada_nao_desloca_as_outras(self):
        def esvazia(s):
            return re.subn(r'(<row r="10"[^>]*>)(.*?)(</row>)',
                           lambda m: m[1] + re.sub(r'<c r="([A-Z]+10)" s="(\d+)"(?: t="\w+")?><v>[^<]*</v></c>',
                                                   r'<c r="\1" s="\2"/>', m[2]) + m[3], s, flags=re.S)
        res = normalizar(muta(self.caminho("vazia.xlsx"), esvazia))
        self.assertEqual([(a.aba, a.linha, a.id_planilha) for a in res.atos],
                         [x for x in self.original if x[:2] != ("CNAS", 10)])

    def test_id_repetido_vira_descarte(self):
        res = normalizar(muta(self.caminho("id.xlsx"),
                              lambda s: re.subn(r'<c r="A3" s="(\d+)"><v>2.0</v></c>', r'<c r="A3" s="\1"><v>1.0</v></c>', s)))
        self.assertEqual(res.descartes, [("CNAS", 3, "ID_VERSAO 1 repetido (já está na linha 2)")])

    def test_coluna_renomeada_para_a_carga(self):
        with zipfile.ZipFile(PLANILHA) as z:
            n = z.read("xl/sharedStrings.xml").decode().count("<si>")
        arq = muta(self.caminho("coluna.xlsx"),
                   lambda s: re.subn(r'<c r="G1" s="(\d+)" t="s"><v>\d+</v></c>', rf'<c r="G1" s="\1" t="s"><v>{n}</v></c>', s),
                   lambda s: re.subn(r"</sst>", "<si><t>TIPOLOGIA</t></si></sst>", s))
        with self.assertRaisesRegex(ErroDeEstrutura, "TIPOL_DECIS"):
            normalizar(arq)

    def test_celula_de_erro_para_a_carga(self):
        arq = muta(self.caminho("erro.xlsx"),
                   lambda s: re.subn(r'<c r="C3" s="(\d+)"><v>[^<]*</v></c>', r'<c r="C3" s="\1" t="e"><v>#N/A</v></c>', s))
        with self.assertRaisesRegex(xlsx.NaoSuportado, "C3"):
            normalizar(arq)


class Saidas(unittest.TestCase):
    def test_relatorio_deterministico(self):
        self.assertEqual(relatorio(normalizar(PLANILHA)), relatorio(normalizar(PLANILHA)))

    def test_sql_escapa_aspas(self):
        self.assertEqual(literal("d'água"), "'d''água'")


if __name__ == "__main__":
    unittest.main()
