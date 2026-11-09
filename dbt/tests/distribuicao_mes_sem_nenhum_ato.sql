-- Um mês do período coberto sem nenhum ato de nenhum conselho não é silêncio: é um mês que não foi
-- ingerido. Sem este teste, o painel mostraria todos os conselhos parados naquele mês.
-- Limite: o intervalo de meses vem do min/max dos atos do DOU, então só pega buraco no meio. Faltar o primeiro ou o último mês encolhe a série e passa; o mês mais recente sem carga é do freshness (#72).
select mes, sum(atos) as atos
from {{ ref('fct_conselho_mes') }}
group by mes
having sum(atos) = 0
