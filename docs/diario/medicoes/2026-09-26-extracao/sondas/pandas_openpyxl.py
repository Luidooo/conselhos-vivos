# Sonda do diário de 26/09 (#3): o que a chamada mais direta do pandas/openpyxl faz com cada armadilha, sem contorno.
# Roda dentro da imagem do candidato; /w tem planilha.xlsx e as mutações.
import json

import openpyxl
import pandas as pd


def tenta(f):
    try:
        return f()
    except Exception as e:  # a sonda registra o erro, não para
        return {"erro": f"{type(e).__name__}: {str(e)[:160]}"}


def cnas(arq):
    df = pd.read_excel(arq, sheet_name="CNAS")
    return {"linhas": len(df), "indice_da_linha_id_12": int(df.index[df["ID_VERSAO"] == 12][0])}


r = {
    "contagem pelo openpyxl (max_row - 1, 5 abas)": tenta(lambda: sum(
        openpyxl.load_workbook("/w/planilha.xlsx")[a].max_row - 1
        for a in ["CNAS", "CONAMA", "CONCIDADES", "CONDRAF", "CNPIR"])),
    "CNAS: read_excel padrão": tenta(lambda: cnas("/w/planilha.xlsx")),
    "CNAS com a linha 10 vazia": tenta(lambda: cnas("/w/linha_vazia.xlsx")),
    "CONAMA: read_excel padrão (cabeçalho na linha 2)": tenta(lambda: {
        "colunas": [str(c) for c in pd.read_excel("/w/planilha.xlsx", sheet_name="CONAMA").columns[:3]]}),
    "CNPIR: DIS_LEG da linha 2": tenta(lambda: repr(
        pd.read_excel("/w/planilha.xlsx", sheet_name="CNPIR")["DIS_LEG (ATO/ANO)"].iloc[0])),
    "CNAS: tipologia 99": tenta(lambda: repr(
        pd.read_excel("/w/planilha.xlsx", sheet_name="CNAS").set_index("ID_VERSAO").loc[47, "TIPOL_DECIS (M e J)"])),
    "CNAS com data 's/d': to_datetime(errors='coerce')": tenta(lambda: {
        "datas_nulas": int(pd.to_datetime(pd.read_excel("/w/data_texto.xlsx", sheet_name="CNAS")["DATA"],
                                          errors="coerce").isna().sum())}),
}
print(json.dumps(r, ensure_ascii=False))
