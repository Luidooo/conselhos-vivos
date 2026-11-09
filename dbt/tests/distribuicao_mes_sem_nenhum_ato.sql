-- Um mês do período coberto sem nenhum ato de nenhum conselho não é silêncio: é um mês que não foi
-- ingerido. Sem este teste, o painel mostraria todos os conselhos parados naquele mês.
select mes, sum(atos) as atos
from {{ ref('fct_conselho_mes') }}
group by mes
having sum(atos) = 0
