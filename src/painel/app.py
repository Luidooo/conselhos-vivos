import os
import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Conselhos Vivos", layout="wide")

st.title("Quais conselhos nacionais de participação social ainda estão funcionando?")

GOLD = os.environ.get("PAINEL_GOLD", "/data/gold/conselhos.duckdb")

# A conexão abre e fecha a cada consulta, para não segurar a trava que o make gold precisa.
def consulta(sql):
    with duckdb.connect(GOLD, read_only=True) as con:
        return con.sql(sql).df()

def mes(d):
    return f"{d:%m/%Y}" if pd.notna(d) else ""

if not os.path.exists(GOLD):
    st.error("Não há gold em data/gold/conselhos.duckdb: rode make gold.")
    st.stop()

erro = None
try:
    periodo = consulta("select min(mes) as primeiro, max(mes) as ultimo from fct_conselho_mes").iloc[0]
    v = consulta("select * from mart_vitalidade order by situacao, meses_sem_publicar desc nulls last, nome")
    mensal = consulta("select mes, sum(atos) as atos from fct_conselho_mes group by mes order by mes")
    # o freshness é uma linha só, com nulos quando o DOU está vazio
    f = consulta("select * from freshness_vitalidade").iloc[0] if pd.notna(periodo["ultimo"]) else None
except duckdb.CatalogException:
    erro = "A gold não tem as tabelas do painel: rode make gold."
except duckdb.IOException:
    erro = "Não foi possível abrir a gold: rode make gold."

if erro:
    st.error(erro)
    st.stop()

if v.empty:
    st.error("A gold não tem conselhos: rode make gold.")
    st.stop()

if f is None:
    st.info("DOU ainda não carregado: rode `make ingest-mensal`.")
else:
    st.caption(f"DOU coberto de {mes(periodo['primeiro'])} a {mes(periodo['ultimo'])}.")
    st.caption(f"A situação abaixo vale para o último mês coberto ({mes(v['mes_referencia'].iloc[0])}), não para hoje.")
    situacao_sla = "dentro do SLA" if f["dentro_do_sla"] else f"{f['atraso_meses']} mês(es) fora do SLA"
    st.caption(
        f"SLA: último mês coberto {mes(f['ultimo_mes_coberto'])}, mês esperado {mes(f['mes_esperado'])}, "
        f"atraso {f['atraso_meses']} mês(es): {situacao_sla}. O mês M entra até o dia 20 do mês M+1."
    )

col1, col2, col3 = st.columns(3)
col1.metric("Ativos", int((v.situacao == "ativo").sum()))
col2.metric("Em silêncio", int((v.situacao == "em silêncio").sum()))
col3.metric("Sem ato no período coberto", int((v.situacao == "sem ato no período coberto").sum()))

st.warning("Sem ato no DOU não prova que o conselho parou: muito conselho funciona sem publicar no DOU. O limite de meses para 'em silêncio' é provisório e aguarda a definição da pesquisadora.")

st.subheader("A situação de cada conselho")
st.caption("Ativo: publicou nos últimos meses cobertos. Em silêncio: publicou antes e parou. Sem ato no período coberto: não publicou nenhum ato no período.")
tabela = v[["nome", "sigla", "situacao", "ultimo_mes_com_ato", "meses_sem_publicar", "atos_no_periodo"]].copy()
tabela["ultimo_mes_com_ato"] = tabela["ultimo_mes_com_ato"].map(mes)
st.dataframe(tabela, hide_index=True)

st.subheader("Atos de conselho por mês")
mensal["mes"] = mensal["mes"].map(mes)
st.bar_chart(mensal, x="mes", y="atos")

st.subheader("O que cada conselho decide")
st.caption("Atos por tipologia da pesquisadora. SEM: ainda não classificado.")
st.dataframe(
    consulta("""select d.nome, f.tipologia_sigla, count(*) as atos from fct_ato f join dim_conselho d on d.orgao_id = f.orgao_id and d.atual group by all order by d.nome, atos desc"""),
    hide_index=True,
)
