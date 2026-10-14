"""Apoio dos testes do dou que gravam no banco (#52), o par do internal/dbtest do Go.

Cada teste roda numa transação que é desfeita no fim: o banco fica como
estava. Sem banco apontado (PGHOST ou POSTGRES_HOST) ou sem psycopg no
ambiente, os testes são pulados, não falham — assim o `unittest discover`
do host, sem banco e sem as bibliotecas dos containers, continua verde.

Uso:
    class MeuTeste(dbtest.CasoComBanco):
        def test_x(self):
            self.conn.execute(...)   # desfeito no tearDown
"""

import os
import unittest

try:
    import psycopg
except ImportError:  # o host sem as bibliotecas dos containers
    psycopg = None

HOST = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")


def _dsn():
    # As mesmas variáveis que o psql e o lake leem: PG* ou POSTGRES_*.
    return {
        "host": HOST,
        "port": int(os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or 5432),
        "user": os.getenv("PGUSER") or os.getenv("POSTGRES_USER"),
        "password": os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB"),
    }


@unittest.skipUnless(HOST and psycopg, "sem PGHOST/POSTGRES_HOST ou sem psycopg: testes de banco pulados")
class CasoComBanco(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(**_dsn(), autocommit=False)

    def tearDown(self):
        try:
            self.conn.rollback()
        finally:
            self.conn.close()
