select id as orgao_id, sigla, codigo_siorg
from {{ source('oltp', 'orgao') }}
