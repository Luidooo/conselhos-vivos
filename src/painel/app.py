import os
import altair as alt
import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Conselhos Vivos", layout="wide")

DOCS = "https://luidooo.github.io/conselhos-vivos/"
GOLD = os.environ.get("PAINEL_GOLD", "/data/gold/conselhos.duckdb")

# O modo que o Streamlit escolheu (o do sistema, ou o que a pessoa trocou no menu). Sem navegador, como no AppTest,
# não há tema: vale o claro.
try:
    ESCURO = st.context.theme.type == "dark"
except AttributeError:
    ESCURO = False

# Os tokens de site/.vitepress/theme/custom.css, nos dois modos: a mesma fonte, o mesmo azul, os mesmos cinzas, o
# cartão de 18 px com sombra suave no claro e com contorno de 1 px no escuro.
T = {
    "fundo": "#000000" if ESCURO else "#ffffff",
    "cartao": "#1c1c1e" if ESCURO else "#f5f5f7",
    "texto": "#f5f5f7" if ESCURO else "#1d1d1f",
    "texto2": "#a1a1a6" if ESCURO else "#6e6e73",
    "divisor": "#2c2c2e" if ESCURO else "#e5e5ea",
    "azul": "#2997ff" if ESCURO else "#0071e3",
    "azul_suave": "rgba(41, 151, 255, 0.14)" if ESCURO else "rgba(0, 113, 227, 0.1)",
    "sombra": "0 0 0 1px #2c2c2e" if ESCURO else "0 1px 2px rgba(0, 0, 0, 0.04), 0 10px 30px rgba(0, 0, 0, 0.06)",
    "aviso": "rgba(250, 178, 25, 0.14)" if ESCURO else "rgba(250, 178, 25, 0.12)",
}

st.markdown(f"""<style>
:root {{
  --cv-fundo: {T['fundo']}; --cv-cartao: {T['cartao']}; --cv-texto: {T['texto']}; --cv-texto-2: {T['texto2']};
  --cv-divisor: {T['divisor']}; --cv-azul: {T['azul']}; --cv-azul-suave: {T['azul_suave']};
  --cv-sombra: {T['sombra']}; --cv-raio: 18px;
}}
.stApp {{ -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}
.block-container {{ max-width: 1152px; padding-top: 3.5rem; padding-bottom: 6rem; }}
header[data-testid="stHeader"] {{
  background: color-mix(in srgb, var(--cv-fundo) 72%, transparent);
  backdrop-filter: saturate(180%) blur(20px); -webkit-backdrop-filter: saturate(180%) blur(20px);
}}

/* o hero da página inicial do site: o rótulo em caixa alta, a pergunta grande e o texto de apoio em cinza */
.cv-rotulo {{ font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--cv-texto-2); }}
.cv-rotulo.azul {{ color: var(--cv-azul); }}
h1 {{ font-size: clamp(34px, 4.6vw, 54px) !important; letter-spacing: -0.035em; line-height: 1.05 !important; max-width: 900px; }}
h2, h3 {{ letter-spacing: -0.022em; }}
h3 {{ margin-top: 1.5rem; }}
.cv-lead {{ font-size: 19px; line-height: 1.55; color: var(--cv-texto-2); max-width: 720px; margin: 4px 0 0; }}

/* os botões do site: pílulas, o principal cheio de azul e os outros só com o contorno */
.cv-acoes {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 26px 0 8px; }}
.cv-botao {{
  display: inline-flex; align-items: center; height: 40px; padding: 0 22px; border-radius: 980px;
  font-size: 15px; font-weight: 500; text-decoration: none !important; border: 1px solid var(--cv-azul);
  color: var(--cv-azul) !important; transition: background-color .2s;
}}
.cv-botao:hover {{ background: var(--cv-azul-suave); }}
.cv-botao.cheio {{ background: #0071e3; border-color: transparent; color: #ffffff !important; }}
.cv-botao.cheio:hover {{ background: #0077ed; }}

/* a cobertura e o SLA em chips, uma linha só */
.cv-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0 6px; }}
.cv-chip {{
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 980px;
  background: var(--cv-cartao); color: var(--cv-texto-2); font-size: 13.5px; line-height: 1.3;
}}
.cv-chip strong {{ color: var(--cv-texto); font-weight: 600; }}
.cv-ponto {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex: none; }}

/* as métricas como os cartões da página inicial: número grande e justo, rótulo em caixa alta */
[data-testid="stMetric"] {{
  background: var(--cv-cartao); border-radius: var(--cv-raio); padding: 20px 24px; box-shadow: var(--cv-sombra);
  transition: transform .25s ease;
}}
[data-testid="stMetric"]:hover {{ transform: translateY(-3px); }}
[data-testid="stMetricLabel"] p {{
  font-size: 12px !important; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--cv-texto-2);
}}
[data-testid="stMetricLabel"] .stMarkdownEllipsis, [data-testid="stMetricLabel"] p {{
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}}
[data-testid="stMetricValue"] {{ letter-spacing: -0.03em; line-height: 1.1; }}

/* o aviso como os blocos do site: raio de 14 px, sem borda */
[data-testid="stAlert"] > div {{ border-radius: 14px; border: none; }}

/* as abas como um controle segmentado, em pílulas (Streamlit 1.66: role="tab", sem baseweb) */
.stTabs [role="tablist"] {{
  gap: 4px; padding: 4px; border-radius: 980px; background: var(--cv-cartao); width: fit-content; max-width: 100%;
  margin-top: 8px; border: none; box-shadow: none; overflow-x: auto;
}}
.stTabs [role="tablist"]::before, .stTabs [role="tablist"]::after,
.stTabs [role="tab"]::before, .stTabs [role="tab"]::after,
.stTabs .react-aria-SelectionIndicator {{ display: none !important; }}
.stTabs [role="tab"] {{
  height: 36px; padding: 0 18px; border-radius: 980px; border: none !important; box-shadow: none;
  color: var(--cv-texto-2); white-space: nowrap; transition: background-color .2s, color .2s;
}}
.stTabs [role="tab"] p {{ font-size: 14.5px; font-weight: 500; }}
.stTabs [role="tab"]:hover {{ color: var(--cv-texto); }}
.stTabs [role="tab"][aria-selected="true"] {{ background: var(--cv-fundo); color: var(--cv-texto); box-shadow: var(--cv-sombra); }}

[data-testid="stDataFrame"], [data-testid="stVegaLiteChart"] {{ border-radius: 14px; overflow: hidden; }}
[data-testid="stVegaLiteChart"] {{ background: var(--cv-cartao); border-radius: var(--cv-raio); }}
[data-testid="stExpander"] details {{ border-radius: var(--cv-raio); border-color: var(--cv-divisor); }}

/* o cartão de um conselho, na aba de detalhe */
.cv-cartao {{
  background: var(--cv-cartao); border-radius: var(--cv-raio); padding: 20px 24px; margin-bottom: 16px;
  box-shadow: var(--cv-sombra);
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px 24px;
}}
@media (max-width: 640px) {{ .cv-cartao {{ grid-template-columns: repeat(2, 1fr); }} }}
.cv-cartao .valor {{ color: var(--cv-texto); font-size: 19px; font-weight: 600; letter-spacing: -0.015em; margin-top: 4px; }}
.cv-marca {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
.cv-legenda {{ font-size: 13px; color: var(--cv-texto-2); }}

.cv-rodape {{
  margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--cv-divisor);
  font-size: 13px; color: var(--cv-texto-2); display: flex; flex-wrap: wrap; gap: 6px 18px;
}}
.cv-rodape a {{ color: var(--cv-texto-2) !important; text-decoration: none; }}
.cv-rodape a:hover {{ color: var(--cv-azul) !important; }}
</style>""", unsafe_allow_html=True)

st.markdown('<div class="cv-rotulo azul">Conselhos Vivos · painel da vitalidade</div>', unsafe_allow_html=True)
st.title("Quais conselhos nacionais de participação social ainda estão funcionando?")
st.markdown(f"""<p class="cv-lead">Os conselhos nacionais não são extintos quando param de funcionar: eles simplesmente
deixam de publicar. Este painel lê o Diário Oficial da União e mostra quais conselhos seguem publicando.</p>
<div class="cv-acoes">
  <a class="cv-botao cheio" href="{DOCS}" target="_blank">Documentação</a>
  <a class="cv-botao" href="{DOCS}entrega-e3" target="_blank">Entrega E3</a>
  <a class="cv-botao" href="{DOCS}linhagem" target="_blank">De onde vem cada número</a>
</div>""", unsafe_allow_html=True)

# A situação: ativo no azul do site, em silêncio no vermelho (o par azul e vermelho da paleta, lido como opostos) e
# cinza neutro para "ainda não dá para dizer". O par passou no validador do dataviz (daltonismo: ΔE 10,3 no claro, 7,0
# no escuro); a cor nunca vem sozinha, o rótulo está sempre ao lado, o que cobre a faixa de aviso do escuro.
SITUACOES = ["ativo", "em silêncio", "sem ato no período coberto"]
CORES_SITUACAO = ["#2997ff", "#e66767", "#8e8e93"] if ESCURO else ["#0071e3", "#e34948", "#8e8e93"]
# o texto dentro de cada fatia da barra: no claro, branco no azul e no vermelho (4,7 e 4,0:1); no escuro, as cores são
# mais claras e o branco cairia para menos de 3:1, então o texto é escuro em todas
TEXTO_SITUACAO = ["#1d1d1f"] * 3 if ESCURO else ["#ffffff", "#ffffff", "#1d1d1f"]
# o SLA é status, não situação: verde em dia, âmbar atrasado
SLA_OK, SLA_ATRASO = "#0ca30c", "#fab219"
# As tipologias são identidades: a paleta categórica, em ordem fixa, com os passos de cada modo. O 99 e o SEM ficam em
# cinza, porque não são categoria da pesquisadora.
TIPOLOGIAS = ["DEF", "FISC", "GEST", "AUTO", "IP", "99", "SEM"]
CORES_TIPOLOGIA = (["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#5a5a57", "#383835"] if ESCURO
                   else ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#c3c2b7", "#e5e5ea"])
# o mapa de calor: um só tom, do zero (quase o fundo do cartão) ao azul mais forte
RAMPA = ["#2c2c2e", "#9ec5f4"] if ESCURO else ["#e8e8ed", "#104281"]

# Os gráficos no tipo e nos cinzas do site: a fonte do sistema, grade e eixos discretos, sem moldura.
FONTE = '-apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'

def grafico(chart):
    # A configuração vai em cada gráfico, não num tema global do Altair: o processo é um só para todas as sessões, e
    # cada uma pode estar num modo. theme=None: sem o tema do Streamlit por cima, que trocaria a fonte e os eixos.
    chart = (chart.properties(padding={"left": 18, "right": 18, "top": 16, "bottom": 12},
                              autosize=alt.AutoSizeParams(type="fit-x", contains="padding"))
             .configure(background="transparent", font=FONTE)
             .configure_view(stroke=None)
             .configure_axis(labelColor=T["texto2"], titleColor=T["texto2"], labelFontSize=12, titleFontSize=12,
                             titleFontWeight=500, gridColor=T["divisor"], domain=False, tickColor=T["divisor"])
             .configure_legend(labelColor=T["texto"], titleColor=T["texto2"], labelFontSize=12, titleFontSize=12,
                               titleFontWeight=600))
    st.altair_chart(chart, width="stretch", theme=None)
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
    barra = base.mark_bar(size=40, cornerRadius=4, stroke=T["cartao"], strokeWidth=2).encode(
        color=alt.Color("situacao:N", scale=alt.Scale(domain=SITUACOES, range=CORES_SITUACAO),
                        legend=alt.Legend(title=None, orient="bottom", direction="horizontal", labelFontSize=13,
                                          symbolType="square", symbolSize=160)),
    )
    # o rótulo diz a situação e o número: a cor nunca fala sozinha
    rotulo = base.transform_filter("datum.conselhos > 0").transform_calculate(
        texto="datum.situacao + ': ' + datum.conselhos + ' (' + format(datum.percentual, '.0%') + ')'"
    ).mark_text(fontWeight=600, fontSize=14).encode(
        x=alt.X("conselhos:Q", stack="normalize", bandPosition=0.5),
        text="texto:N",
        color=alt.Color("situacao:N", scale=alt.Scale(domain=SITUACOES, range=TEXTO_SITUACAO), legend=None),
    )
    # escalas de cor independentes: a da barra (situação) e a do texto (contraste sobre cada fatia)
    return (barra + rotulo).resolve_scale(color="independent").properties(height=44)

def heatmap(serie, v):
    nomes = v[["orgao_id", "nome", "situacao"]]
    dados = serie.merge(nomes, on="orgao_id")
    dados["mes_txt"] = dados["mes"].map(mes)
    ordem_meses = [mes(m) for m in sorted(serie["mes"].unique())]
    return alt.Chart(dados).mark_rect(cornerRadius=3, stroke=T["cartao"], strokeWidth=2).encode(
        x=alt.X("mes_txt:O", title=None, sort=ordem_meses, axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("nome:N", title=None, sort=list(v["nome"]), axis=alt.Axis(labelLimit=360, labelOverlap=False, labelFontSize=12)),
        color=alt.Color("atos:Q", title="Atos no mês",
                        # um só tom, do claro ao escuro (sequencial); raiz quadrada para um conselho de 30 atos não apagar os de 1 ou 2
                        scale=alt.Scale(type="sqrt", domainMin=0, range=RAMPA, interpolate="lab")),
        tooltip=[alt.Tooltip("nome:N", title="Conselho"), alt.Tooltip("mes_txt:N", title="Mês"),
                 alt.Tooltip("atos:Q", title="Atos"), alt.Tooltip("situacao:N", title="Situação")],
    ).properties(height=max(120, 24 * len(v)))

def grafico_mensal(serie):
    total = serie.groupby("mes", as_index=False)["atos"].sum()
    total["mes_txt"] = total["mes"].map(mes)
    return alt.Chart(total).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=T["azul"]).encode(
        x=alt.X("mes_txt:O", title=None, sort=list(total["mes_txt"]), axis=alt.Axis(labelAngle=0)),
        y=alt.Y("atos:Q", title="Atos de conselho", axis=alt.Axis(tickMinStep=1, format="d")),
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("atos:Q", title="Atos")],
    ).properties(height=180)

def escala_tipologia(siglas):
    presentes = [t for t in TIPOLOGIAS if t in set(siglas)]
    return alt.Scale(domain=presentes, range=[CORES_TIPOLOGIA[TIPOLOGIAS.index(t)] for t in presentes])

def grafico_tipologia(tipologia):
    dados = tipologia[tipologia.origem == "PLANILHA"].copy()
    dados["significado"] = dados.tipologia_sigla.map(NOME_TIPOLOGIA)
    return alt.Chart(dados).mark_bar(stroke=T["cartao"], strokeWidth=2).encode(
        x=alt.X("atos:Q", stack="normalize", title="Parte dos atos da planilha", axis=alt.Axis(format="%", tickCount=5)),
        y=alt.Y("nome:N", title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("tipologia_sigla:N", title="Tipologia", scale=escala_tipologia(dados.tipologia_sigla)),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("nome:N", title="Conselho"), alt.Tooltip("tipologia_sigla:N", title="Tipologia"),
                 alt.Tooltip("significado:N", title="O que é"), alt.Tooltip("atos:Q", title="Atos")],
    ).transform_calculate(ordem=f"indexof({TIPOLOGIAS}, datum.tipologia_sigla)").properties(height=max(80, 40 * dados.nome.nunique()))

def detalhe_conselho(linha, serie, por_ano, mencoes):
    cor = CORES_SITUACAO[SITUACOES.index(linha.situacao)] if linha.situacao in SITUACOES else "#8e8e93"
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
        f'<div><div class="cv-rotulo">{r}</div><div class="valor">{x}</div></div>' for r, x in campos) + "</div>",
        unsafe_allow_html=True)

    esq, dir_ = st.columns(2)
    with esq:
        st.markdown("**Atos próprios no DOU, por mês**")
        propria = serie[serie.orgao_id == linha.orgao_id]
        if propria.empty:
            st.caption("O DOU ainda não foi carregado.")
        else:
            grafico(grafico_mensal(propria))
    with dir_:
        st.markdown("**Tipologias da planilha, por ano (2003–2020)**")
        anos = por_ano[por_ano.orgao_id == linha.orgao_id].copy()
        if anos.empty:
            st.info("Este conselho não está na planilha: sem atos classificados pela pesquisadora.")
        else:
            anos["significado"] = anos.tipologia_sigla.map(NOME_TIPOLOGIA)
            grafico(alt.Chart(anos).mark_bar(stroke=T["cartao"], strokeWidth=1).encode(
                x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("atos:Q", title="Atos"),
                color=alt.Color("tipologia_sigla:N", title="Tipologia", scale=escala_tipologia(anos.tipologia_sigla)),
                order=alt.Order("ordem:Q"),
                tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("tipologia_sigla:N", title="Tipologia"),
                         alt.Tooltip("significado:N", title="O que é"), alt.Tooltip("atos:Q", title="Atos")],
            ).transform_calculate(ordem=f"indexof({TIPOLOGIAS}, datum.tipologia_sigla)").properties(height=220))

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
    sla = "dentro do SLA" if f["dentro_do_sla"] else f"atraso {f['atraso_meses']} mês(es) fora do SLA"
    cor_sla = SLA_OK if f["dentro_do_sla"] else SLA_ATRASO
    st.markdown(f"""<div class="cv-chips">
  <span class="cv-chip"><strong>DOU coberto de {mes(periodo['primeiro'])} a {mes(periodo['ultimo'])}.</strong></span>
  <span class="cv-chip">A situação vale para o último mês coberto ({mes(v['mes_referencia'].iloc[0])}), não para hoje.</span>
  <span class="cv-chip" title="O mês M entra até o dia 20 do mês M+1."><span class="cv-ponto" style="background:{cor_sla}"></span>
    SLA: último mês coberto {mes(f['ultimo_mes_coberto'])}, mês esperado {mes(f['mes_esperado'])}, {sla}.</span>
</div>""", unsafe_allow_html=True)

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

grafico(grafico_composicao(v))

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
    so_citados = filtro3.toggle("Só os citados", help="Só os conselhos citados por outros órgãos no período.")

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
        grafico(grafico_mensal(serie))
        st.markdown("**Conselho a conselho, mês a mês.** Cada célula é um mês: quanto mais forte o azul, mais atos. A célula cinza é o mês sem ato.")
        grafico(heatmap(serie, visiveis if not visiveis.empty else v))

with aba_conselho:
    st.subheader("Um conselho em detalhe")
    rotulos = {f"{r.sigla} · {r.nome}" if pd.notna(r.sigla) and r.sigla else r.nome: r.orgao_id for r in v.itertuples()}
    escolhido = st.selectbox("Conselho", list(rotulos))
    detalhe_conselho(v[v.orgao_id == rotulos[escolhido]].iloc[0], serie, por_ano, mencoes)

with aba_decidem:
    st.subheader("O que cada conselho decide")
    st.caption("Atos por tipologia da pesquisadora. Origem PLANILHA: atos da planilha; DOU: atos do Diário Oficial. SEM: ainda não classificado. 99: ato da planilha sem tipologia atribuída.")
    if (tipologia.origem == "PLANILHA").any():
        grafico(grafico_tipologia(tipologia))
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

st.markdown(f"""<div class="cv-rodape">
  <span>Conselhos Vivos</span>
  <a href="{DOCS}" target="_blank">Documentação</a>
  <a href="{DOCS}docs/adr/" target="_blank">Decisões (ADRs)</a>
  <a href="{DOCS}linhagem" target="_blank">Linhagem dos dados</a>
  <a href="https://github.com/Luidooo/conselhos-vivos" target="_blank">Código no GitHub</a>
</div>""", unsafe_allow_html=True)
