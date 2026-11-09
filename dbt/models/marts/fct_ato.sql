-- Fato. Granularidade: uma linha por matéria publicada (a versão mais recente), ligada ao nome que o
-- conselho tinha na data da publicação. Atos de órgãos fora da dim_conselho (ADR 0010) saem daqui; a
-- contagem deles está em docs/adr/medicoes/0009-gold/fct_ato-fora-do-escopo.txt.
with atos as (
    select ato_id, materia, origem, data_publicacao, mes, orgao_id, tipologia_sigla, revisor_tipo
    from {{ ref('stg_atos') }}
    where orgao_id in (select orgao_id from {{ ref('dim_conselho') }})
),
primeiro_nome as (
    select orgao_id, conselho_sk from {{ ref('dim_conselho') }}
    qualify row_number() over (partition by orgao_id order by valido_de) = 1
),
-- asof: o último nome que começou até a data. Cobre o nome vigente, um buraco entre dois nomes e o ato
-- depois da extinção (fica com o último nome). Antes do primeiro nome não há par: fica com o mais antigo.
casado as (
    select a.*, d.conselho_sk, d.valido_ate
    from atos a
    asof left join {{ ref('dim_conselho') }} d
      on a.orgao_id = d.orgao_id and a.data_publicacao >= d.valido_de
)
select
    c.ato_id,
    c.materia,
    c.origem,
    c.data_publicacao,
    c.mes,
    c.orgao_id,
    coalesce(c.conselho_sk, p.conselho_sk) as conselho_sk,
    -- aproximado: a data cai fora da vigência do nome escolhido
    c.conselho_sk is null or c.data_publicacao > c.valido_ate as nome_aproximado,
    coalesce(c.tipologia_sigla, 'SEM') as tipologia_sigla,
    c.revisor_tipo
from casado c
left join primeiro_nome p on p.orgao_id = c.orgao_id
