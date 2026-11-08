-- Duas vigências do mesmo conselho que se cruzam fariam um ato casar com dois nomes e contar duas vezes.
select a.orgao_id, a.conselho_sk, b.conselho_sk as outro
from {{ ref('dim_conselho') }} a
join {{ ref('dim_conselho') }} b
  on a.orgao_id = b.orgao_id
 and a.conselho_sk < b.conselho_sk
 and a.valido_de <= b.valido_ate
 and b.valido_de <= a.valido_ate
