-- SCD tipo 2: uma linha por nome que o conselho teve, com a vigência. Renomear é inserir, não sobrescrever.
-- Início nulo no OLTP (ADR 0004, ponto 4) vira limite aberto aqui, marcado em inicio_nao_verificado:
-- um valido_de nulo faria o fato descartar, sem erro, os atos desse conselho.
-- É conselho todo órgão que já teve "Conselho" no início do nome (ADR 0010), menos os da seed
-- conselhos_excluidos; vale por órgão, não por linha.
with escopo as (
    select orgao_id
    from {{ ref('stg_orgao_nome') }}
    group by orgao_id
    having bool_or(nome ilike 'conselho%')
       and not bool_or(nome in (select nome from {{ ref('conselhos_excluidos') }}))
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
join {{ ref('stg_orgao') }} o on o.orgao_id = n.orgao_id
left join {{ ref('stg_conselho') }} c on c.orgao_id = n.orgao_id
