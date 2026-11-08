-- No máximo um nome vigente por conselho. Dois duplicam o conselho. Zero é o estado "extinto"
-- (todos os nomes encerrados) e não é erro: a pergunta da E3 é justamente quais ainda funcionam.
select orgao_id, count(*) filter (where atual) as atuais
from {{ ref('dim_conselho') }}
group by orgao_id
having count(*) filter (where atual) > 1
