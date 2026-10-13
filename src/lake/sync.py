"""Lógica de extração do PostgreSQL e sincronização idempotente com Delta Lake."""

import datetime as dt
import hashlib
import os
from pathlib import Path
from typing import Any, Dict

from deltalake import DeltaTable, WriterProperties, write_deltalake
import psycopg
import pyarrow as pa

QUERY_OLTP = """
SELECT 
    a.id AS ato_id,
    a.origem,
    COALESCE(a.id_dou, a.id_planilha::text) AS id_origem,
    a.versao,
    a.data_publicacao,
    EXTRACT(YEAR FROM a.data_publicacao)::int AS ano,
    o.id AS orgao_id,
    COALESCE(nome_epoca.nome, n_vigente.nome) AS orgao_nome,
    o.sigla AS orgao_sigla,
    o.codigo_siorg,
    a.ref_legal,
    a.ementa,
    a.conteudo,
    cv.tipologia_sigla,
    r.tipo AS revisor_tipo
FROM ato a
JOIN orgao o ON o.id = a.orgao_id
-- Nome vigente do órgão como fallback (LEFT JOIN para conselho extinto ou sem nome com fim aberto):
LEFT JOIN orgao_nome n_vigente ON n_vigente.orgao_id = o.id AND n_vigente.data_fim IS NULL
-- Nome histórico vigente na data da publicação do ato (ADR 0004):
LEFT JOIN orgao_nome nome_epoca ON nome_epoca.orgao_id = o.id 
    AND a.data_publicacao >= nome_epoca.data_inicio 
    AND (nome_epoca.data_fim IS NULL OR a.data_publicacao <= nome_epoca.data_fim)
-- Classificação vigente (prioriza revisão humana sobre pipeline):
LEFT JOIN LATERAL (
    SELECT cv.tipologia_sigla, cv.revisor_id, cv.criado_em
    FROM classificacao_vigente cv
    JOIN revisor r ON r.id = cv.revisor_id
    WHERE cv.ato_id = a.id
    ORDER BY (r.tipo = 'HUMANO') DESC, cv.criado_em DESC
    LIMIT 1
) cv ON true
LEFT JOIN revisor r ON r.id = cv.revisor_id
-- Sem lista (NULL): todos os atos (make lake). Com lista: só os atos afetados (make cdc).
WHERE (%(ato_ids)s::bigint[] IS NULL OR a.id = ANY(%(ato_ids)s::bigint[]))
ORDER BY a.data_publicacao, a.id;
"""

ARROW_SCHEMA = pa.schema([
    ("ato_id", pa.int64()),
    ("origem", pa.string()),
    ("id_origem", pa.string()),
    ("versao", pa.int32()),
    ("data_publicacao", pa.date32()),
    ("ano", pa.int32()),
    ("orgao_id", pa.int32()),
    ("orgao_nome", pa.string()),
    ("orgao_sigla", pa.string()),
    ("codigo_siorg", pa.int32()),
    ("ref_legal", pa.string()),
    ("ementa", pa.string()),
    ("conteudo", pa.string()),
    ("tipologia_sigla", pa.string()),
    ("revisor_tipo", pa.string()),
    ("checksum", pa.string()),
    ("atualizado_em", pa.timestamp("us", tz="UTC")),
])


def calcular_checksum(
    ementa: str | None,
    conteudo: str | None,
    tipologia: str | None,
    orgao_id: int,
    orgao_nome: str | None,
    orgao_sigla: str | None,
    codigo_siorg: int | None,
    revisor_tipo: str | None,
    ref_legal: str | None,
    data_publicacao: Any,
) -> str:
    """Hash determinístico de todo o conteúdo para merge seguro e sem armadilhas de NULL."""
    conteudo_str = (
        f"{ementa or ''}|{conteudo or ''}|{tipologia or ''}|{orgao_id}|"
        f"{orgao_nome or ''}|{orgao_sigla or ''}|{codigo_siorg or ''}|"
        f"{revisor_tipo or ''}|{ref_legal or ''}|{data_publicacao or ''}"
    )
    return hashlib.md5(conteudo_str.encode("utf-8")).hexdigest()


def obter_conexao() -> psycopg.Connection:
    """Conecta ao Postgres respeitando PG* ou POSTGRES_* do ambiente."""
    host = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST") or "localhost"
    port = int(os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or "5432")
    user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER") or "conselhos"
    password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD") or "conselhos"
    dbname = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB") or "conselhos"

    return psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        autocommit=True,
    )


def extrair_oltp(conn: psycopg.Connection, ato_ids: list[int] | None = None) -> pa.Table:
    """Lê os atos consolidados do OLTP (todos, ou só os de ato_ids) e retorna uma tabela PyArrow tipada."""
    agora = dt.datetime.now(dt.timezone.utc)
    
    with conn.cursor() as cur:
        cur.execute(QUERY_OLTP, {"ato_ids": ato_ids})
        linhas = cur.fetchall()

    if not linhas:
        return pa.Table.from_arrays([pa.array([], type=f.type) for f in ARROW_SCHEMA], schema=ARROW_SCHEMA)

    dados = {campo.name: [] for campo in ARROW_SCHEMA}
    for r in linhas:
        dados["ato_id"].append(r[0])
        dados["origem"].append(r[1])
        dados["id_origem"].append(r[2])
        dados["versao"].append(r[3])
        dados["data_publicacao"].append(r[4])
        dados["ano"].append(r[5])
        dados["orgao_id"].append(r[6])
        dados["orgao_nome"].append(r[7])
        dados["orgao_sigla"].append(r[8])
        dados["codigo_siorg"].append(r[9])
        dados["ref_legal"].append(r[10])
        dados["ementa"].append(r[11])
        dados["conteudo"].append(r[12])
        dados["tipologia_sigla"].append(r[13])
        dados["revisor_tipo"].append(r[14])
        dados["checksum"].append(
            calcular_checksum(
                ementa=r[11],
                conteudo=r[12],
                tipologia=r[13],
                orgao_id=r[6],
                orgao_nome=r[7],
                orgao_sigla=r[8],
                codigo_siorg=r[9],
                revisor_tipo=r[14],
                ref_legal=r[10],
                data_publicacao=r[4],
            )
        )
        dados["atualizado_em"].append(agora)

    arrays = [pa.array(dados[campo.name], type=campo.type) for campo in ARROW_SCHEMA]
    return pa.Table.from_arrays(arrays, schema=ARROW_SCHEMA)


def sincronizar_delta(tabela_arrow: pa.Table, destino: Path) -> Dict[str, Any]:
    """Grava ou faz MERGE idempotente na tabela Delta em destino particionada por ano e comprimida com ZSTD."""
    destino_str = str(destino)
    total_fonte = len(tabela_arrow)
    writer_props = WriterProperties(compression="ZSTD")

    # 1. Primeira execução: a tabela ainda não existe
    if not DeltaTable.is_deltatable(destino_str):
        destino.mkdir(parents=True, exist_ok=True)
        write_deltalake(
            destino_str,
            tabela_arrow,
            partition_by=["ano"],
            mode="error",
            writer_properties=writer_props,
        )
        return {
            "inseridas": total_fonte,
            "atualizadas": 0,
            "inalteradas": 0,
            "total_lake": total_fonte,
        }

    # 2. Execuções subsequentes: MERGE idempotente na chave do ato no OLTP (ato_id)
    dt_table = DeltaTable(destino_str)
    
    predicate = "target.ato_id = source.ato_id"
    update_condition = "target.checksum != source.checksum"

    merge_res = (
        dt_table.merge(
            source=tabela_arrow,
            predicate=predicate,
            source_alias="source",
            target_alias="target",
            writer_properties=writer_props,
        )
        .when_matched_update_all(predicate=update_condition)
        .when_not_matched_insert_all()
        .execute()
    )

    inseridas = merge_res.get("num_target_rows_inserted", 0)
    atualizadas = merge_res.get("num_target_rows_updated", 0)
    inalteradas = total_fonte - inseridas - atualizadas

    dt_atualizada = DeltaTable(destino_str)
    total_lake = dt_atualizada.count()

    return {
        "inseridas": inseridas,
        "atualizadas": atualizadas,
        "inalteradas": inalteradas,
        "total_lake": total_lake,
    }