import os
import altair as alt
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
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { padding: 8px 16px; border-radius: 10px 10px 0 0; font-weight: 500; }
.cv-cartao {
  background: #f5f5f7; border-radius: 14px; padding: 18px 22px; margin-bottom: 12px;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px 24px;
}
.cv-cartao .rotulo { color: #6e6e73; font-size: 0.85rem; }
.cv-cartao .valor { color: #1d1d1f; font-size: 1.15rem; font-weight: 600; }
.cv-marca { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
</style>""", unsafe_allow_html=True)

st.title("Quais conselhos nacionais de participação social ainda estão funcionando?")

GOLD = os.environ.get("PAINEL_GOLD", "/data/gold/conselhos.duckdb")

# A situação é um estado, então usa a paleta de status (dataviz, references/palette.md): verde para ativo, âmbar para
# em silêncio e cinza neutro para "ainda não dá para dizer". A cor nunca vem sozinha: o rótulo está sempre ao lado.
SITUACOES = ["ativo", "em silêncio", "sem ato no período coberto"]
CORES_SITUACAO = ["#0ca30c", "#fab219", "#a1a1a6"]
# As tipologias são identidades: a paleta categórica, em ordem fixa. O 99 e o SEM ficam em cinza, porque não são
# categoria da pesquisadora.
TIPOLOGIAS = ["DEF", "FISC", "GEST", "AUTO", "IP", "99", "SEM"]
CORES_TIPOLOGIA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#c3c2b7", "#e5e5ea"]
NOME_TIPOLOGIA = {
    "DEF": "define a política", "FISC": "fiscaliza", "GEST": "gestão administrativa", "AUTO": "autorregulação",
    "IP": "gere instâncias participativas", "99": "sem tipologia na planilha", "SEM": "DOU ainda não classificado",
}

def mes(d):
    return f"{d:%m/%Y}" if pd.notna(d) else ""

def participacao(x):
    # nulo é não avaliado, não falso: só o falso vira "não"
    return "não avaliado" if pd.isna(x) else ("sim" if x else "não")

def carregar(gold):
    # uma conexão por carga, fechada antes de desenhar: não segura a trava que o make gold precisa
    d = {}
    with duckdb.connect(gold, read_only=True) as con:
        d["periodo"] = con.sql("select min(mes) as primeiro, max(mes) as ultimo from fct_conselho_mes").df().iloc[0]
        # eh_participativo vem da dim_conselho: a marca da pesquisadora, sem filtrar nada aqui (ADR 0010, ponto 4)
        d["v"] = con.sql("select m.*, d.eh_participativo from mart_vitalidade m left join (select distinct orgao_id, eh_participativo from dim_conselho) d on d.orgao_id = m.orgao_id order by m.situacao, m.meses_sem_publicar desc nulls last, m.nome").df()
        d["serie"] = con.sql("select orgao_id, mes, atos from fct_conselho_mes order by mes").df()
        # o freshness é uma linha só, com nulos quando o DOU está vazio
        d["f"] = con.sql("select * from freshness_vitalidade").df().iloc[0] if pd.notna(d["periodo"]["ultimo"]) else None
        d["tipologia"] = con.sql("select v.nome, f.origem, f.tipologia_sigla, count(*) as atos from mart_vitalidade v join fct_ato f on f.orgao_id = v.orgao_id group by all order by v.nome, atos desc").df()
        d["por_ano"] = con.sql("select orgao_id, cast(extract(year from data_publicacao) as integer) as ano, tipologia_sigla, count(*) as atos from fct_ato where origem = 'PLANILHA' group by all order by ano").df()
        d["mencoes"] = con.sql("select orgao_id, data_publicacao, publicador, titulo from fct_mencao order by data_publicacao desc").df()
    return d

def grafico_composicao(v):
    contagem = v.situacao.value_counts().reindex(SITUACOES, fill_value=0).reset_index()
    contagem.columns = ["situacao", "conselhos"]
    contagem["ordem"] = range(len(contagem))
    contagem["percentual"] = contagem.conselhos / max(1, contagem.conselhos.sum())
    base = alt.Chart(contagem).encode(
        x=alt.X("conselhos:Q", stack="normalize", axis=None),
        order="ordem:Q",
        tooltip=[alt.Tooltip("situacao:N", title="Situação"), alt.Tooltip("conselhos:Q", title="Conselhos"),
                 alt.Tooltip("percentual:Q", title="Do total", format=".0%")],
    )
    barra = base.mark_bar(size=40, cornerRadius=4, stroke="#ffffff", strokeWidth=2).encode(
        color=alt.Color("situacao:N", scale=alt.Scale(domain=SITUACOES, range=CORES_SITUACAO),
                        legend=alt.Legend(title=None, orient="bottom", direction="horizontal", labelFontSize=13,
                                          symbolType="square", symbolSize=160)),
    )
    # o rótulo diz a situação e o número: a cor nunca fala sozinha
    rotulo = base.transform_filter("datum.conselhos > 0").transform_calculate(
        texto="datum.situacao + ': ' + datum.conselhos + ' (' + format(datum.percentual, '.0%') + ')'"
    ).mark_text(color="#1d1d1f", fontWeight=600, fontSize=14).encode(
        x=alt.X("conselhos:Q", stack="normalize", bandPosition=0.5),
        text="texto:N",
    )
    return (barra + rotulo).properties(height=44)

def heatmap(serie, v):
    nomes = v[["orgao_id", "nome", "situacao"]]
    dados = serie.merge(nomes, on="orgao_id")
    dados["mes_txt"] = dados["mes"].map(mes)
    ordem_meses = [mes(m) for m in sorted(serie["mes"].unique())]
    return alt.Chart(dados).mark_rect(cornerRadius=3, stroke="#ffffff", strokeWidth=2).encode(
        x=alt.X("mes_txt:O", title=None, sort=ordem_meses, axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("nome:N", title=None, sort=list(v["nome"]), axis=alt.Axis(labelLimit=360, labelOverlap=False, labelFontSize=12)),
        color=alt.Color("atos:Q", title="Atos no mês",
                        # um só tom, do claro ao escuro (sequencial); raiz quadrada para um conselho de 30 atos não apagar os de 1 ou 2
                        scale=alt.Scale(type="sqrt", domainMin=0, range=["#f0efec", "#104281"], interpolate="lab")),
        tooltip=[alt.Tooltip("nome:N", title="Conselho"), alt.Tooltip("mes_txt:N", title="Mês"),
                 alt.Tooltip("atos:Q", title="Atos"), alt.Tooltip("situacao:N", title="Situação")],
    ).properties(height=max(120, 24 * len(v)))

def grafico_mensal(serie):
    total = serie.groupby("mes", as_index=False)["atos"].sum()
    total["mes_txt"] = total["mes"].map(mes)
    return alt.Chart(total).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#2a78d6").encode(
        x=alt.X("mes_txt:O", title=None, sort=list(total["mes_txt"]), axis=alt.Axis(labelAngle=0)),
        y=alt.Y("atos:Q", title="Atos de conselho"),
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("atos:Q", title="Atos")],
    ).properties(height=180)

def escala_tipologia(siglas):
    presentes = [t for t in TIPOLOGIAS if t in set(siglas)]
    return alt.Scale(domain=presentes, range=[CORES_TIPOLOGIA[TIPOLOGIAS.index(t)] for t in presentes])

def grafico_tipologia(tipologia):
    dados = tipologia[tipologia.origem == "PLANILHA"].copy()
    dados["significado"] = dados.tipologia_sigla.map(NOME_TIPOLOGIA)
    return alt.Chart(dados).mark_bar(stroke="#ffffff", strokeWidth=2).encode(
        x=alt.X("atos:Q", stack="normalize", title="Parte dos atos da planilha", axis=alt.Axis(format="%", tickCount=5)),
        y=alt.Y("nome:N", title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("tipologia_sigla:N", title="Tipologia", scale=escala_tipologia(dados.tipologia_sigla)),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("nome:N", title="Conselho"), alt.Tooltip("tipologia_sigla:N", title="Tipologia"),
                 alt.Tooltip("significado:N", title="O que é"), alt.Tooltip("atos:Q", title="Atos")],
    ).transform_calculate(ordem=f"indexof({TIPOLOGIAS}, datum.tipologia_sigla)").properties(height=max(80, 40 * dados.nome.nunique()))

def detalhe_conselho(linha, serie, por_ano, mencoes):
    cor = CORES_SITUACAO[SITUACOES.index(linha.situacao)] if linha.situacao in SITUACOES else "#a1a1a6"
    meses_sem = "" if pd.isna(linha.meses_sem_publicar) else int(linha.meses_sem_publicar)
    campos = [
        ("Situação", f'<span class="cv-marca" style="background:{cor}"></span>{linha.situacao}'),
        ("Último mês com ato", mes(linha.ultimo_mes_com_ato) or "nenhum no período"),
        ("Meses sem publicar", meses_sem if meses_sem != "" else "não se aplica"),
        ("Atos no período", int(linha.atos_no_periodo)),
        ("Citado por outros órgãos", int(linha.mencoes_no_periodo)),
        ("Participação social (pesquisadora)", participacao(linha.eh_participativo)),
    ]
    st.markdown('<div class="cv-cartao">' + "".join(
        f'<div><div class="rotulo">{r}</div><div class="valor">{x}</div></div>' for r, x in campos) + "</div>",
        unsafe_allow_html=True)

    esq, dir_ = st.columns(2)
    with esq:
        st.markdown("**Atos próprios no DOU, por mês**")
        propria = serie[serie.orgao_id == linha.orgao_id]
        if propria.empty:
            st.caption("O DOU ainda não foi carregado.")
        else:
            st.altair_chart(grafico_mensal(propria), width="stretch")
    with dir_:
        st.markdown("**Tipologias da planilha, por ano (2003–2020)**")
        anos = por_ano[por_ano.orgao_id == linha.orgao_id].copy()
        if anos.empty:
            st.info("Este conselho não está na planilha: sem atos classificados pela pesquisadora.")
        else:
            anos["significado"] = anos.tipologia_sigla.map(NOME_TIPOLOGIA)
            st.altair_chart(alt.Chart(anos).mark_bar(stroke="#ffffff", strokeWidth=1).encode(
                x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("atos:Q", title="Atos"),
                color=alt.Color("tipologia_sigla:N", title="Tipologia", scale=escala_tipologia(anos.tipologia_sigla)),
                order=alt.Order("ordem:Q"),
                tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("tipologia_sigla:N", title="Tipologia"),
                         alt.Tooltip("significado:N", title="O que é"), alt.Tooltip("atos:Q", title="Atos")],
            ).transform_calculate(ordem=f"indexof({TIPOLOGIAS}, datum.tipologia_sigla)").properties(height=220),
                width="stretch")

    st.markdown("**Citações por outros órgãos no período**")
    citacoes = mencoes[mencoes.orgao_id == linha.orgao_id]
    if citacoes.empty:
        st.caption("Nenhum ato de outro órgão tem este conselho como assunto no período coberto.")
    else:
        st.dataframe(citacoes[["data_publicacao", "publicador", "titulo"]], hide_index=True, width="stretch",
                     column_config={"data_publicacao": st.column_config.DateColumn("Publicado em", format="DD/MM/YYYY"),
                                    "publicador": "Publicado por", "titulo": "Título"})

if not os.path.exists(GOLD):
    st.error("Não há gold em data/gold/conselhos.duckdb: rode make gold.")
    st.stop()

erro = None
try:
    dados = carregar(GOLD)
except duckdb.CatalogException:
    erro = "A gold não tem as tabelas do painel: rode make gold."
except duckdb.IOException:
    erro = "A gold está ocupada ou sendo gerada pelo make gold: tente de novo em alguns segundos."

if erro:
    st.error(erro)
    st.stop()

periodo, v, serie, f = dados["periodo"], dados["v"], dados["serie"], dados["f"]
tipologia, por_ano, mencoes = dados["tipologia"], dados["por_ano"], dados["mencoes"]

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

total = len(v)
def fatia(n):
    return f"{n / total:.0%} dos {total} conselhos"

n_ativo = int((v.situacao == "ativo").sum())
n_silencio = int((v.situacao == "em silêncio").sum())
n_sem = int((v.situacao == "sem ato no período coberto").sum())
# o segundo sinal de vida: fora de ativo, mas com algum ato de outro órgão que tem o conselho como assunto
n_citados = int(((v.situacao != "ativo") & (v.mencoes_no_periodo > 0)).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ativos", n_ativo, help=fatia(n_ativo))
col2.metric("Em silêncio", n_silencio, help=fatia(n_silencio))
col3.metric("Sem ato no período coberto", n_sem, help=fatia(n_sem))
col4.metric("Sem ato próprio, mas citados", n_citados,
            help="Conselhos que não estão ativos, mas aparecem como assunto em atos de outros órgãos no período.")

st.altair_chart(grafico_composicao(v), width="stretch")

st.warning("Sem ato no DOU não prova que o conselho parou: muito conselho funciona sem publicar no DOU. O limite de meses para 'em silêncio' é provisório e aguarda a definição da pesquisadora.")

aba_resposta, aba_conselho, aba_decidem, aba_ler = st.tabs(["Resposta", "Conselho a conselho", "O que decidem", "Como ler"])

with aba_resposta:
    st.subheader("A situação de cada conselho")
    # shortcut: limite de 3 meses (meses_ativo do mart_vitalidade, provisório), atualizar quando a pesquisadora definir o limite
    st.caption("Ativo: publicou até 3 meses atrás. Em silêncio: publicou há mais de 3 meses, ou nunca publicou com mais de 3 meses de cobertura. Sem ato no período coberto: nunca publicou, com 3 meses ou menos de cobertura.")
    # O segundo sinal (plano 2026-11-09): atos de outros órgãos que citam o conselho no período, como uma homologação
    # ou a renovação da composição. Ele não muda a situação, que segue a regra da mart.
    st.caption("Citado por outros órgãos: atos publicados por outro órgão, no mesmo período, que têm o conselho como assunto. Um conselho sem ato próprio, mas citado, deu sinal de vida fora do DOU dele.")

    filtro1, filtro2, filtro3 = st.columns([2, 2, 1])
    escolhidas = filtro1.multiselect("Situação", SITUACOES, placeholder="Todas as situações")
    busca = filtro2.text_input("Buscar conselho", placeholder="Nome ou sigla")
    so_citados = filtro3.toggle("Só os citados por outros órgãos")

    visiveis = v
    if escolhidas:
        visiveis = visiveis[visiveis.situacao.isin(escolhidas)]
    if busca.strip():
        termo = busca.strip().lower()
        visiveis = visiveis[visiveis.nome.str.lower().str.contains(termo, regex=False)
                            | visiveis.sigla.fillna("").str.lower().str.contains(termo, regex=False)]
    if so_citados:
        visiveis = visiveis[visiveis.mencoes_no_periodo > 0]

    tabela = visiveis[["nome", "sigla", "situacao", "ultimo_mes_com_ato", "meses_sem_publicar", "atos_no_periodo", "mencoes_no_periodo", "eh_participativo"]].copy()
    tabela["ultimo_mes_com_ato"] = pd.to_datetime(tabela["ultimo_mes_com_ato"])
    tabela["eh_participativo"] = tabela["eh_participativo"].map(participacao)
    st.dataframe(
        tabela.rename(columns={"nome": "Conselho", "sigla": "Sigla", "situacao": "Situação", "ultimo_mes_com_ato": "Último mês com ato", "meses_sem_publicar": "Meses sem publicar", "atos_no_periodo": "Atos no período", "mencoes_no_periodo": "Citado por outros órgãos", "eh_participativo": "Participação social (pesquisadora)"}),
        hide_index=True, width="stretch",
        column_config={
            "Último mês com ato": st.column_config.DateColumn(format="MM/YYYY"),
            "Atos no período": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=max(1, int(v.atos_no_periodo.max()))),
            "Citado por outros órgãos": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=max(1, int(v.mencoes_no_periodo.max()))),
        },
    )
    st.caption(f"{len(visiveis)} de {total} conselhos.")

    st.subheader("Atos de conselho por mês")
    if serie.empty:
        st.caption("O DOU ainda não foi carregado.")
    else:
        st.altair_chart(grafico_mensal(serie), width="stretch")
        st.markdown("**Conselho a conselho, mês a mês.** Cada célula é um mês: quanto mais escura, mais atos. A célula clara é o mês sem ato.")
        st.altair_chart(heatmap(serie, visiveis if not visiveis.empty else v), width="stretch")

with aba_conselho:
    st.subheader("Um conselho em detalhe")
    rotulos = {f"{r.sigla} · {r.nome}" if pd.notna(r.sigla) and r.sigla else r.nome: r.orgao_id for r in v.itertuples()}
    escolhido = st.selectbox("Conselho", list(rotulos))
    detalhe_conselho(v[v.orgao_id == rotulos[escolhido]].iloc[0], serie, por_ano, mencoes)

with aba_decidem:
    st.subheader("O que cada conselho decide")
    st.caption("Atos por tipologia da pesquisadora. Origem PLANILHA: atos da planilha; DOU: atos do Diário Oficial. SEM: ainda não classificado. 99: ato da planilha sem tipologia atribuída.")
    if (tipologia.origem == "PLANILHA").any():
        st.altair_chart(grafico_tipologia(tipologia), width="stretch")
        st.caption(" · ".join(f"{s}: {NOME_TIPOLOGIA[s]}" for s in TIPOLOGIAS[:5]))
    st.dataframe(tipologia.rename(columns={"nome": "Conselho", "origem": "Origem", "tipologia_sigla": "Tipologia", "atos": "Atos"}), hide_index=True, width="stretch")

with aba_ler:
    # As regras de negócio por extenso, para quem lê o painel sem ter lido os ADRs. O 3 repete o meses_ativo da mart.
    # shortcut: os números e as regras estão escritos aqui; se a mart ou o ADR 0010 mudarem, este texto muda junto.
    with st.expander("Como ler este painel: as regras de negócio", expanded=True):
        st.markdown(f"""
**O que conta como conselho.** Todo órgão do governo federal que tem ou já teve um nome começando com
"Conselho", menos uma lista curta de exclusões de órgãos que não são colegiados de participação social, como
o Conselho Monetário Nacional e o Conselho Nacional de Justiça ([ADR 0010](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome.md)).
Hoje são **{len(v)} conselhos**. Comissões, comitês e câmaras ficam de fora, mesmo quando funcionam como conselho.
Por isso o número é menor que os 82 órgãos da identidade dos conselhos da E1: 62 deles têm "Conselho" no nome, e
3 desses são excluídos (Conselho da Justiça Federal, Conselho Monetário Nacional e Conselho Nacional de Justiça).

**De onde vêm os dados.** Dos atos publicados no Diário Oficial da União, Seção 1, pelos dados abertos da
Imprensa Nacional, e da planilha da pesquisadora, com 215 atos de 2003 a 2020, já classificados por tipologia.
A situação de cada conselho usa só o período coberto pelo DOU; a planilha entra no bloco das tipologias.

**A situação de cada conselho**, medida no último mês coberto, não hoje:
- **Ativo:** o último ato próprio foi publicado até 3 meses antes do último mês coberto.
- **Em silêncio:** o último ato foi há mais de 3 meses, ou o conselho não publicou nada num período coberto de
  mais de 3 meses.
- **Sem ato no período coberto:** o conselho não publicou nada, e o período coberto ainda tem 3 meses ou menos,
  curto demais para chamar de silêncio.

O limite de 3 meses é provisório: ele aguarda a definição da pesquisadora.

**Citado por outros órgãos.** Atos publicados por outro órgão, no mesmo período, que têm o conselho como
assunto: a homologação de um parecer, a renovação da composição, a aprovação do regimento. O nome do conselho é
procurado só no título, na ementa e no começo do texto, para não contar citações de passagem. Isso é um segundo
sinal de vida, mostrado ao lado: ele **não muda** a situação.

**Participação social (pesquisadora).** A marca que a pesquisadora deu a cada conselho: "sim", "não" ou
"não avaliado". Não avaliado não quer dizer "não": o painel não filtra por ela.

**Atualização e SLA.** Um mês entra no painel até o dia 20 do mês seguinte, porque a Imprensa Nacional publica
o mês cerca de duas semanas depois que ele acaba. A atualização tenta do dia 15 ao 28 de cada mês.

**Limites.** Um conselho pode funcionar sem publicar no DOU, e o painel não sabe distinguir um conselho extinto
de um calado. O ato publicado em nome de um ministério, sem citar o conselho no começo, não aparece aqui.
""")
