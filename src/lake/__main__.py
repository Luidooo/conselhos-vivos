"""Interface CLI do job analítico: python -m lake [destino]."""

import logging
from pathlib import Path
import sys

from .sync import extrair_oltp, obter_conexao, sincronizar_delta

DESTINO_PADRAO = Path("data/silver/atos")


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("lake")

    destino = Path(argv[0]) if argv else DESTINO_PADRAO
    logger.info("Iniciando sincronização OLTP -> Delta Lake em %s", destino)

    try:
        with obter_conexao() as conn:
            logger.info("Extraindo dados consolidados do PostgreSQL...")
            tabela = extrair_oltp(conn)
            logger.info("Extraídos %d atos do banco.", len(tabela))

        metricas = sincronizar_delta(tabela, destino)
        logger.info(
            "Concluído: inseridas=%d atualizadas=%d inalteradas=%d total_lake=%d",
            metricas["inseridas"],
            metricas["atualizadas"],
            metricas["inalteradas"],
            metricas["total_lake"],
        )
    except Exception as e:
        logger.error("Falha na sincronização do lake: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])