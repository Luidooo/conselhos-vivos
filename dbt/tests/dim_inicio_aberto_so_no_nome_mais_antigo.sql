-- O início desconhecido (0001-01-01) só cabe no nome mais antigo do conselho. Um nome novo sem data
-- passaria despercebido, porque o coalesce da dimensão esconde o nulo do OLTP.
select a.orgao_id, a.conselho_sk
from {{ ref('dim_conselho') }} a
where a.inicio_nao_verificado
  and exists (
      select 1 from {{ ref('dim_conselho') }} b
      where b.orgao_id = a.orgao_id and b.valido_ate < a.valido_ate
  )
