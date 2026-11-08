-- SCD tipo 2: uma linha por nome que o conselho teve, com a vigência. Renomear é inserir, não sobrescrever.
-- Início nulo no OLTP (ADR 0004, ponto 4) vira limite aberto aqui, marcado em inicio_nao_verificado:
-- um valido_de nulo faria o fato descartar, sem erro, os atos desse conselho.
-- É conselho todo órgão que tem ou já teve "Conselho" no nome (ADR 0010); vale por órgão, não por linha.
with escopo as (
    select orgao_id
    from {{ ref('stg_orgao_nome') }}
    group by orgao_id
    having bool_or(nome ilike 'conselho%')
)

select
    n.orgao_nome_id as conselho_sk,
    n.orgao_id,
    n.nome,
    o.sigla,
    o.codigo_siorg,
    coalesce(n.data_inicio, date '0001-01-01') as valido_de,
    n.data_inicio is null as inicio_nao_verificado,
    coalesce(n.data_fim, date '9999-12-31') as valido_ate,
    n.data_fim is null as atual,
    c.eh_participativo -- nulo = não avaliado pela pesquisadora, não falso
from {{ ref('stg_orgao_nome') }} n
join escopo e on e.orgao_id = n.orgao_id
join {{ source('oltp', 'orgao') }} o on o.id = n.orgao_id
left join {{ source('oltp', 'conselho') }} c on c.orgao_id = n.orgao_id
