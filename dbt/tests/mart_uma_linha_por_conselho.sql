-- A vitalidade responde por todo conselho do escopo: nenhum pode sumir, nem o extinto.
with esperado as (select count(distinct orgao_id) as n from {{ ref('dim_conselho') }}),
real as (select count(*) as n from {{ ref('mart_vitalidade') }})
select esperado.n as esperado, real.n as real
from esperado, real
where esperado.n <> real.n
