"""python -m dou fetch-mensal --month AAAA-MM: um mês da Seção 1 pelos dados
abertos (o par do cmd/fetch-mensal do Go). Só orquestra: argumentos,
configuração, log, código de saída; o download é do dadosabertos.

Saída 2: erro de uso. Saída 1: mês ainda não publicado, ou qualquer falha.
DADOS_ABERTOS_OUTPUT_DIR diz onde gravar (padrão: o diretório corrente).
"""

import argparse
import logging
import os
import sys

from . import dadosabertos
from .bronze import Bronze

logger = logging.getLogger("dou.fetch-mensal")


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
    parser = argparse.ArgumentParser(prog="python -m dou fetch-mensal", description=__doc__.split("\n\n")[0],
                                     epilog="A month already on disk is not asked for again. A month is published "
                                            "about two weeks after it ends; one that is not out yet exits with 1 "
                                            "and writes nothing.")
    parser.add_argument("--month", required=True, metavar="YYYY-MM", help="month to download; required")
    args = parser.parse_args(argv)  # sai com 2 em erro de uso, como o flag do Go
    try:
        mes = dadosabertos.Mes.parse(args.month)
    except ValueError as e:
        parser.error(f"--month: {e}")

    destino = os.environ.get("DADOS_ABERTOS_OUTPUT_DIR", ".")
    try:
        bronze = Bronze(destino)
        logger.info("iniciando mes=%s destino=%s", mes, destino)
        dadosabertos.Cliente().baixar_mes(mes, bronze)
    except dadosabertos.NaoPublicado as e:
        logger.error("mes ainda nao publicado mes=%s err=%s", mes, e)
        return 1
    except Exception as e:
        logger.error("run aborted err=%s", e)
        return 1
    return 0
