-- O fato tem uma linha por matéria do escopo (ADR 0010): nem perde ato no join com a dimensão, nem duplica.
-- E os 215 atos da planilha nunca podem sumir.
with esperado as (
    select count(*) as n from {{ ref('stg_atos') }}
    where orgao_id in (select orgao_id from {{ ref('dim_conselho') }})
),
real as (
    select count(*) as n, count(*) filter (where origem = 'PLANILHA') as planilha from {{ ref('fct_ato') }}
)
select esperado.n as esperado, real.n as real, real.planilha
from esperado, real
where esperado.n <> real.n or real.planilha < 215
