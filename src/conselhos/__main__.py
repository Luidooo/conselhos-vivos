"""python -m conselhos {sql|relatorio|siorg} — escreve no stdout.

sql e relatorio leem a planilha, o arquivo de decisões e o recorte do SIORG, sem rede.
siorg baixa o SIORG e escreve o recorte novo (make siorg, o único que precisa de rede).
"""

import sys

from .carga import sql
from .identidade import resolver
from .relatorio import relatorio

PLANILHA = "data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx"
DECISOES = "data/referencia/conselhos-decisoes.csv"
SIORG = "data/referencia/siorg-conselhos.csv"


def main(argv):
    if len(argv) != 1 or argv[0] not in ("sql", "relatorio", "siorg"):
        sys.exit(__doc__.strip().splitlines()[0])
    if argv[0] == "siorg":
        from . import siorg
        sys.stdout.write(siorg.recorte(PLANILHA, siorg.baixar()))
        return
    res = resolver(PLANILHA, DECISOES, SIORG)
    sys.stdout.write(sql(res) if argv[0] == "sql" else relatorio(res))


main(sys.argv[1:])
