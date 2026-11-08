-- Todo conselho tem exatamente um nome vigente. Zero quebra o painel; dois duplicam o conselho.
select orgao_id, count(*) filter (where atual) as atuais
from {{ ref('dim_conselho') }}
group by orgao_id
having count(*) filter (where atual) <> 1
