-- No gabarito da pesquisadora, 6 de 215 atos (3%) ficam fora da tipologia. Passar de 20% indica
-- classificação quebrada, não conselhos diferentes.
select count(*) filter (where tipologia_sigla = '99') * 1.0 / count(*) as fracao_fora
from {{ ref('fct_ato') }}
where tipologia_sigla <> 'SEM'
having count(*) > 0 and count(*) filter (where tipologia_sigla = '99') * 1.0 / count(*) > 0.2
