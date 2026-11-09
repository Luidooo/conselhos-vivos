"""Grava as menções na silver: uma tabela Delta particionada por ano, comprimida com ZSTD, com MERGE
idempotente na chave (id_dou, orgao_id), no molde do lake (ADR 0006)."""

import datetime as dt
import hashlib
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable, WriterProperties, write_deltalake

ESQUEMA = pa.schema([
    ("id_dou", pa.string()),
    ("orgao_id", pa.int32()),
    ("nome_citado", pa.string()),
    ("data_publicacao", pa.date32()),
    ("ano", pa.int32()),
    ("tipo_ato", pa.string()),
    ("publicador", pa.string()),
    ("titulo", pa.string()),
    ("ementa", pa.string()),
    ("assunto", pa.string()),
    ("fonte", pa.string()),
    ("checksum", pa.string()),
    ("atualizado_em", pa.timestamp("us", tz="UTC")),
])

CAMPOS_DO_CONTEUDO = ("nome_citado", "data_publicacao", "tipo_ato", "publicador", "titulo", "ementa", "assunto")


def tabela(linhas, fonte=""):
    """As menções como tabela Arrow, com ano, fonte, checksum do conteúdo e a hora da gravação."""
    agora = dt.datetime.now(dt.timezone.utc)
    registros = []
    for m in linhas:
        conteudo = "|".join(str(m.get(c) or "") for c in CAMPOS_DO_CONTEUDO)
        registros.append({**{c: m.get(c) for c in ("id_dou", "orgao_id") + CAMPOS_DO_CONTEUDO},
                          "ano": m["data_publicacao"].year, "fonte": m.get("fonte", fonte),
                          "checksum": hashlib.md5(conteudo.encode("utf-8")).hexdigest(), "atualizado_em": agora})
    return pa.Table.from_pylist(registros, schema=ESQUEMA)


def gravar(t, destino):
    """MERGE de t em destino. Uma segunda execução com o mesmo conteúdo não muda nada; sem nada a gravar,
    a tabela é criada vazia, para o dbt achar a fonte num clone limpo."""
    destino = Path(destino)
    props = WriterProperties(compression="ZSTD")
    if not DeltaTable.is_deltatable(str(destino)):
        destino.mkdir(parents=True, exist_ok=True)
        write_deltalake(str(destino), t, partition_by=["ano"], mode="error", writer_properties=props)
        return {"inseridas": len(t), "atualizadas": 0, "inalteradas": 0}
    if len(t) == 0:
        return {"inseridas": 0, "atualizadas": 0, "inalteradas": 0}
    r = (DeltaTable(str(destino))
         .merge(source=t, predicate="target.id_dou = source.id_dou and target.orgao_id = source.orgao_id",
                source_alias="source", target_alias="target", writer_properties=props)
         .when_matched_update_all(predicate="target.checksum != source.checksum")
         .when_not_matched_insert_all()
         .execute())
    inseridas, atualizadas = r.get("num_target_rows_inserted", 0), r.get("num_target_rows_updated", 0)
    return {"inseridas": inseridas, "atualizadas": atualizadas, "inalteradas": len(t) - inseridas - atualizadas}
