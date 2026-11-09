-- Granularidade: uma linha por conselho por mês do período coberto pela ingestão do DOU.
-- Mês sem ato vira linha com atos = 0: é o silêncio que a pergunta da E1 mede.
with limites as (
    select min(mes) as inicio, max(mes) as fim
    from {{ ref('fct_ato') }}
    where origem = 'DOU'
),
meses as (
    select unnest(generate_series(inicio, fim, interval 1 month))::date as mes
    from limites
    where inicio is not null
),
conselhos as (select distinct orgao_id from {{ ref('dim_conselho') }})
select c.orgao_id, m.mes, count(a.ato_id) as atos
from conselhos c
cross join meses m
left join {{ ref('fct_ato') }} a
  on a.orgao_id = c.orgao_id and a.mes = m.mes and a.origem = 'DOU'
group by c.orgao_id, m.mes
