"""Medição do ADR 0006: particionamento e codec de compressão da camada analítica.

Executa benchmark comparativo real com os dados do banco:
1. Particionamento: anual vs diário (quantidade de arquivos, tamanho e tempo de agregação)
2. Compressão: Snappy vs ZSTD (tamanho em disco, agregação analítica e busca no texto)

Uso:
    docker compose run --rm lake python docs/adr/medicoes/0006-camada-analitica/bench.py
"""

import json
from pathlib import Path
import statistics
import tempfile
import time

from deltalake import write_deltalake, WriterProperties
import duckdb

from lake.sync import obter_conexao, extrair_oltp

REPETICOES = 200


def medir_tamanho_dir(caminho: Path) -> int:
    return sum(f.stat().st_size for f in caminho.rglob("*.parquet"))


def contar_arquivos_parquet(caminho: Path) -> int:
    return len(list(caminho.rglob("*.parquet")))


def medir_tempo(con: duckdb.DuckDBPyConnection, sql: str, n: int = REPETICOES) -> float:
    # Aquecimento
    con.execute(sql).fetchall()
    tempos = []
    for _ in range(n):
        t0 = time.perf_counter()
        con.execute(sql).fetchall()
        tempos.append(time.perf_counter() - t0)
    # Mediana em milissegundos
    return statistics.median(tempos) * 1000.0


def main():
    print("Extraindo dados do PostgreSQL...")
    with obter_conexao() as conn:
        tabela = extrair_oltp(conn)
    total_atos = len(tabela)
    print(f"Total de atos no banco: {total_atos}")

    con = duckdb.connect()
    con.execute("INSTALL delta; LOAD delta;")

    resultados = {
        "total_atos": total_atos,
        "particionamento": {},
        "compressao": {},
    }

    # -------------------------------------------------------------
    # 1. Benchmark de Particionamento (comprimido em ZSTD)
    # -------------------------------------------------------------
    print("\n==> 1. Medindo Particionamento (Anual vs Diário)...")
    with tempfile.TemporaryDirectory() as tmp_anual, tempfile.TemporaryDirectory() as tmp_diario:
        p_anual = Path(tmp_anual)
        p_diario = Path(tmp_diario)

        # Anual
        write_deltalake(
            str(p_anual),
            tabela,
            partition_by=["ano"],
            writer_properties=WriterProperties(compression="ZSTD"),
        )
        qtd_anual = contar_arquivos_parquet(p_anual)
        tam_anual = medir_tamanho_dir(p_anual)
        q_anual = f"SELECT orgao_sigla, tipologia_sigla, ano, count(*) FROM delta_scan('{p_anual}') GROUP BY 1, 2, 3"
        t_anual = medir_tempo(con, q_anual)

        # Diário
        write_deltalake(
            str(p_diario),
            tabela,
            partition_by=["ano", "data_publicacao"],
            writer_properties=WriterProperties(compression="ZSTD"),
        )
        qtd_diario = contar_arquivos_parquet(p_diario)
        tam_diario = medir_tamanho_dir(p_diario)
        q_diario = f"SELECT orgao_sigla, tipologia_sigla, ano, count(*) FROM delta_scan('{p_diario}') GROUP BY 1, 2, 3"
        t_diario = medir_tempo(con, q_diario)

        resultados["particionamento"] = {
            "anual": {
                "arquivos": qtd_anual,
                "tamanho_kb": round(tam_anual / 1024, 1),
                "tempo_ms": round(t_anual, 2),
            },
            "diario": {
                "arquivos": qtd_diario,
                "tamanho_kb": round(tam_diario / 1024, 1),
                "tempo_ms": round(t_diario, 2),
            },
        }

        print(f"  Anual:  {qtd_anual} arquivos | {tam_anual/1024:.1f} KB | {t_anual:.2f} ms")
        print(f"  Diário: {qtd_diario} arquivos | {tam_diario/1024:.1f} KB | {t_diario:.2f} ms")

    # -------------------------------------------------------------
    # 2. Benchmark de Compressão (particionado por ano)
    # -------------------------------------------------------------
    print("\n==> 2. Medindo Compressão (Snappy vs ZSTD)...")
    with tempfile.TemporaryDirectory() as tmp_snappy, tempfile.TemporaryDirectory() as tmp_zstd:
        p_snappy = Path(tmp_snappy)
        p_zstd = Path(tmp_zstd)

        # Snappy
        write_deltalake(
            str(p_snappy),
            tabela,
            partition_by=["ano"],
            writer_properties=WriterProperties(compression="SNAPPY"),
        )
        tam_snappy = medir_tamanho_dir(p_snappy)
        q_agg_snappy = f"SELECT orgao_sigla, tipologia_sigla, ano, count(*) FROM delta_scan('{p_snappy}') GROUP BY 1, 2, 3"
        t_agg_snappy = medir_tempo(con, q_agg_snappy)
        q_txt_snappy = f"SELECT count(*) FROM delta_scan('{p_snappy}') WHERE conteudo LIKE '%Regimento%' OR conteudo LIKE '%resolução%'"
        t_txt_snappy = medir_tempo(con, q_txt_snappy)

        # ZSTD
        write_deltalake(
            str(p_zstd),
            tabela,
            partition_by=["ano"],
            writer_properties=WriterProperties(compression="ZSTD"),
        )
        tam_zstd = medir_tamanho_dir(p_zstd)
        q_agg_zstd = f"SELECT orgao_sigla, tipologia_sigla, ano, count(*) FROM delta_scan('{p_zstd}') GROUP BY 1, 2, 3"
        t_agg_zstd = medir_tempo(con, q_agg_zstd)
        q_txt_zstd = f"SELECT count(*) FROM delta_scan('{p_zstd}') WHERE conteudo LIKE '%Regimento%' OR conteudo LIKE '%resolução%'"
        t_txt_zstd = medir_tempo(con, q_txt_zstd)

        diff_tam_pct = ((tam_zstd - tam_snappy) / tam_snappy) * 100.0

        resultados["compressao"] = {
            "snappy": {
                "tamanho_kb": round(tam_snappy / 1024, 1),
                "tempo_agregacao_ms": round(t_agg_snappy, 2),
                "tempo_texto_ms": round(t_txt_snappy, 2),
            },
            "zstd": {
                "tamanho_kb": round(tam_zstd / 1024, 1),
                "reducao_pct": round(diff_tam_pct, 1),
                "tempo_agregacao_ms": round(t_agg_zstd, 2),
                "tempo_texto_ms": round(t_txt_zstd, 2),
            },
        }

        print(f"  Snappy: {tam_snappy/1024:.1f} KB | agregação: {t_agg_snappy:.2f} ms | texto: {t_txt_snappy:.2f} ms")
        print(f"  ZSTD:   {tam_zstd/1024:.1f} KB ({diff_tam_pct:+.1f}%) | agregação: {t_agg_zstd:.2f} ms | texto: {t_txt_zstd:.2f} ms")

    out_json = Path(__file__).parent / "resultados.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nResultados gravados em {out_json}")


if __name__ == "__main__":
    main()

