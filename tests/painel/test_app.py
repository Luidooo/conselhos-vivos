import os
import shutil
import tempfile
import unittest
from unittest import mock
import duckdb
from streamlit.testing.v1 import AppTest

APP = "/app/app.py"
METRICAS = ["Ativos", "Em silêncio", "Sem ato no período coberto", "Sem ato próprio, mas citados"]


def textos(at):
    # a cobertura e o SLA estão em chips (markdown); as regras de leitura, em legendas
    return [c.value for c in at.caption] + [m.value for m in at.markdown]


def tabela_com(at, coluna):
    # as abas mudam a ordem dos dataframes: acha a tabela pela coluna que só ela tem
    return next(d.value for d in at.dataframe if coluna in d.value.columns)


class TestApp(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gold_path = os.path.join(self.tmpdir, "conselhos.duckdb")
        self.orig_gold = os.environ.get("PAINEL_GOLD")

    def tearDown(self):
        if self.orig_gold is not None:
            os.environ["PAINEL_GOLD"] = self.orig_gold
        else:
            os.environ.pop("PAINEL_GOLD", None)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _cria_tabelas_base(self, con):
        con.execute("""
            CREATE TABLE fct_conselho_mes (
                orgao_id INTEGER,
                mes DATE,
                atos INTEGER
            );
            INSERT INTO fct_conselho_mes VALUES
                (1, DATE '2026-07-01', 2),
                (1, DATE '2026-08-01', 3),
                (1, DATE '2026-09-01', 5),
                (2, DATE '2026-07-01', 1),
                (2, DATE '2026-08-01', 0),
                (2, DATE '2026-09-01', 0),
                (3, DATE '2026-07-01', 1),
                (3, DATE '2026-08-01', 0),
                (3, DATE '2026-09-01', 0),
                (4, DATE '2026-07-01', 0),
                (4, DATE '2026-08-01', 0),
                (4, DATE '2026-09-01', 0);

            CREATE TABLE dim_conselho (
                orgao_id INTEGER,
                nome VARCHAR,
                sigla VARCHAR,
                atual BOOLEAN,
                eh_participativo BOOLEAN
            );
            INSERT INTO dim_conselho VALUES
                (1, 'Conselho Um', 'C1', true, true),
                (2, 'Conselho Dois', 'C2', true, NULL),
                (3, 'Conselho Três', 'C3', true, false),
                (4, 'Conselho Quatro', 'C4', true, NULL);

            CREATE TABLE fct_ato (
                orgao_id INTEGER,
                tipologia_sigla VARCHAR,
                origem VARCHAR,
                data_publicacao DATE
            );
            INSERT INTO fct_ato VALUES
                (1, 'SEM', 'DOU', DATE '2026-07-10'),
                (1, 'GEST', 'PLANILHA', DATE '2010-03-02'),
                (2, 'SEM', 'DOU', DATE '2026-07-15');

            CREATE TABLE fct_mencao (
                orgao_id INTEGER,
                data_publicacao DATE,
                publicador VARCHAR,
                titulo VARCHAR
            );
            INSERT INTO fct_mencao VALUES
                (1, DATE '2026-08-05', 'Ministério X', 'Portaria 1'),
                (4, DATE '2026-08-06', 'Ministério Y', 'Portaria 2'),
                (4, DATE '2026-08-07', 'Ministério Y', 'Portaria 3');

            CREATE TABLE mart_vitalidade (
                orgao_id INTEGER,
                nome VARCHAR,
                sigla VARCHAR,
                mes_referencia DATE,
                ultimo_mes_com_ato DATE,
                atos_no_periodo INTEGER,
                meses_sem_publicar INTEGER,
                situacao VARCHAR,
                mencoes_no_periodo INTEGER,
                ultimo_mes_citado DATE
            );
            INSERT INTO mart_vitalidade VALUES
                (1, 'Conselho Um', 'C1', DATE '2026-09-01', DATE '2026-09-01', 10, 0, 'ativo', 3, DATE '2026-08-01'),
                (2, 'Conselho Dois', 'C2', DATE '2026-09-01', DATE '2026-07-01', 1, 2, 'em silêncio', 0, NULL),
                (3, 'Conselho Três', 'C3', DATE '2026-09-01', DATE '2026-07-01', 1, 2, 'ativo', 0, NULL),
                (4, 'Conselho Quatro', 'C4', DATE '2026-09-01', NULL, 0, NULL, 'sem ato no período coberto', 2, DATE '2026-08-01');
        """)

    def _cria_freshness(self, con):
        con.execute("""
            CREATE TABLE freshness_vitalidade (
                primeiro_mes_coberto DATE,
                ultimo_mes_coberto DATE,
                mes_esperado DATE,
                atraso_meses INTEGER,
                dentro_do_sla BOOLEAN
            );
            INSERT INTO freshness_vitalidade VALUES
                (DATE '2026-07-01', DATE '2026-09-01', DATE '2026-09-01', 0, true);
        """)

    def test_com_dados_e_freshness(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual([m.label for m in at.metric], METRICAS)
        self.assertEqual([m.value for m in at.metric], ["2", "1", "1", "1"])
        self.assertEqual(at.title[0].value, "Quais conselhos nacionais de participação social ainda estão funcionando?")
        self.assertEqual(len(tabela_com(at, "Situação")), 4)
        self.assertEqual(len(tabela_com(at, "Origem")), 3)
        self.assertIn("Origem", tabela_com(at, "Origem").columns)
        warnings = [w.value for w in at.warning]
        self.assertGreater(len(warnings), 0)
        self.assertIn("Sem ato no DOU não prova que o conselho parou", warnings[0])
        legendas = textos(at)
        self.assertTrue(any("DOU coberto de 07/2026 a 09/2026." in t for t in legendas), legendas)
        self.assertTrue(any("dentro do SLA" in t for t in legendas))

    def test_participacao_social_sem_filtrar(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        tabela = tabela_com(at, "Situação")
        # verdadeiro vira sim, falso vira não, nulo vira não avaliado; nenhuma linha some
        self.assertEqual(len(tabela), 4)
        participacao = dict(zip(tabela["Conselho"], tabela["Participação social (pesquisadora)"]))
        self.assertEqual(participacao, {
            "Conselho Um": "sim",
            "Conselho Dois": "não avaliado",
            "Conselho Três": "não",
            "Conselho Quatro": "não avaliado",
        })

    def test_citado_por_outros_orgaos(self):
        # O segundo sinal (plano 2026-11-09): o conselho sem ato próprio, mas citado, aparece com as menções.
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        tabela = tabela_com(at, "Situação")
        citado = dict(zip(tabela["Conselho"], tabela["Citado por outros órgãos"]))
        self.assertEqual(citado["Conselho Quatro"], 2)
        self.assertEqual(citado["Conselho Dois"], 0)
        legendas = textos(at)
        self.assertTrue(any("Citado por outros órgãos" in t for t in legendas), legendas)

    def test_regras_de_negocio_explicadas(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.expander[0].label, "Como ler este painel: as regras de negócio")
        regras = " ".join(m.value for m in at.expander[0].markdown)
        for trecho in ("O que conta como conselho", "Hoje são **4 conselhos**", "Em silêncio", "Citado por outros órgãos",
                       "não avaliado", "dia 20 do mês seguinte", "Limites"):
            self.assertIn(trecho, regras)

    def test_sla_fora_aparece_na_pagina(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            con.execute("""
                CREATE TABLE freshness_vitalidade (
                    primeiro_mes_coberto DATE, ultimo_mes_coberto DATE, mes_esperado DATE,
                    atraso_meses INTEGER, dentro_do_sla BOOLEAN
                );
                INSERT INTO freshness_vitalidade VALUES
                    (DATE '2026-07-01', DATE '2026-09-01', DATE '2026-10-01', 1, false);
            """)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        legendas = textos(at)
        self.assertTrue(any("mês esperado 10/2026" in t and "1 mês(es) fora do SLA" in t for t in legendas), legendas)

    def test_sla_adiantado_nao_mostra_atraso(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            con.execute("""
                CREATE TABLE freshness_vitalidade (
                    primeiro_mes_coberto DATE, ultimo_mes_coberto DATE, mes_esperado DATE,
                    atraso_meses INTEGER, dentro_do_sla BOOLEAN
                );
                INSERT INTO freshness_vitalidade VALUES
                    (DATE '2026-07-01', DATE '2026-09-01', DATE '2026-08-01', -1, true);
            """)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        legendas = textos(at)
        self.assertFalse(any("atraso -" in t for t in legendas), legendas)
        self.assertTrue(any("dentro do SLA" in t for t in legendas), legendas)

    def test_fct_vazio_sem_dou(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            con.execute("""
                DELETE FROM fct_conselho_mes;
                CREATE TABLE freshness_vitalidade (
                    primeiro_mes_coberto DATE, ultimo_mes_coberto DATE, mes_esperado DATE,
                    atraso_meses INTEGER, dentro_do_sla BOOLEAN
                );
                INSERT INTO freshness_vitalidade VALUES (NULL, NULL, DATE '2026-09-01', NULL, false);
            """)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        infos = [i.value for i in at.info]
        self.assertTrue(any("DOU ainda não carregado: rode `make ingest-mensal MES=AAAA-MM`, depois `make lake` e `make gold`." in i for i in infos), infos)
        self.assertEqual([m.label for m in at.metric], METRICAS)
        self.assertEqual(len(tabela_com(at, "Situação")), 4)

    def test_sem_banco(self):
        caminho_inexistente = os.path.join(self.tmpdir, "inexistente.duckdb")
        os.environ["PAINEL_GOLD"] = caminho_inexistente
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        erros = [e.value for e in at.error]
        self.assertGreater(len(erros), 0)
        self.assertIn("make gold", erros[0])

    def test_banco_vazio_sem_tabelas(self):
        duckdb.connect(self.gold_path).close()
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        erros = [e.value for e in at.error]
        self.assertGreater(len(erros), 0)
        self.assertIn("make gold", erros[0])

    def test_gold_ocupada_pede_nova_tentativa(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        with mock.patch("duckdb.connect", side_effect=duckdb.IOException("locked")):
            at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        erros = [e.value for e in at.error]
        self.assertGreater(len(erros), 0)
        self.assertIn("ocupada", erros[0])
        self.assertNotIn("rode make gold", erros[0])

    def test_sem_tabela_da_tipologia_pede_make_gold(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
            con.execute("DROP TABLE fct_ato")
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        erros = [e.value for e in at.error]
        self.assertGreater(len(erros), 0)
        self.assertIn("make gold", erros[0])

    def _abre(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        return at

    def test_filtro_de_situacao_reduz_as_linhas(self):
        at = self._abre()
        at.multiselect[0].set_value(["ativo"]).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(sorted(tabela_com(at, "Situação")["Conselho"]), ["Conselho Três", "Conselho Um"])

    def test_busca_por_sigla(self):
        at = self._abre()
        at.text_input[0].set_value("c4").run(timeout=60)
        self.assertEqual(list(tabela_com(at, "Situação")["Conselho"]), ["Conselho Quatro"])

    def test_so_citados(self):
        at = self._abre()
        at.toggle[0].set_value(True).run(timeout=60)
        self.assertEqual(sorted(tabela_com(at, "Situação")["Conselho"]), ["Conselho Quatro", "Conselho Um"])

    def test_detalhe_de_conselho_sem_planilha(self):
        at = self._abre()
        at.selectbox[0].set_value("C4 · Conselho Quatro").run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        infos = [i.value for i in at.info]
        self.assertTrue(any("sem atos classificados" in i for i in infos), infos)
        citacoes = tabela_com(at, "data_publicacao")
        self.assertEqual(len(citacoes), 2)

    def test_detalhe_de_conselho_da_planilha(self):
        at = self._abre()
        at.selectbox[0].set_value("C1 · Conselho Um").run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(any("sem atos classificados" in i.value for i in at.info))

    def test_graficos_altair(self):
        at = self._abre()
        # composição, atos por mês, heatmap, mensal do detalhe, tipologia por ano do detalhe e tipologia por conselho
        self.assertGreaterEqual(len(at.get("vega_lite_chart")), 5)

    def test_mapa_oculta_conselho_sem_ato(self):
        at = self._abre()
        # o Conselho Quatro não tem ato em nenhum mês: fica fora do mapa e é contado na legenda
        legendas = [c.value for c in at.caption]
        self.assertTrue(any("1 conselho(s) sem nenhum ato no período ficam fora do mapa" in t for t in legendas), legendas)

    def test_sem_tabela_de_mencoes_pede_make_gold(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
            con.execute("DROP TABLE fct_mencao")
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertIn("make gold", at.error[0].value)

    def test_painel_solta_a_gold(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        # mesmo processo: se o app deixasse a conexão read_only aberta, esta abertura para escrita falharia por configuração diferente
        with duckdb.connect(self.gold_path) as con:
            con.execute("CREATE TABLE sonda (x INTEGER)")
            con.execute("DROP TABLE sonda")


if __name__ == "__main__":
    unittest.main()
