"""python -m dou extract [--html] EDICAO.zip: as matérias de uma edição já em
disco, uma por linha em JSON no stdout, para um ZIP ser inspecionado sem
banco (o par do cmd/extract do Go). Um ZIP por execução.

O log e o resumo vão para o stderr. Entrada que não é XML é ignorada; XML
que não é matéria é falha, e a saída é 1 mesmo com o resto impresso.
"""

import argparse
import json
import logging
import sys
import zipfile
from dataclasses import dataclass

from . import materia

logger = logging.getLogger("dou.extract")


@dataclass
class Resumo:
    lidas: int = 0      # matéria impressa
    ignoradas: int = 0  # entrada que não é XML, como a imagem de uma matéria
    falhou: int = 0     # XML que não leu como matéria


def extrair(saida, caminho, com_html=False):
    """Imprime cada matéria do ZIP em `saida`. Entrada ruim é logada e contada;
    ZIP que não abre encerra a execução (zipfile.BadZipFile / OSError)."""
    resumo = Resumo()
    with zipfile.ZipFile(caminho) as edicao:
        for item, erro in materia.ler(edicao):
            if erro is not None:
                if isinstance(erro.__cause__, materia.NaoEXML):
                    resumo.ignoradas += 1
                    logger.info("ignorada zip=%s erro=%s", caminho, erro)
                else:
                    resumo.falhou += 1
                    logger.warning("falhou zip=%s erro=%s", caminho, erro)
                continue
            saida.write(json.dumps(item.como_json(com_html), ensure_ascii=False) + "\n")
            resumo.lidas += 1
    return resumo


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
    parser = argparse.ArgumentParser(prog="python -m dou extract", description=__doc__.split("\n\n")[0])
    parser.add_argument("-html", "--html", dest="com_html", action="store_true",
                        help="also print <Texto> as published, HTML and all")
    parser.add_argument("zip", metavar="EDICAO.zip")
    args = parser.parse_args(argv)
    try:
        resumo = extrair(sys.stdout, args.zip, args.com_html)
    except (zipfile.BadZipFile, OSError) as e:
        logger.error("run aborted err=opening %s: %s", args.zip, e)
        return 1
    logger.info("done lidas=%d ignoradas=%d falhou=%d", resumo.lidas, resumo.ignoradas, resumo.falhou)
    return 1 if resumo.falhou else 0
