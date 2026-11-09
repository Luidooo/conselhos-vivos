-- Fato. Granularidade: uma linha por matéria publicada por outro órgão × conselho citado nela, no escopo da
-- dim_conselho (ADR 0010). É o segundo sinal de vida do conselho (plano 2026-11-09): alguém fora dele registrou
-- uma homologação, a composição, o regimento ou a estrutura que o inclui.
select
    s.id_dou || '-' || s.orgao_id::varchar as mencao_id,
    s.id_dou,
    s.orgao_id,
    s.nome_citado,
    s.data_publicacao,
    s.mes,
    s.tipo_ato,
    s.publicador,
    s.titulo,
    s.ementa,
    s.assunto
from {{ ref('stg_mencoes') }} s
where s.orgao_id in (select orgao_id from {{ ref('dim_conselho') }})
