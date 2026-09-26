"""python -m planilha {csv|relatorio|sql} [planilha.xlsx] — escreve no stdout.

Nada é gravado em disco pelo container: quem redireciona é o scripts/carga.sh.
"""

import csv
import sys

from .carga import sql
from .normalizar import normalizar
from .relatorio import relatorio

PLANILHA = "data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx"
COLUNAS = ["aba", "linha", "conselho", "id_planilha", "data_publicacao", "ref_legal", "ementa", "conteudo",
           "tipologia", "tipologia_original", "referente"]


def main(argv):
    if len(argv) not in (1, 2) or argv[0] not in ("csv", "relatorio", "sql"):
        sys.exit(__doc__.strip().splitlines()[0])
    res = normalizar(argv[1] if len(argv) == 2 else PLANILHA)
    if argv[0] == "csv":
        out = csv.writer(sys.stdout, lineterminator="\n")
        out.writerow(COLUNAS)
        out.writerows([getattr(a, c) for c in COLUNAS] for a in res.atos)
    else:
        sys.stdout.write(relatorio(res) if argv[0] == "relatorio" else sql(res))


main(sys.argv[1:])
