-- Medição do dado pessoal no OLTP (docs/lgpd.md).
-- Uso: docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < docs/lgpd/medir.sql
select 'revisores humanos' as o_que, count(*) from revisor where tipo = 'HUMANO'
union all select 'revisores com e-mail', count(*) from revisor where email is not null
union all select 'atos com CPF mascarado no texto', count(*) from ato where conteudo ~ '\*{3}\.[0-9]{3}\.[0-9]{3}-\*{2}'
-- só a ementa e o começo do texto: no texto inteiro, um regimento que manda "designar os relatores" contaria
union all select 'atos de nomeação, designação ou exoneração', count(*) from ato
  where ementa ~* '(nomea|designa|exonera)' or left(conteudo, 300) ~* '(nomear|designar|exonerar)'
union all select 'atos do DOU', count(*) from ato where origem = 'DOU'
union all select 'atos no total (DOU e planilha)', count(*) from ato;
