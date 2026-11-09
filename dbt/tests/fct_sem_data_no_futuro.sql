-- Data de publicação depois de hoje é erro de leitura do pubDate, não ato do futuro.
select ato_id, data_publicacao from {{ ref('fct_ato') }} where data_publicacao > current_date
