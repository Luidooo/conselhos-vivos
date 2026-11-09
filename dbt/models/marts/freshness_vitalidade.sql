-- Freshness de mart_vitalidade. SLA: o mês M está na gold até o dia 20 do mês M+1.
-- Hoje se espera, então, o mês de (hoje - 20 dias) menos um. A var hoje só existe para os testes fixarem a data.
-- View, não tabela: o current_date vale na hora da leitura. Como tabela, o "hoje" congelaria no dia do make gold,
-- e o painel diria "dentro do SLA" mesmo depois do prazo, justamente quando a carga do mês falhou e a gold não
-- foi refeita.
{{ config(materialized='view') }}
with cobertura as (select min(mes) as primeiro, max(mes) as ultimo from {{ ref('fct_conselho_mes') }}),
hoje as (
    select {% if var('hoje', none) %}date '{{ var("hoje") }}'{% else %}current_date{% endif %} as dia
),
esperado as (select (date_trunc('month', dia - interval 20 day) - interval 1 month)::date as mes from hoje)
select
    c.primeiro as primeiro_mes_coberto,
    c.ultimo as ultimo_mes_coberto,
    e.mes as mes_esperado,
    date_diff('month', c.ultimo, e.mes) as atraso_meses,
    -- DOU vazio está fora do SLA: um nulo aqui faria o teste sla_vitalidade passar calado
    coalesce(date_diff('month', c.ultimo, e.mes) <= 0, false) as dentro_do_sla
from cobertura c, esperado e
