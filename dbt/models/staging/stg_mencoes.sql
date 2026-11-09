-- Uma linha por matéria de outro órgão × órgão citado nela, como a silver grava (python -m mencoes).
-- O escopo do ADR 0010 fica no fct_mencao.
select
    id_dou,
    orgao_id,
    nome_citado,
    data_publicacao,
    date_trunc('month', data_publicacao)::date as mes,
    tipo_ato,
    publicador,
    titulo,
    ementa,
    assunto
from {{ source('silver', 'mencoes') }}
