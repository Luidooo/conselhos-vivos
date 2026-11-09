-- Aviso, não erro: gold atrasada não deve impedir o resto do grafo, mas precisa aparecer.
{{ config(severity='warn') }}
select * from {{ ref('freshness_vitalidade') }} where not dentro_do_sla
