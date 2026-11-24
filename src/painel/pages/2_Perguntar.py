"""Perguntar (E4, ADR 0012): a pesquisadora pergunta em português; a busca acha os atos no Postgres e a API do Claude
responde citando cada um. A página entra como app_perguntas: lê o texto dos atos e o nome dos órgãos, nada mais."""

import os

import anthropic
import psycopg
import streamlit as st

from busca import buscar, link_dou
from perguntar import MODELO, CitacaoInvalida, Recusada, responder

st.title("Perguntar aos atos")
st.caption("A resposta usa só os atos achados no Diário Oficial e cita cada um pelo número. Se nenhum ato responde, ela diz que não achou.")
st.caption("Não escreva dado pessoal na pergunta: ela e os trechos achados vão para a API do Claude, fora do país.")


def conecta():
    return psycopg.connect(host=os.environ.get("PGHOST", "db"), port=int(os.environ.get("PGPORT", 5432)),
                           dbname=os.environ.get("PGDATABASE"), user=os.environ.get("PERGUNTAS_PGUSER"),
                           password=os.environ.get("PERGUNTAS_PGPASSWORD"), connect_timeout=3)


try:
    with conecta() as conn:
        conselhos = conn.execute("select orgao_id, nome from orgao_nome "
                                 "where data_fim is null and nome ilike 'conselho%' order by nome").fetchall()
except psycopg.OperationalError:
    st.error("Sem conexão com o banco da curadoria: suba o Postgres com make up.")
    st.stop()

pergunta = st.text_input("Pergunta", placeholder="O que o CONAMA decidiu sobre licenciamento?")
c1, c2, c3 = st.columns(3)
conselho = c1.selectbox("Conselho", [None] + conselhos, format_func=lambda c: "todos" if c is None else c[1])
de = c2.date_input("De", value=None)
ate = c3.date_input("Até", value=None)
if not st.button("Perguntar", disabled=not pergunta):
    st.stop()

with conecta() as conn:
    atos = buscar(conn, pergunta, orgao=conselho[0] if conselho else None, de=de, ate=ate)

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.info("Sem ANTHROPIC_API_KEY no .env: a busca funciona, a resposta não. Os atos achados estão abaixo.")
else:
    try:
        with st.spinner("Lendo os atos achados..."):
            r = responder(pergunta, atos, anthropic.Anthropic())
        st.markdown(r.texto)
        links = [f"[ato {i}]({link})" for i in r.citados if (link := link_dou(atos[i - 1]))]
        if links:
            st.markdown("**Abrir no Diário Oficial:** " + " · ".join(links))
        if atos and not r.citados:
            st.warning("A resposta não cita nenhum ato. Se ela afirma algo, confira nos atos abaixo.")
        if r.cortada:
            st.warning("A resposta bateu no limite de tamanho e pode ter parado no meio.")
        st.caption(f"{r.tokens} tokens · {MODELO}")
    except CitacaoInvalida as e:
        st.error(f"A resposta foi recusada: {e}. Tente de novo.")
    except Recusada:
        st.error("O modelo recusou responder a essa pergunta. Os atos achados estão abaixo.")
    # Do mais específico para o mais geral: cada falha pede uma ação diferente de quem está usando.
    except anthropic.AuthenticationError:
        st.error("A API do Claude não aceitou a chave: confira a ANTHROPIC_API_KEY no .env. Os atos achados estão abaixo.")
    except anthropic.RateLimitError:
        st.error("A API do Claude pediu para esperar: tente de novo em um minuto. Os atos achados estão abaixo.")
    except anthropic.APIConnectionError:
        st.error("Sem conexão com a API do Claude: confira a rede. Os atos achados estão abaixo.")
    except anthropic.APIStatusError as e:
        st.error(f"A API do Claude falhou ({e.status_code}): {e.message}. Os atos achados estão abaixo.")

if not atos:
    st.write("Nenhum ato achado para essa pergunta.")
for i, a in enumerate(atos, 1):
    with st.expander(f"[{i}] {a.conselho} · {a.data:%d/%m/%Y} · DOU {a.id_dou or 'planilha'}"):
        if a.ementa:
            st.write(a.ementa)
        st.markdown(a.trecho)
        if link := link_dou(a):
            st.link_button("Abrir no Diário Oficial", link)
        else:
            st.caption("Ato da planilha da pesquisadora: sem link do Diário Oficial.")
