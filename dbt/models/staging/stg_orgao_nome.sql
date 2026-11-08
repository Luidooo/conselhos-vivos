select id as orgao_nome_id, orgao_id, nome, data_inicio, data_fim
from {{ source('oltp', 'orgao_nome') }}
