# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb==1.5.5"]
# ///
# Candidato "DuckDB" do diário de 26/09 (#3): read_xlsx (extensão excel) e a normalização em SQL.
# Contrato comum aos candidatos: ver o docstring de ../bench.py.
import sys

import duckdb

# aba: (linha do cabeçalho, coluna da data, coluna da referência legal, coluna da tipologia)
# O DuckDB apara os espaços dos nomes de coluna ("TEMA " do CNPIR vira "TEMA").
ABAS = {
    "CNAS": (1, "DATA", None, "TIPOL_DECIS (M e J)"),
    "CONAMA": (2, "ANO E DATA", "DISP_LEG", "TIPO Incidência (geral)"),
    "CONCIDADES": (1, "DATA", "DIS_LEG", "TIPOL_DECIS"),
    "CONDRAF": (1, "DATA", "DIS_LEG", "TIPOL_DECIS"),
    "CNPIR": (1, "DATA (MÊS/DIA/ANO)", "DIS_LEG (ATO/ANO)", "TIPOL_DECIS"),
}

# all_varchar: sem isso a coluna DIS_LEG do CNPIR vira DATE e a célula "7/2013 (moção)" aborta a leitura.
# stop_at_empty=false: devolve as linhas só formatadas, e o row_number() vira a linha do Excel.
POR_ABA = """
SELECT {ordem} AS ordem, '{aba}' AS aba, linha,
       CAST(CAST(ID_VERSAO AS DOUBLE) AS BIGINT) AS id_versao,
       DATE '1899-12-30' + CAST(CAST("{data}" AS DOUBLE) AS INTEGER) AS data,
       {ref} AS ref_legal,
       coalesce(CAST(TRY_CAST("{tip}" AS DOUBLE) AS BIGINT)::VARCHAR, "{tip}") AS tipologia,
       TEMA AS tema
FROM (SELECT row_number() OVER () + {cab} AS linha, *
      FROM read_xlsx(getvariable('xlsx'), sheet = '{aba}', all_varchar = true, stop_at_empty = false))
WHERE concat_ws('', *COLUMNS(* EXCLUDE (linha))) <> ''
"""

# CNPIR: o Excel leu "1/2005" como data; o mês é o número do ato
REF_CNPIR = """CASE WHEN TRY_CAST("{c}" AS DOUBLE) IS NULL THEN "{c}" ELSE
  month(DATE '1899-12-30' + CAST(CAST("{c}" AS DOUBLE) AS INTEGER)) || '/' ||
  year(DATE '1899-12-30' + CAST(CAST("{c}" AS DOUBLE) AS INTEGER)) END"""


def main(xlsx):
    con = duckdb.connect()
    con.execute("INSTALL excel; LOAD excel")
    con.execute("SET VARIABLE xlsx = ?", [xlsx])
    partes = []
    for ordem, (aba, (cab, c_data, c_ref, c_tip)) in enumerate(ABAS.items()):
        ref = "''" if c_ref is None else REF_CNPIR.format(c=c_ref) if aba == "CNPIR" else f'coalesce("{c_ref}", \'\')'
        partes.append(POR_ABA.format(ordem=ordem, aba=aba, cab=cab, data=c_data, ref=ref, tip=c_tip))
    con.execute(f"COPY (SELECT * EXCLUDE (ordem) FROM ({' UNION ALL '.join(partes)}) ORDER BY ordem, linha) "
                "TO '/dev/stdout' (HEADER)")


if __name__ == "__main__":
    main(sys.argv[1])
