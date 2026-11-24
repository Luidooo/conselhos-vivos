-- E4 (#112): o significado das colunas do OLTP que ainda não tinham comentário. O make dicionario lê estes
-- comentários para montar site/dicionario.md, e falha se alguma coluna ficar sem.

COMMENT ON COLUMN alerta.id IS 'Identificador do alerta.';
COMMENT ON COLUMN alerta.orgao_id IS 'Conselho a que o alerta se refere.';
COMMENT ON COLUMN alerta.tipo IS 'em_silencio: o conselho está em silêncio na mart_vitalidade. citado_sem_ato_proprio: não está ativo, mas outros órgãos o citaram no período.';
COMMENT ON COLUMN alerta.mes_referencia IS 'Último mês coberto pelo DOU quando o alerta foi gerado (mes_referencia da mart_vitalidade).';
COMMENT ON COLUMN alerta.detalhe IS 'Texto do alerta: o conselho, o que foi observado e o que conferir. O ETL reverso o atualiza enquanto o alerta está aberto.';
COMMENT ON COLUMN alerta.criado_em IS 'Quando o ETL reverso gravou o alerta pela primeira vez.';
COMMENT ON COLUMN alerta.tratado_por IS 'Revisor que tratou o alerta. Nulo: aberto.';
COMMENT ON COLUMN alerta.nota IS 'O que a curadoria conferiu ao tratar o alerta. Opcional.';

COMMENT ON COLUMN ato.id IS 'Identificador da linha: uma versão de um ato.';
COMMENT ON COLUMN ato.orgao_id IS 'Órgão que publicou o ato.';
COMMENT ON COLUMN ato.data_publicacao IS 'Data de publicação do ato, como veio da fonte.';
COMMENT ON COLUMN ato.ementa IS 'Ementa da matéria. Nos atos da planilha, o resumo escrito pela pesquisadora (ADR 0003).';
COMMENT ON COLUMN ato.conteudo IS 'Texto da matéria: no DOU, o HTML como veio; na planilha, o texto transcrito, quando há.';
COMMENT ON COLUMN ato.criado_em IS 'Quando a linha foi gravada no banco.';

COMMENT ON COLUMN classificacao.id IS 'Identificador da classificação. A tabela só recebe linha nova (ADR 0001).';
COMMENT ON COLUMN classificacao.ato_id IS 'Versão do ato que foi classificada.';
COMMENT ON COLUMN classificacao.tipologia_sigla IS 'Tipologia atribuída ao ato.';
COMMENT ON COLUMN classificacao.revisor_id IS 'Quem classificou.';
COMMENT ON COLUMN classificacao.criado_em IS 'Quando a classificação foi registrada. A mais recente de cada revisor é a vigente.';

COMMENT ON COLUMN conselho.orgao_id IS 'O órgão que a pesquisadora avaliou como conselho.';
COMMENT ON COLUMN conselho.descricao IS 'Descrição livre do conselho. Opcional.';
COMMENT ON COLUMN conselho.criado_em IS 'Quando a linha foi gravada no banco.';

COMMENT ON COLUMN orgao.id IS 'Identificador do órgão.';
COMMENT ON COLUMN orgao.criado_em IS 'Quando a linha foi gravada no banco.';

COMMENT ON COLUMN orgao_alias.id IS 'Identificador do alias.';
COMMENT ON COLUMN orgao_alias.fonte IS 'Onde o nome foi visto: PLANILHA ou DOU.';
COMMENT ON COLUMN orgao_alias.orgao_id IS 'Órgão a que o nome se refere. Nulo enquanto o status não for RESOLVIDO.';
COMMENT ON COLUMN orgao_alias.motivo IS 'Por que o nome está indefinido ou ambíguo. Obrigatório fora do RESOLVIDO.';
COMMENT ON COLUMN orgao_alias.criado_em IS 'Quando a linha foi gravada no banco.';

COMMENT ON COLUMN orgao_nome.id IS 'Identificador da linha de nome. Vira a chave substituta da dim_conselho.';
COMMENT ON COLUMN orgao_nome.orgao_id IS 'Órgão que teve esse nome.';
COMMENT ON COLUMN orgao_nome.nome IS 'Nome oficial do órgão nesse período.';
COMMENT ON COLUMN orgao_nome.criado_em IS 'Quando a linha foi gravada no banco.';

COMMENT ON COLUMN revisor.id IS 'Identificador do revisor.';
COMMENT ON COLUMN revisor.nome IS 'Nome de quem classifica. Dado pessoal quando o tipo é HUMANO (docs/lgpd.md).';
COMMENT ON COLUMN revisor.email IS 'E-mail do revisor. Dado pessoal: o papel app_curadoria não lê esta coluna (ADR 0011).';
COMMENT ON COLUMN revisor.criado_em IS 'Quando a linha foi gravada no banco.';

COMMENT ON COLUMN schema_migrations.arquivo IS 'Nome do arquivo de sql/ já aplicado pelo make migrate.';
COMMENT ON COLUMN schema_migrations.aplicado_em IS 'Quando a migração foi aplicada.';

COMMENT ON COLUMN tipologia.sigla IS 'Sigla da tipologia, a chave. O 99 é o Fora da tipologia, da planilha (ADR 0003).';
COMMENT ON COLUMN tipologia.nome IS 'Nome da tipologia.';
COMMENT ON COLUMN tipologia.descricao IS 'O que a tipologia cobre.';
