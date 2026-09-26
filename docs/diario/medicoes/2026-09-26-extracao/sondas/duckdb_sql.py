# Sonda do diário de 26/09 (#3): o que a chamada mais direta do read_xlsx faz com cada armadilha, sem contorno.
# Roda dentro da imagem do candidato; /w tem planilha.xlsx e as mutações.
import json

import duckdb

con = duckdb.connect()
con.execute("LOAD excel")


def tenta(sql):
    try:
        return con.execute(sql).fetchall()
    except Exception as e:  # a sonda registra o erro, não para
        return {"erro": f"{type(e).__name__}: {str(e)[:160]}"}


r = {
    "CNAS: read_xlsx padrão": tenta("SELECT count(*) FROM read_xlsx('/w/planilha.xlsx', sheet='CNAS')"),
    "CNAS com a linha 10 vazia": tenta("SELECT count(*) FROM read_xlsx('/w/linha_vazia.xlsx', sheet='CNAS')"),
    "CONAMA: read_xlsx padrão (cabeçalho na linha 2)": tenta(
        "SELECT count(*), min(ID_VERSAO) FROM read_xlsx('/w/planilha.xlsx', sheet='CONAMA')"),
    "CNPIR: read_xlsx padrão": tenta("SELECT count(*) FROM read_xlsx('/w/planilha.xlsx', sheet='CNPIR')"),
    "CNPIR: ignore_errors=true, DIS_LEG nulos": tenta(
        "SELECT count(*) FILTER (WHERE \"DIS_LEG (ATO/ANO)\" IS NULL), min(\"DIS_LEG (ATO/ANO)\") "
        "FROM read_xlsx('/w/planilha.xlsx', sheet='CNPIR', ignore_errors=true)"),
    "CNAS: tipologia 99": tenta(
        "SELECT \"TIPOL_DECIS (M e J)\" FROM read_xlsx('/w/planilha.xlsx', sheet='CNAS') WHERE ID_VERSAO = 47"),
    "CNAS com data 's/d': read_xlsx padrão": tenta(
        "SELECT count(*) FROM read_xlsx('/w/data_texto.xlsx', sheet='CNAS')"),
}
print(json.dumps(r, ensure_ascii=False, default=str))
