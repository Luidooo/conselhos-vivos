"""python -m mencoes [--destino DIR] ZIP...: lê as matérias de cada ZIP da Seção 1 e grava na silver as
menções aos conselhos feitas por outros órgãos. Os nomes vêm do OLTP (todos os nomes que cada órgão já teve);
o escopo do ADR 0010 fica no dbt. Sem ZIP, cria a tabela vazia. Pode rodar de novo: não duplica.

Saída 0: gravou. Saída 1: falha de infraestrutura (ZIP que não abre, banco fora).
"""

import argparse
import logging
import sys
import zipfile
from pathlib import Path

from dou import materia

from . import Casador, mencoes

logger = logging.getLogger("mencoes")

# Os órgãos que já tiveram algum nome começando com "Conselho": o mesmo critério do ADR 0010, antes da seed de
# exclusões, que fica no dbt.
NOMES_SQL = """select orgao_id, nome from orgao_nome
               where orgao_id in (select orgao_id from orgao_nome group by 1 having bool_or(nome ilike 'conselho%'))"""


def nomes_do_oltp():
    import psycopg  # aqui, não no topo: os testes da extração não precisam do driver

    with psycopg.connect() as c:  # PGHOST, PGUSER, PGPASSWORD e PGDATABASE vêm do ambiente
        return c.execute(NOMES_SQL).fetchall()


def ler_zip(caminho, casador):
    linhas = []
    with zipfile.ZipFile(caminho) as z:
        for m, erro in materia.ler(z):
            if erro is None:
                linhas.extend({**x, "fonte": Path(caminho).name} for x in mencoes(m, casador))
    return linhas


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
    parser = argparse.ArgumentParser(prog="python -m mencoes", description=__doc__.split("\n\n")[0])
    parser.add_argument("--destino", default="/data/silver/mencoes")
    parser.add_argument("zips", nargs="*", metavar="ZIP")
    args = parser.parse_args(argv)
    from .silver import gravar, tabela  # deltalake só para quem grava

    try:
        casador = Casador(nomes_do_oltp())
        linhas = []
        for caminho in args.zips:
            achadas = ler_zip(caminho, casador)
            logger.info("lido zip=%s mencoes=%d", Path(caminho).name, len(achadas))
            linhas.extend(achadas)
        resumo = gravar(tabela(linhas), args.destino)
    except Exception as e:
        logger.error("run aborted err=%s", e)
        return 1
    logger.info("done inseridas=%d atualizadas=%d inalteradas=%d", resumo["inseridas"], resumo["atualizadas"], resumo["inalteradas"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
