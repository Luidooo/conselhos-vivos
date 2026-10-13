"""CDC leve: aplica no Delta as mudanças de `classificacao` pendentes no slot lógico do Postgres.

O slot (plugin `test_decoding`, que já vem na imagem oficial) só diz *quais* atos mudaram.
Os atos afetados são relidos do OLTP pela mesma consulta do `make lake`, então a regra
"revisão humana vence pipeline" e o checksum continuam num lugar só. O slot só avança
depois que o Delta foi gravado: entrega pelo menos uma vez, absorvida pelo MERGE idempotente.

Uso: python -m lake.cdc [destino]      (padrão: /data/silver/atos, o volume do container)
     python -m lake.cdc --drop-slot    (remove o slot; slot parado retém WAL)
Variável CDC_SLOT muda o nome do slot (padrão: conselhos_lake).
"""

import logging
import os
from pathlib import Path
import re
import sys
from typing import List, Tuple

from deltalake import DeltaTable
import psycopg

from .sync import extrair_oltp, obter_conexao, sincronizar_delta

DESTINO_PADRAO = Path("/data/silver/atos")  # volume do serviço cdc (o mesmo do lake)
SLOT_PADRAO = "conselhos_lake"

# Linha do test_decoding: "table public.classificacao: INSERT: id[bigint]:7 ato_id[bigint]:12 ..."
_INSERT_CLASSIFICACAO = re.compile(r"^table public\.classificacao: INSERT: .*?\bato_id\[bigint\]:(\d+)\b")

logger = logging.getLogger("lake.cdc")


def nome_do_slot() -> str:
    return os.getenv("CDC_SLOT") or SLOT_PADRAO


def garantir_slot(conn: psycopg.Connection, slot: str) -> bool:
    """Cria o slot se não existir. Devolve True se criou agora."""
    existe = conn.execute("SELECT 1 FROM pg_replication_slots WHERE slot_name = %s", (slot,)).fetchone()
    if existe:
        return False
    conn.execute("SELECT pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
    return True


def remover_slot(conn: psycopg.Connection, slot: str) -> bool:
    existe = conn.execute("SELECT 1 FROM pg_replication_slots WHERE slot_name = %s", (slot,)).fetchone()
    if not existe:
        return False
    conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
    return True


def extrair_ato_ids(linhas_decodificadas: List[str]) -> List[int]:
    """ato_ids (sem repetição, em ordem) dos INSERTs em classificacao; o resto do WAL é ignorado."""
    vistos = {}
    for texto in linhas_decodificadas:
        m = _INSERT_CLASSIFICACAO.match(texto)
        if m:
            vistos[int(m.group(1))] = None
    return list(vistos)


def ler_pendentes(conn: psycopg.Connection, slot: str) -> Tuple[List[int], str | None, int]:
    """Espia o slot sem consumir. Devolve (ato_ids, último LSN, nº de eventos de classificacao)."""
    rows = conn.execute("SELECT lsn::text, data FROM pg_logical_slot_peek_changes(%s, NULL, NULL)", (slot,)).fetchall()
    if not rows:
        return [], None, 0
    textos = [r[1] for r in rows]
    eventos = sum(1 for t in textos if _INSERT_CLASSIFICACAO.match(t))
    return extrair_ato_ids(textos), rows[-1][0], eventos


def confirmar(conn: psycopg.Connection, slot: str, lsn: str) -> None:
    """Consome do slot até lsn (só depois de o Delta ter sido gravado)."""
    conn.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s, %s::pg_lsn, NULL)", (slot, lsn))


def aplicar(destino: Path, conn: psycopg.Connection, ato_ids: List[int]) -> dict:
    if not DeltaTable.is_deltatable(str(destino)):
        raise RuntimeError(f"{destino} não é uma tabela Delta: rode `make lake` antes (carga inicial)")
    return sincronizar_delta(extrair_oltp(conn, ato_ids), destino)


def main(argv: List[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    slot = nome_do_slot()
    try:
        with obter_conexao() as conn:
            if argv[:1] == ["--drop-slot"]:
                logger.info("Slot %s %s.", slot, "removido" if remover_slot(conn, slot) else "não existia")
                return

            destino = Path(argv[0]) if argv else DESTINO_PADRAO
            if garantir_slot(conn, slot):
                logger.warning(
                    "Slot %s criado agora: só captura mudanças a partir deste momento. "
                    "Rode `make lake` para a carga completa.", slot)

            ato_ids, lsn, eventos = ler_pendentes(conn, slot)
            if lsn is None:
                logger.info("Concluído: pendentes=0 atos_afetados=0")
                return
            if not ato_ids:
                confirmar(conn, slot, lsn)  # só WAL de outras tabelas: nada a aplicar
                logger.info("Concluído: pendentes=0 atos_afetados=0")
                return

            metricas = aplicar(destino, conn, ato_ids)
            confirmar(conn, slot, lsn)
            logger.info(
                "Concluído: pendentes=%d atos_afetados=%d inseridas=%d atualizadas=%d inalteradas=%d total_lake=%d",
                eventos, len(ato_ids), metricas["inseridas"], metricas["atualizadas"],
                metricas["inalteradas"], metricas["total_lake"],
            )
    except Exception as e:
        logger.error("Falha no consumidor CDC: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
