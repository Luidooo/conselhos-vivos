"""Camada analítica em Delta Lake (ADR 0006).

Extrai os atos, órgãos e tipologias vigentes do OLTP (PostgreSQL) e grava
uma tabela Delta colunar particionada por ano e comprimida com zstd em data/silver/atos/.
"""

from .sync import extrair_oltp, sincronizar_delta

__all__ = ["extrair_oltp", "sincronizar_delta"]