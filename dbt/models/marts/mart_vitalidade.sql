-- Granularidade: uma linha por conselho, com o nome mais recente e a situação no último mês coberto.
-- É a resposta à pergunta da E1.
-- Sem ato algum: 'sem ato no período coberto' só enquanto a cobertura tem meses_ativo meses ou menos; com mais cobertura que isso, é 'em silêncio'. mes_referencia é o último mês coberto, não hoje.
with cobertura as (select min(mes) as primeiro, max(mes) as ultimo, date_diff('month', min(mes), max(mes)) + 1 as meses from {{ ref('fct_conselho_mes') }}),
por_conselho as (
    select orgao_id,
           max(mes) filter (where atos > 0) as ultimo_mes_com_ato,
           sum(atos) as atos_no_periodo
    from {{ ref('fct_conselho_mes') }}
    group by orgao_id
),
-- O segundo sinal (plano 2026-11-09): menções de outros órgãos na mesma janela do DOU. Não muda a situação.
mencoes as (
    select orgao_id, count(*) as mencoes_no_periodo, max(mes) as ultimo_mes_citado
    from {{ ref('fct_mencao') }}
    where mes between (select primeiro from cobertura) and (select ultimo from cobertura)
    group by orgao_id
),
-- o nome mais recente, não d.atual: o conselho extinto não tem nome atual e não pode sumir daqui
nome_recente as (
    select orgao_id, nome, sigla
    from {{ ref('dim_conselho') }}
    qualify row_number() over (partition by orgao_id order by valido_de desc) = 1
)
select
    d.orgao_id,
    d.nome,
    d.sigla,
    c.ultimo as mes_referencia,
    p.ultimo_mes_com_ato,
    coalesce(p.atos_no_periodo, 0) as atos_no_periodo,
    date_diff('month', p.ultimo_mes_com_ato, c.ultimo) as meses_sem_publicar,
    case
        when p.ultimo_mes_com_ato is null and coalesce(c.meses, 0) <= {{ var('meses_ativo', 3) }} then 'sem ato no período coberto'
        when p.ultimo_mes_com_ato is null then 'em silêncio'
        when date_diff('month', p.ultimo_mes_com_ato, c.ultimo) <= {{ var('meses_ativo', 3) }} then 'ativo'
        else 'em silêncio'
    end as situacao,
    coalesce(m.mencoes_no_periodo, 0) as mencoes_no_periodo,
    m.ultimo_mes_citado
from nome_recente d
cross join cobertura c
left join por_conselho p on p.orgao_id = d.orgao_id
left join mencoes m on m.orgao_id = d.orgao_id
