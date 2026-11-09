import os
import duckdb
import streamlit as st

st.set_page_config(page_title="Conselhos Vivos", layout="wide")

st.title("Quais conselhos nacionais de participação social ainda estão funcionando?")

GOLD = os.environ.get("PAINEL_GOLD", "/data/gold/conselhos.duckdb")

# A conexão abre e fecha a cada consulta, para não segurar a trava que o make gold precisa.
def consulta(sql):
    with duckdb.connect(GOLD, read_only=True) as con:
        return con.sql(sql).df()

if not os.path.exists(GOLD):
    st.error("Não há gold em data/gold/conselhos.duckdb: rode make gold.")
    st.stop()

erro = None
try:
    periodo = consulta("select min(mes) as primeiro, max(mes) as ultimo from fct_conselho_mes").iloc[0]
    v = consulta("select * from mart_vitalidade order by situacao, meses_sem_publicar desc nulls last, nome")
except duckdb.CatalogException:
    erro = "A gold não tem as tabelas do painel: rode make gold."
except duckdb.IOException:
    erro = "Não foi possível abrir a gold: rode make gold."

if erro:
    st.error(erro)
    st.stop()

st.caption(f"DOU coberto de {periodo['primeiro']:%m/%Y} a {periodo['ultimo']:%m/%Y}.")

mes_ref = v["mes_referencia"].iloc[0]
st.caption(f"A situação abaixo vale para o último mês coberto ({mes_ref:%m/%Y}), não para hoje.")

tem_freshness = not consulta("select 1 from information_schema.tables where table_name = 'freshness_vitalidade'").empty
# shortcut: sem freshness_vitalidade até a #72 entrar; tirar este ramo quando ela entrar.
if tem_freshness:
    f = consulta("select * from freshness_vitalidade").iloc[0]
    situacao_sla = "dentro do SLA" if f["dentro_do_sla"] else f"{f['atraso_meses']} mês(es) fora do SLA"
    st.caption(
        f"Último mês coberto: {f['ultimo_mes_coberto']:%m/%Y}. "
        f"Mês esperado: {f['mes_esperado']:%m/%Y}. "
        f"Atraso: {f['atraso_meses']} mês(es) ({situacao_sla}). "
        "SLA: o mês M entra até o dia 20 do mês M+1."
    )
else:
    st.info("SLA ainda não disponível (#72)")

col1, col2, col3 = st.columns(3)
col1.metric("Ativos", int((v.situacao == "ativo").sum()))
col2.metric("Em silêncio", int((v.situacao == "em silêncio").sum()))
col3.metric("Sem ato no período coberto", int((v.situacao == "sem ato no período coberto").sum()))

st.warning("Sem ato no DOU não prova que o conselho parou: muito conselho funciona sem publicar no DOU. O limite de meses para 'em silêncio' é provisório e aguarda a definição da pesquisadora.")

st.subheader("A situação de cada conselho")
st.caption("Ativo: publicou nos últimos meses cobertos. Em silêncio: publicou antes e parou. Sem ato no período coberto: não publicou nenhum ato no período.")
st.dataframe(v[["nome", "sigla", "situacao", "ultimo_mes_com_ato", "meses_sem_publicar", "atos_no_periodo"]], hide_index=True)

st.subheader("Atos de conselho por mês")
st.bar_chart(consulta("select mes, sum(atos) as atos from fct_conselho_mes group by mes order by mes"), x="mes", y="atos")

st.subheader("O que cada conselho decide")
st.caption("Atos por tipologia da pesquisadora. SEM: ainda não classificado.")
st.dataframe(
    consulta("""select d.nome, f.tipologia_sigla, count(*) as atos from fct_ato f join dim_conselho d on d.orgao_id = f.orgao_id and d.atual group by all order by d.nome, atos desc"""),
    hide_index=True,
)
