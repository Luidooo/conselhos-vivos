"""A conexão com o banco de curadoria, pelas mesmas variáveis que o psql e o
lake leem (PG* ou POSTGRES_*). Transação explícita (autocommit=False): quem
abre decide quando confirma — o persist confirma uma vez por ZIP.

Não reusa lake.sync.obter_conexao de propósito: aquela é autocommit.
"""

import os


def conectar():
    # Importado aqui, não no topo: o serviço carga (testes sem banco) não tem o
    # psycopg, e `python -m dou` precisa importar o persist para listar os
    # subcomandos. Quem não grava não paga o driver.
    import psycopg

    return psycopg.connect(
        host=os.getenv("PGHOST") or os.getenv("POSTGRES_HOST") or "localhost",
        port=int(os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or 5432),
        user=os.getenv("PGUSER") or os.getenv("POSTGRES_USER"),
        password=os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB"),
        autocommit=False,
    )
