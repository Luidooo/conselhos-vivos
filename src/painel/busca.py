"""Busca do RAG (E4, ADR 0012): os atos que respondem a uma pergunta, pela busca textual do Postgres em português.
Fica só a versão mais recente de cada matéria. As palavras da pergunta entram com OU, e a nota (ts_rank) ordena:
com E, uma pergunta em linguagem natural quase nunca acharia nada."""

from dataclasses import dataclass
from datetime import date

DOC = "to_tsvector('portuguese', coalesce(a.ementa, '') || ' ' || coalesce(a.conteudo, ''))"

# shortcut: a pergunta vai para a busca como foi escrita; o Claude reescrever em termos de busca fica para quando a
# avaliação (Tarefa 15) mostrar perguntas que não acham o ato esperado.
BUSCA = f"""
select a.id, a.id_dou, a.data_publicacao, coalesce(n.nome, '(sem nome vigente)'), a.ementa,
       ts_headline('portuguese',
                   regexp_replace(coalesce(a.ementa, '') || ' ' || coalesce(a.conteudo, ''), '<[^>]+>', ' ', 'g'),
                   q.q, 'MaxWords=60, MinWords=25, MaxFragments=2, StartSel=**, StopSel=**')
from ato a
cross join (select nullif(replace(plainto_tsquery('portuguese', %(pergunta)s)::text, ' & ', ' | '), '')::tsquery as q) q
left join orgao_nome n on n.orgao_id = a.orgao_id and n.data_fim is null
where q.q is not null and {DOC} @@ q.q
  and (%(orgao)s::int is null or a.orgao_id = %(orgao)s::int)
  and (%(de)s::date is null or a.data_publicacao >= %(de)s::date)
  and (%(ate)s::date is null or a.data_publicacao <= %(ate)s::date)
  and not exists (select 1 from ato b where b.origem = a.origem and b.id_dou = a.id_dou and b.versao > a.versao)
order by ts_rank({DOC}, q.q) desc, a.data_publicacao desc
limit %(limite)s
"""


@dataclass(frozen=True)
class Ato:
    id: int
    id_dou: str | None
    data: date
    conselho: str
    ementa: str | None
    trecho: str


def buscar(conn, pergunta, orgao=None, de=None, ate=None, limite=8):
    linhas = conn.execute(BUSCA, {"pergunta": pergunta, "orgao": orgao, "de": de, "ate": ate, "limite": limite}).fetchall()
    return [Ato(*l) for l in linhas]
