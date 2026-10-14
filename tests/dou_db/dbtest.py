"""Apoio dos testes do dou que gravam no banco (#52), o par do internal/dbtest do Go.

Cada teste roda numa transação que é desfeita no fim: o banco fica como
estava. Sem PGHOST no ambiente, os testes são pulados, não falham — assim o
`unittest discover` do host, sem banco, continua verde.

Uso:
    class MeuTeste(dbtest.CasoComBanco):
        def test_x(self):
            self.conn.execute(...)   # desfeito no tearDown
"""

import os
import unittest

import psycopg


def _dsn():
    # As mesmas variáveis que o psql e o lake leem: PG* ou POSTGRES_*.
    return {
        "host": os.getenv("PGHOST") or os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or 5432),
        "user": os.getenv("PGUSER") or os.getenv("POSTGRES_USER"),
        "password": os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB"),
    }


@unittest.skipUnless(os.getenv("PGHOST"), "sem PGHOST: testes de banco pulados")
class CasoComBanco(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(**_dsn(), autocommit=False)

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()
