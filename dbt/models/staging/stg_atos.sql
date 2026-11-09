-- Uma linha por matéria: a versão mais recente. Uma matéria do DOU é o id_dou; um ato da planilha é o próprio ato.
select
    *,
    date_trunc('month', data_publicacao)::date as mes,
    case when origem = 'DOU' then 'DOU:' || id_origem else 'PLANILHA:' || ato_id::varchar end as materia
from {{ source('silver', 'atos') }}
{% if var('excluir_mes', none) %}
-- shortcut: só para demonstrar o teste de distribuição (#71); nunca use em produção.
where date_trunc('month', data_publicacao)::date <> date '{{ var("excluir_mes") }}'
{% endif %}
qualify row_number() over (partition by materia order by versao desc) = 1
