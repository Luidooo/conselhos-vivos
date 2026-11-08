select orgao_id, eh_participativo
from {{ source('oltp', 'conselho') }}
