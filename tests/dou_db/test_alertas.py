"""A gravação do ETL reverso no Postgres (src/alertas.gravar), em transação desfeita (dbtest)."""

import unittest
from datetime import date

import dbtest

from alertas import Alerta, gravar

SET = date(2026, 9, 1)


class Gravar(dbtest.CasoComBanco):
    def setUp(self):
        super().setUp()
        self.orgao = self.conn.execute("select orgao_id from conselho limit 1").fetchone()[0]

    def test_segunda_vez_nao_muda_nada(self):
        a = [Alerta(self.orgao, "em_silencio", SET, "x")]
        self.assertEqual(gravar(self.conn, a), (1, 0, 0))
        self.assertEqual(gravar(self.conn, a), (0, 0, 1))

    def test_detalhe_novo_atualiza_o_aberto(self):
        gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "x")])
        self.assertEqual(gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "y")]), (0, 1, 0))

    def test_tratado_nao_e_reescrito(self):
        gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "x")])
        self.conn.execute("update alerta set tratado_em = now(), tratado_por = (select min(id) from revisor), nota = 'ok' "
                          "where orgao_id = %s", (self.orgao,))
        self.assertEqual(gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "y")]), (0, 0, 1))
        self.assertEqual(self.conn.execute("select detalhe from alerta where orgao_id = %s", (self.orgao,)).fetchone()[0], "x")


if __name__ == "__main__":
    unittest.main()
