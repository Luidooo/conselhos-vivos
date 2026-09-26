# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas==3.0.6", "openpyxl==3.1.5"]
# ///
# Candidato "pandas + openpyxl" do diário de 26/09 (#3): pd.read_excel aba por aba.
# Contrato comum aos candidatos: ver o docstring de ../bench.py.
import csv
import datetime as dt
import sys

import pandas as pd

# aba: (linha do cabeçalho, coluna da data, coluna da referência legal, coluna da tipologia, coluna do tema)
ABAS = {
    "CNAS": (1, "DATA", None, "TIPOL_DECIS (M e J)", "TEMA"),
    "CONAMA": (2, "ANO E DATA", "DISP_LEG", "TIPO Incidência (geral)", "TEMA"),
    "CONCIDADES": (1, "DATA", "DIS_LEG", "TIPOL_DECIS", "TEMA"),
    "CONDRAF": (1, "DATA", "DIS_LEG", "TIPOL_DECIS", "TEMA"),
    "CNPIR": (1, "DATA (MÊS/DIA/ANO)", "DIS_LEG (ATO/ANO)", "TIPOL_DECIS ", "TEMA "),
}


def texto(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def ref_legal(aba, v):
    if aba == "CNPIR" and isinstance(v, dt.datetime):  # o Excel leu "1/2005" como data: o mês é o número do ato
        return f"{v.month}/{v.year}"
    return texto(v)


def main(xlsx):
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["aba", "linha", "id_versao", "data", "ref_legal", "tipologia", "tema"])
    for aba, (cab, c_data, c_ref, c_tip, c_tema) in ABAS.items():
        df = pd.read_excel(xlsx, sheet_name=aba, header=cab - 1, engine="openpyxl")
        df["linha"] = df.index + cab + 1  # índice 0 = primeira linha depois do cabeçalho
        df = df.dropna(how="all", subset=df.columns.drop("linha"))
        datas = pd.to_datetime(df[c_data]).dt.strftime("%Y-%m-%d")
        for (_, r), d in zip(df.iterrows(), datas):
            out.writerow([aba, r["linha"], texto(r["ID_VERSAO"]), d,
                          ref_legal(aba, r[c_ref]) if c_ref else "", texto(r[c_tip]), texto(r[c_tema])])


if __name__ == "__main__":
    main(sys.argv[1])
