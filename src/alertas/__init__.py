"""ETL reverso (E4, ADR 0011): a situação de cada conselho, tratada na gold, volta ao Postgres como alerta, onde a
curadoria age (página Revisar do painel). A regra mora aqui; a situação vem pronta da mart_vitalidade."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Alerta:
    orgao_id: int
    tipo: str
    mes_referencia: date
    detalhe: str


def alertas(linhas: list[dict]) -> list[Alerta]:
    """Os alertas de cada linha da mart_vitalidade. Sem mês de referência (gold sem DOU), nenhum."""
    out = []
    for l in linhas:
        if l["mes_referencia"] is None:
            continue
        nome = l["sigla"] or l["nome"]
        if l["situacao"] == "em silêncio":
            quanto = (f"{l['meses_sem_publicar']} meses sem ato próprio no DOU" if l["meses_sem_publicar"] is not None
                      else "nenhum ato próprio no período coberto")
            out.append(Alerta(l["orgao_id"], "em_silencio", l["mes_referencia"],
                              f"{nome}: {quanto}. Confira se o conselho foi extinto, mudou de nome ou publica por outro órgão."))
        if l["situacao"] != "ativo" and (l["mencoes_no_periodo"] or 0) > 0:
            out.append(Alerta(l["orgao_id"], "citado_sem_ato_proprio", l["mes_referencia"],
                              f"{nome}: sem ato próprio recente, mas citado {l['mencoes_no_periodo']} vez(es) por outros órgãos. "
                              "Confira se os atos dele saem com outro nome (fila de órgãos em orgao_alias)."))
    return out


# Idempotente: o mesmo alerta não duplica (uq_alerta), e um alerta já tratado não é reescrito.
# xmax = 0 só na linha recém-inserida: separa novo de atualizado sem outra consulta.
UPSERT = """
insert into alerta (orgao_id, tipo, mes_referencia, detalhe) values (%s, %s, %s, %s)
on conflict (orgao_id, tipo, mes_referencia) do update set detalhe = excluded.detalhe
  where alerta.tratado_em is null and alerta.detalhe is distinct from excluded.detalhe
returning (xmax = 0) as novo
"""


def gravar(conn, lista: list[Alerta]) -> tuple[int, int, int]:
    """Grava os alertas na transação de `conn`, sem commit. Devolve (novos, atualizados, inalterados).
    shortcut: alerta que deixou de valer não é fechado sozinho; a curadoria fecha na página Revisar."""
    novos = atualizados = 0
    for a in lista:
        linha = conn.execute(UPSERT, (a.orgao_id, a.tipo, a.mes_referencia, a.detalhe)).fetchone()
        if linha is None:
            continue
        if linha[0]:
            novos += 1
        else:
            atualizados += 1
    return novos, atualizados, len(lista) - novos - atualizados
