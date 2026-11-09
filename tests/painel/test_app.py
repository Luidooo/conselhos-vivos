import os
import shutil
import tempfile
import unittest
import duckdb
from streamlit.testing.v1 import AppTest

APP = "/app/app.py"


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
                (3, DATE '2026-07-01', 0),
                (3, DATE '2026-08-01', 0),
                (3, DATE '2026-09-01', 0),
                (4, DATE '2026-07-01', 0),
                (4, DATE '2026-08-01', 0),
                (4, DATE '2026-09-01', 0);

            CREATE TABLE dim_conselho (
                orgao_id INTEGER,
                nome VARCHAR,
                sigla VARCHAR,
                atual BOOLEAN
            );
            INSERT INTO dim_conselho VALUES
                (1, 'Conselho Um', 'C1', true),
                (2, 'Conselho Dois', 'C2', true),
                (3, 'Conselho Três', 'C3', true),
                (4, 'Conselho Quatro', 'C4', true);

            CREATE TABLE fct_ato (
                orgao_id INTEGER,
                tipologia_sigla VARCHAR
            );
            INSERT INTO fct_ato VALUES
                (1, 'SEM'),
                (1, 'GEST'),
                (2, 'SEM');

            CREATE TABLE mart_vitalidade (
                orgao_id INTEGER,
                nome VARCHAR,
                sigla VARCHAR,
                mes_referencia DATE,
                ultimo_mes_com_ato DATE,
                atos_no_periodo INTEGER,
                meses_sem_publicar INTEGER,
                situacao VARCHAR
            );
            INSERT INTO mart_vitalidade VALUES
                (1, 'Conselho Um', 'C1', DATE '2026-09-01', DATE '2026-09-01', 10, 0, 'ativo'),
                (2, 'Conselho Dois', 'C2', DATE '2026-09-01', DATE '2026-07-01', 1, 2, 'em silêncio'),
                (3, 'Conselho Três', 'C3', DATE '2026-09-01', DATE '2026-07-01', 1, 2, 'em silêncio'),
                (4, 'Conselho Quatro', 'C4', DATE '2026-09-01', NULL, 0, NULL, 'sem ato no período coberto');
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
        self.assertEqual([m.label for m in at.metric], ["Ativos", "Em silêncio", "Sem ato no período coberto"])
        self.assertEqual([m.value for m in at.metric], ["1", "2", "1"])
        self.assertEqual(len(at.dataframe[0].value), 4)
        warnings = [w.value for w in at.warning]
        self.assertGreater(len(warnings), 0)
        self.assertIn("Sem ato no DOU não prova que o conselho parou", warnings[0])
        legendas = [c.value for c in at.caption]
        self.assertTrue(any("dentro do SLA" in t for t in legendas))

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
        legendas = [c.value for c in at.caption]
        self.assertTrue(any("mês esperado 10/2026" in t and "1 mês(es) fora do SLA" in t for t in legendas), legendas)

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
        self.assertTrue(any("DOU ainda não carregado: rode `make ingest-mensal`" in i for i in infos), infos)
        self.assertEqual([m.label for m in at.metric], ["Ativos", "Em silêncio", "Sem ato no período coberto"])
        self.assertEqual(len(at.dataframe[0].value), 4)

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


if __name__ == "__main__":
    unittest.main()
