import os
import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Conselhos Vivos", layout="wide")

# O desenho do site (site/.vitepress/theme/custom.css): a fonte do sistema e os cartões com raio de 14 px e sombra
# suave. As cores ficam no .streamlit/config.toml.
st.markdown("""<style>
html, body, [class*="css"], .stMarkdown, h1, h2, h3 {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", "Helvetica Neue", Helvetica, Arial, sans-serif;
}
h1 { font-weight: 700; letter-spacing: -0.02em; }
h2, h3 { font-weight: 600; letter-spacing: -0.01em; }
[data-testid="stMetric"] {
  background: #f5f5f7; border-radius: 14px; padding: 18px 22px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 10px 30px rgba(0, 0, 0, 0.06);
}
[data-testid="stMetricValue"] { color: #1d1d1f; font-weight: 600; }
[data-testid="stMetricLabel"] { color: #6e6e73; }
[data-testid="stDataFrame"], [data-testid="stVegaLiteChart"] { border-radius: 14px; overflow: hidden; }
</style>""", unsafe_allow_html=True)

st.title("Quais conselhos nacionais de participação social ainda estão funcionando?")

GOLD = os.environ.get("PAINEL_GOLD", "/data/gold/conselhos.duckdb")

def mes(d):
    return f"{d:%m/%Y}" if pd.notna(d) else ""

def participacao(x):
    # nulo é não avaliado, não falso: só o falso vira "não"
    return "não avaliado" if pd.isna(x) else ("sim" if x else "não")

if not os.path.exists(GOLD):
    st.error("Não há gold em data/gold/conselhos.duckdb: rode make gold.")
    st.stop()

erro = None
# uma conexão por carga, fechada antes de desenhar: não segura a trava que o make gold precisa
try:
    with duckdb.connect(GOLD, read_only=True) as con:
        periodo = con.sql("select min(mes) as primeiro, max(mes) as ultimo from fct_conselho_mes").df().iloc[0]
        # eh_participativo vem da dim_conselho: a marca da pesquisadora, sem filtrar nada aqui (ADR 0010, ponto 4)
        v = con.sql("select m.*, d.eh_participativo from mart_vitalidade m left join (select distinct orgao_id, eh_participativo from dim_conselho) d on d.orgao_id = m.orgao_id order by m.situacao, m.meses_sem_publicar desc nulls last, m.nome").df()
        mensal = con.sql("select mes, sum(atos) as atos from fct_conselho_mes group by mes order by mes").df()
        # o freshness é uma linha só, com nulos quando o DOU está vazio
        f = con.sql("select * from freshness_vitalidade").df().iloc[0] if pd.notna(periodo["ultimo"]) else None
        tipologia = con.sql("select v.nome, f.origem, f.tipologia_sigla, count(*) as atos from mart_vitalidade v join fct_ato f on f.orgao_id = v.orgao_id group by all order by v.nome, atos desc").df()
except duckdb.CatalogException:
    erro = "A gold não tem as tabelas do painel: rode make gold."
except duckdb.IOException:
    erro = "A gold está ocupada ou sendo gerada pelo make gold: tente de novo em alguns segundos."

if erro:
    st.error(erro)
    st.stop()

if v.empty:
    st.error("A gold não tem conselhos: rode make gold.")
    st.stop()

if f is None:
    st.info("DOU ainda não carregado: rode `make ingest-mensal MES=AAAA-MM`, depois `make lake` e `make gold`.")
else:
    st.caption(f"DOU coberto de {mes(periodo['primeiro'])} a {mes(periodo['ultimo'])}.")
    st.caption(f"A situação abaixo vale para o último mês coberto ({mes(v['mes_referencia'].iloc[0])}), não para hoje.")
    sla = "dentro do SLA" if f["dentro_do_sla"] else f"atraso {f['atraso_meses']} mês(es) fora do SLA"
    st.caption(
        f"SLA: último mês coberto {mes(f['ultimo_mes_coberto'])}, mês esperado {mes(f['mes_esperado'])}, "
        f"{sla}. O mês M entra até o dia 20 do mês M+1."
    )

col1, col2, col3 = st.columns(3)
col1.metric("Ativos", int((v.situacao == "ativo").sum()))
col2.metric("Em silêncio", int((v.situacao == "em silêncio").sum()))
col3.metric("Sem ato no período coberto", int((v.situacao == "sem ato no período coberto").sum()))

st.warning("Sem ato no DOU não prova que o conselho parou: muito conselho funciona sem publicar no DOU. O limite de meses para 'em silêncio' é provisório e aguarda a definição da pesquisadora.")

st.subheader("A situação de cada conselho")
# shortcut: limite de 3 meses (meses_ativo do mart_vitalidade, provisório), atualizar quando a pesquisadora definir o limite
st.caption("Ativo: publicou até 3 meses atrás. Em silêncio: publicou há mais de 3 meses, ou nunca publicou com mais de 3 meses de cobertura. Sem ato no período coberto: nunca publicou, com 3 meses ou menos de cobertura.")
# O segundo sinal (plano 2026-11-09): atos de outros órgãos que citam o conselho no período, como uma homologação
# ou a renovação da composição. Ele não muda a situação, que segue a regra da mart.
st.caption("Citado por outros órgãos: atos publicados por outro órgão, no mesmo período, que têm o conselho como assunto. Um conselho sem ato próprio, mas citado, deu sinal de vida fora do DOU dele.")
tabela = v[["nome", "sigla", "situacao", "ultimo_mes_com_ato", "meses_sem_publicar", "atos_no_periodo", "mencoes_no_periodo", "eh_participativo"]].copy()
tabela["ultimo_mes_com_ato"] = tabela["ultimo_mes_com_ato"].map(mes)
tabela["eh_participativo"] = tabela["eh_participativo"].map(participacao)
st.dataframe(tabela.rename(columns={"nome": "Conselho", "sigla": "Sigla", "situacao": "Situação", "ultimo_mes_com_ato": "Último mês com ato", "meses_sem_publicar": "Meses sem publicar", "atos_no_periodo": "Atos no período", "mencoes_no_periodo": "Citado por outros órgãos", "eh_participativo": "Participação social (pesquisadora)"}), hide_index=True)

st.subheader("Atos de conselho por mês")
mensal["mes"] = mensal["mes"].map(mes)
st.bar_chart(mensal, x="mes", y="atos", sort=False)

st.subheader("O que cada conselho decide")
st.caption("Atos por tipologia da pesquisadora. Origem PLANILHA: atos da planilha; DOU: atos do Diário Oficial. SEM: ainda não classificado.")
st.dataframe(tipologia.rename(columns={"nome": "Conselho", "origem": "Origem", "tipologia_sigla": "Tipologia", "atos": "Atos"}), hide_index=True)
