"""Revisar (E4, ADR 0011): os alertas que o ETL reverso gravou no Postgres, para a curadoria tratar. A página entra
como app_curadoria: lê o alerta e o nome do revisor, nunca o e-mail, e só marca o alerta como tratado."""

import os

import psycopg
import streamlit as st

st.title("Alertas para revisar")

TIPOS = {"em_silencio": "em silêncio", "citado_sem_ato_proprio": "citado, sem ato próprio"}


def conecta():
    return psycopg.connect(host=os.environ.get("PGHOST", "db"), port=int(os.environ.get("PGPORT", 5432)),
                           dbname=os.environ.get("PGDATABASE"), user=os.environ.get("PAINEL_PGUSER"),
                           password=os.environ.get("PAINEL_PGPASSWORD"), connect_timeout=3)


try:
    with conecta() as conn:
        abertos = conn.execute("""
            select a.id, coalesce(n.nome, '(sem nome vigente)'), a.tipo, a.mes_referencia, a.detalhe
            from alerta a left join orgao_nome n on n.orgao_id = a.orgao_id and n.data_fim is null
            where a.tratado_em is null
            order by a.mes_referencia desc, 2, a.tipo""").fetchall()
        revisores = conn.execute("select id, nome from revisor where tipo = 'HUMANO' order by nome").fetchall()
except psycopg.OperationalError:
    st.error("Sem conexão com o banco da curadoria: suba o Postgres com make up.")
    st.stop()

st.caption("Cada alerta vem da situação do conselho na gold, gravada pelo ETL reverso a cada mês. Tratar é "
           "registrar o que foi conferido; o alerta sai da lista e fica no banco.")
if not abertos:
    st.success("Nenhum alerta aberto.")
    st.stop()
if not revisores:
    st.error("Nenhum revisor humano cadastrado: rode make carga.")
    st.stop()

quem = st.selectbox("Quem está revisando", revisores, format_func=lambda r: r[1])
for id_, conselho, tipo, mes_ref, detalhe in abertos:
    with st.container(border=True):
        st.markdown(f"**{conselho}** · {TIPOS[tipo]} · {mes_ref:%m/%Y}")
        st.write(detalhe)
        nota = st.text_input("O que foi conferido", key=f"nota{id_}")
        if st.button("Marcar como tratado", key=f"ok{id_}"):
            with conecta() as conn:
                conn.execute("update alerta set tratado_em = now(), tratado_por = %s, nota = %s "
                             "where id = %s and tratado_em is null", (quem[0], nota or None, id_))
            st.rerun()
