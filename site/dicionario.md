---
title: Dicionário de dados
outline: [2, 2]
---

# Dicionário de dados

As colunas do projeto, da curadoria no Postgres (oltp) às tabelas que o painel lê (gold). A silver, em Delta, aparece pelo staging, menos quatro colunas de controle da tabela de menções, que ele não lê: `ano`, `atualizado_em`, `checksum` e `fonte`. Gerado pelo `make dicionario`
a partir do banco e do dbt: o tipo é o real, e o significado vem das descrições no YAML do dbt e dos `COMMENT ON` do
Postgres. Coluna sem significado faz o `make dicionario` falhar.

<!-- dicionario:inicio -->
## fonte oltp

| Tabela | Coluna | Tipo | Significado |
|---|---|---|---|
| conselho | criado_em | TIMESTAMP WITH TIME ZONE | Quando a linha foi gravada no banco. |
| conselho | descricao | VARCHAR | Descrição livre do conselho. Opcional. |
| conselho | eh_participativo | BOOLEAN | Marca da pesquisadora: o conselho tem participação da sociedade civil. |
| conselho | orgao_id | INTEGER | O órgão que a pesquisadora avaliou como conselho. |
| orgao | codigo_siorg | INTEGER | Código da unidade no SIORG, quando o nome casa com exatamente uma unidade. Vínculo externo, não identidade (ADR 0004). |
| orgao | criado_em | TIMESTAMP WITH TIME ZONE | Quando a linha foi gravada no banco. |
| orgao | id | INTEGER | Identificador do órgão. |
| orgao | parent_id | INTEGER | Órgão pai na hierarquia administrativa. |
| orgao | sigla | VARCHAR | Sigla do órgão (SIORG ou a da planilha). Não é única entre conselhos. |
| orgao_nome | criado_em | TIMESTAMP WITH TIME ZONE | Quando a linha foi gravada no banco. |
| orgao_nome | data_fim | DATE | Fim da vigência do nome. Nulo é o nome em uso. |
| orgao_nome | data_inicio | DATE | Início da vigência do nome: a data do ato legal que o deu. Nulo é data não verificada (ADR 0004). |
| orgao_nome | id | INTEGER | Identificador da linha de nome. |
| orgao_nome | nome | VARCHAR | Nome oficial do órgão nesse período. |
| orgao_nome | orgao_id | INTEGER | Órgão que teve esse nome. |

## gold

| Tabela | Coluna | Tipo | Significado |
|---|---|---|---|
| dim_conselho | atual | BOOLEAN | Verdadeiro no nome sem data de fim. Conselho extinto não tem nome atual. |
| dim_conselho | codigo_siorg | INTEGER | Código da unidade no SIORG, quando o nome casa com exatamente uma unidade. Vínculo externo, não identidade (ADR 0004). |
| dim_conselho | conselho_sk | INTEGER | Chave substituta: o id da linha de nome no OLTP (orgao_nome.id). O conselho tem uma por nome que teve. |
| dim_conselho | eh_participativo | BOOLEAN | Marca da pesquisadora. Nulo significa não avaliado, não falso. |
| dim_conselho | inicio_nao_verificado | BOOLEAN | Verdadeiro quando o OLTP não tem a data de início do nome (ADR 0004, ponto 4). Nesse caso valido_de é 0001-01-01, um limite aberto, não uma data real. |
| dim_conselho | nome | VARCHAR | Nome do conselho nesse período. |
| dim_conselho | orgao_id | INTEGER | Identificador do conselho no OLTP. É o mesmo em todos os nomes do conselho. |
| dim_conselho | sigla | VARCHAR | Sigla do órgão (SIORG ou a da planilha). Não é única entre conselhos. |
| dim_conselho | valido_ate | DATE | Fim da vigência do nome. É 9999-12-31 no nome sem fim. |
| dim_conselho | valido_de | DATE | Início da vigência do nome. É 0001-01-01 quando a data não foi verificada (inicio_nao_verificado). |
| fct_ato | ato_id | BIGINT | Id da versão mais recente da matéria no OLTP (ato.id). |
| fct_ato | conselho_sk | INTEGER | O nome que o conselho tinha na data da publicação (dim_conselho). |
| fct_ato | data_publicacao | DATE | Data de publicação do ato, como veio da fonte. |
| fct_ato | materia | VARCHAR | Chave da matéria: DOU: mais o id do DOU, ou PLANILHA: mais o id do ato. As versões de uma retificação têm a mesma. |
| fct_ato | mes | DATE | Primeiro dia do mês da publicação. |
| fct_ato | nome_aproximado | BOOLEAN | Verdadeiro quando a data cai fora da vigência do nome escolhido. |
| fct_ato | orgao_id | INTEGER | Conselho que publicou o ato. |
| fct_ato | origem | VARCHAR | DOU: matéria lida do Diário Oficial. PLANILHA: ato da carga inicial da pesquisadora. |
| fct_ato | revisor_tipo | VARCHAR | Quem deu a classificação vigente: HUMANO ou PIPELINE. Nulo sem classificação. |
| fct_ato | tipologia_sigla | VARCHAR | Tipologia da classificação vigente. SEM quando o ato não foi classificado. |
| fct_conselho_mes | atos | BIGINT | Matérias do DOU publicadas pelo conselho no mês. Zero é o mês de silêncio. |
| fct_conselho_mes | mes | DATE | Primeiro dia do mês, dentro do período coberto pelo DOU. |
| fct_conselho_mes | orgao_id | INTEGER | Conselho. |
| fct_mencao | assunto | VARCHAR | Do que a matéria trata em relação ao conselho: extinção, criação, estrutura, regimento, homologação, composição ou outro. |
| fct_mencao | data_publicacao | DATE | Data de publicação da matéria que cita o conselho. |
| fct_mencao | ementa | VARCHAR | Ementa da matéria que cita o conselho. |
| fct_mencao | id_dou | VARCHAR | Identificador da matéria do outro órgão, emitido pela Imprensa Nacional. |
| fct_mencao | mencao_id | VARCHAR | Chave da menção: o id da matéria no DOU, um hífen e o id do conselho citado. |
| fct_mencao | mes | DATE | Primeiro dia do mês da publicação. |
| fct_mencao | nome_citado | VARCHAR | O nome do conselho como apareceu na matéria. |
| fct_mencao | orgao_id | INTEGER | Conselho citado na matéria. |
| fct_mencao | publicador | VARCHAR | Órgão que publicou a matéria, com a hierarquia separada por barra. |
| fct_mencao | tipo_ato | VARCHAR | Tipo do ato, como veio no XML do DOU. |
| fct_mencao | titulo | VARCHAR | Título da matéria que cita o conselho. |
| freshness_vitalidade | atraso_meses | BIGINT | Meses entre o último mês coberto e o esperado. Zero ou negativo é em dia. |
| freshness_vitalidade | dentro_do_sla | BOOLEAN | Verdadeiro quando o atraso é zero ou menos. Falso também com o DOU vazio. |
| freshness_vitalidade | mes_esperado | DATE | O mês que o SLA espera hoje: o mês M tem de estar na gold até o dia 20 do mês M+1. |
| freshness_vitalidade | primeiro_mes_coberto | DATE | Primeiro mês com DOU na gold. |
| freshness_vitalidade | ultimo_mes_coberto | DATE | Último mês com DOU na gold. |
| mart_vitalidade | atos_no_periodo | HUGEINT | Matérias do DOU publicadas pelo conselho no período coberto. |
| mart_vitalidade | mencoes_no_periodo | BIGINT | Matérias de outros órgãos que citam o conselho, no período coberto. Não muda a situação. |
| mart_vitalidade | mes_referencia | DATE | Último mês coberto pelo DOU. A situação vale para esse mês, não para hoje. |
| mart_vitalidade | meses_sem_publicar | BIGINT | Meses entre o último mês com ato e o mês de referência. Nulo se não publicou no período coberto. |
| mart_vitalidade | nome | VARCHAR | Nome mais recente do conselho. |
| mart_vitalidade | orgao_id | INTEGER | Conselho. |
| mart_vitalidade | sigla | VARCHAR | Sigla do órgão (SIORG ou a da planilha). Não é única entre conselhos. |
| mart_vitalidade | situacao | VARCHAR | ativo: publicou há meses_ativo meses (padrão 3) ou menos. em silêncio: há mais que isso, ou nunca, com a cobertura já maior que o limite. sem ato no período coberto: nunca, com a cobertura ainda dentro do limite. |
| mart_vitalidade | ultimo_mes_citado | DATE | Último mês em que outro órgão citou o conselho. Nulo sem menção no período. |
| mart_vitalidade | ultimo_mes_com_ato | DATE | Último mês em que o conselho publicou. Nulo se não publicou no período coberto. |
| metricflow_time_spine | date_day | DATE | Um dia por linha, de 2002 a 2030. É a espinha de tempo que o MetricFlow exige. |

## oltp

| Tabela | Coluna | Tipo | Significado |
|---|---|---|---|
| alerta | criado_em | timestamp with time zone | Quando o ETL reverso gravou o alerta pela primeira vez. |
| alerta | detalhe | text | Texto do alerta: o conselho, o que foi observado e o que conferir. O ETL reverso o atualiza enquanto o alerta está aberto. |
| alerta | id | bigint | Identificador do alerta. |
| alerta | mes_referencia | date | Último mês coberto pelo DOU quando o alerta foi gerado (mes_referencia da mart_vitalidade). |
| alerta | nota | text | O que a curadoria conferiu ao tratar o alerta. Opcional. |
| alerta | orgao_id | integer | Conselho a que o alerta se refere. |
| alerta | tipo | character varying(30) | em_silencio: o conselho está em silêncio na mart_vitalidade. citado_sem_ato_proprio: não está ativo, mas outros órgãos o citaram no período. |
| alerta | tratado_em | timestamp with time zone | Quando a curadoria tratou o alerta, na página Revisar. Nulo: aberto. |
| alerta | tratado_por | integer | Revisor que tratou o alerta. Nulo: aberto. |
| ato | conteudo | text | Texto da matéria: no DOU, o HTML como veio; na planilha, o texto transcrito, quando há. |
| ato | criado_em | timestamp with time zone | Quando a linha foi gravada no banco. |
| ato | data_publicacao | date | Data de publicação do ato, como veio da fonte. |
| ato | ementa | text | Ementa da matéria. Nos atos da planilha, o resumo escrito pela pesquisadora (ADR 0003). |
| ato | id | bigint | Identificador da linha: uma versão de um ato. |
| ato | id_dou | character varying(100) | Identificador natural da matéria emitido pela Imprensa Nacional. NULL para atos de origem PLANILHA. |
| ato | id_planilha | integer | ID_VERSAO da planilha da pesquisadora. Com orgao_id, é a chave dos atos de origem PLANILHA; NULL para os do DOU. |
| ato | orgao_id | integer | Órgão que publicou o ato. |
| ato | origem | character varying(20) | DOU: matéria lida do Diário Oficial (exige id_dou e conteudo). PLANILHA: ato da carga inicial da pesquisadora, 2003–2020 (exige id_planilha); ementa é o resumo dela e conteudo o texto que ela transcreveu, quando há. |
| ato | ref_legal | character varying(100) | Referência legal como aparece na fonte (ex.: Resolução Nº 18). Informativa: não é única e falta em parte da planilha. |
| ato | versao | integer | Versão da publicação. Atos retificados recebem nova versão com o mesmo id_dou sem sobrescrever a original. |
| classificacao | ato_id | bigint | Versão do ato que foi classificada. |
| classificacao | confianca | numeric(4,3) | Score de confiança da predição (utilizado quando revisor.tipo = PIPELINE, valor entre 0 e 1). |
| classificacao | criado_em | timestamp with time zone | Quando a classificação foi registrada. A mais recente de cada revisor para cada ato é a vigente. |
| classificacao | id | bigint | Identificador da classificação. A tabela só recebe linha nova (ADR 0001). |
| classificacao | revisor_id | integer | Quem classificou. |
| classificacao | tipologia_sigla | character varying(10) | Tipologia atribuída ao ato. |
| classificacao_vigente | ato_id | bigint | Versão do ato que foi classificada. |
| classificacao_vigente | confianca | numeric(4,3) | Score de confiança da predição, entre 0 e 1, quando o revisor é PIPELINE. |
| classificacao_vigente | criado_em | timestamp with time zone | Quando a classificação vigente foi registrada. |
| classificacao_vigente | id | bigint | Identificador da classificação vigente (classificacao.id). |
| classificacao_vigente | revisor_id | integer | Quem classificou. Há uma linha por revisor para cada ato. |
| classificacao_vigente | tipologia_sigla | character varying(10) | Tipologia atribuída ao ato. |
| conselho | criado_em | timestamp with time zone | Quando a linha foi gravada no banco. |
| conselho | descricao | text | Descrição livre do conselho. Opcional. |
| conselho | eh_participativo | boolean | Distingue conselhos com participação da sociedade civil daqueles puramente corporativos/consultivos (ex: CFM, CFF). |
| conselho | orgao_id | integer | O órgão que a pesquisadora avaliou como conselho. |
| orgao | codigo_siorg | integer | Código da unidade no SIORG, quando o nome casa com exatamente uma unidade. Vínculo externo, não identidade (ADR 0004). |
| orgao | criado_em | timestamp with time zone | Quando a linha foi gravada no banco. |
| orgao | id | integer | Identificador do órgão. |
| orgao | parent_id | integer | Auto-relacionamento hierárquico (ex: CONAMA tem como pai o Ministério do Meio Ambiente). |
| orgao | sigla | character varying(30) | Sigla do órgão (SIORG ou a da planilha). Não é única: CNE e CNT se repetem entre conselhos diferentes. |
| orgao_alias | chave | character varying(255) | Nome sem caixa, acento, espaços repetidos e sigla no fim (src/conselhos). Nomes com a mesma chave são o mesmo órgão. |
| orgao_alias | criado_em | timestamp with time zone | Quando a linha foi gravada no banco. |
| orgao_alias | fonte | character varying(20) | Onde o nome foi visto: PLANILHA ou DOU. |
| orgao_alias | id | integer | Identificador do alias. |
| orgao_alias | motivo | text | Por que o nome está indefinido ou ambíguo. Obrigatório fora do RESOLVIDO. |
| orgao_alias | nome | character varying(255) | Nome como aparece na fonte, com espaços e quebras de linha reduzidos a um espaço. |
| orgao_alias | orgao_id | integer | Órgão a que o nome se refere. Nulo enquanto o status não for RESOLVIDO. |
| orgao_alias | status | character varying(20) | RESOLVIDO: aponta para um órgão. INDEFINIDO: nome genérico, sem como saber o órgão. AMBIGUO: à espera de decisão da squad ou da pesquisadora. |
| orgao_nome | criado_em | timestamp with time zone | Quando a linha foi gravada no banco. |
| orgao_nome | data_fim | date | Data final de vigência do nome. Se NULL, indica o nome em uso corrente. |
| orgao_nome | data_inicio | date | Início da vigência do nome: data do ato legal que o criou ou deu. NULL = data não verificada (ADR 0004); consulta por vigência precisa tratar o nulo. |
| orgao_nome | id | integer | Identificador da linha de nome. Vira a chave substituta da dim_conselho. |
| orgao_nome | nome | character varying(255) | Nome oficial do órgão nesse período. |
| orgao_nome | orgao_id | integer | Órgão que teve esse nome. |
| revisor | criado_em | timestamp with time zone | Quando a linha foi gravada no banco. |
| revisor | email | character varying(255) | E-mail do revisor. Dado pessoal: o papel app_curadoria não lê esta coluna (ADR 0011). |
| revisor | id | integer | Identificador do revisor. |
| revisor | nome | character varying(150) | Nome de quem classifica. Dado pessoal quando o tipo é HUMANO (docs/lgpd.md). |
| revisor | tipo | character varying(20) | Classifica o revisor entre HUMANO (bolsista, pesquisador) ou PIPELINE (modelo automatizado). |
| schema_migrations | aplicado_em | timestamp with time zone | Quando a migração foi aplicada. |
| schema_migrations | arquivo | text | Nome do arquivo de sql/ já aplicado pelo make migrate. |
| tipologia | descricao | text | O que a tipologia cobre. |
| tipologia | nome | character varying(100) | Nome da tipologia. |
| tipologia | sigla | character varying(10) | Sigla da tipologia, a chave. O 99 é o Fora da tipologia, da planilha (ADR 0003). |

## seed

| Tabela | Coluna | Tipo | Significado |
|---|---|---|---|
| conselhos_excluidos | motivo | VARCHAR | Por que o órgão não é um colegiado de participação social. |
| conselhos_excluidos | nome | VARCHAR | Nome do órgão excluído, como em orgao_nome. |

## staging

| Tabela | Coluna | Tipo | Significado |
|---|---|---|---|
| stg_atos | ano | INTEGER | Ano da publicação. Particiona a tabela Delta (ADR 0006). |
| stg_atos | ato_id | BIGINT | Id da versão do ato no OLTP (ato.id). |
| stg_atos | atualizado_em | TIMESTAMP WITH TIME ZONE | Quando o lake gravou a linha na silver. |
| stg_atos | checksum | VARCHAR | Resumo do texto, da data, da referência legal, do órgão, da classificação e do tipo do revisor. O lake só regrava o ato quando ele muda. |
| stg_atos | codigo_siorg | INTEGER | Código da unidade no SIORG, quando o nome casa com exatamente uma unidade. Vínculo externo, não identidade (ADR 0004). |
| stg_atos | conteudo | VARCHAR | Texto da matéria: no DOU, o HTML como veio. |
| stg_atos | data_publicacao | DATE | Data de publicação do ato, como veio da fonte. |
| stg_atos | ementa | VARCHAR | Ementa da matéria. Nos atos da planilha, o resumo escrito pela pesquisadora. |
| stg_atos | id_origem | VARCHAR | Id da matéria na fonte: o id do DOU, ou o ID_VERSAO da planilha. |
| stg_atos | materia | VARCHAR | Chave da matéria: DOU: mais o id do DOU, ou PLANILHA: mais o id do ato. As versões de uma retificação têm a mesma. |
| stg_atos | mes | DATE | Primeiro dia do mês da publicação. |
| stg_atos | orgao_id | INTEGER | Órgão que publicou o ato. |
| stg_atos | orgao_nome | VARCHAR | Nome do órgão na data da publicação. Sem nome para a data, o nome vigente. |
| stg_atos | orgao_sigla | VARCHAR | Sigla do órgão (SIORG ou a da planilha). Não é única entre conselhos. |
| stg_atos | origem | VARCHAR | DOU: matéria lida do Diário Oficial. PLANILHA: ato da carga inicial da pesquisadora. |
| stg_atos | ref_legal | VARCHAR | Referência legal como aparece na fonte. Informativa: não é única. |
| stg_atos | revisor_tipo | VARCHAR | Quem deu a classificação vigente: HUMANO ou PIPELINE. Nulo sem classificação. |
| stg_atos | tipologia_sigla | VARCHAR | Tipologia da classificação vigente. A de revisor humano vence a do pipeline. Nulo sem classificação. |
| stg_atos | versao | INTEGER | Versão da publicação. Fica só a mais recente de cada matéria. |
| stg_conselho | eh_participativo | BOOLEAN | Marca da pesquisadora: o conselho tem participação da sociedade civil. |
| stg_conselho | orgao_id | INTEGER | O órgão que a pesquisadora avaliou como conselho. |
| stg_mencoes | assunto | VARCHAR | Do que a matéria trata em relação ao conselho: extinção, criação, estrutura, regimento, homologação, composição ou outro. |
| stg_mencoes | data_publicacao | DATE | Data de publicação da matéria que cita o conselho. |
| stg_mencoes | ementa | VARCHAR | Ementa da matéria que cita o conselho. |
| stg_mencoes | id_dou | VARCHAR | Identificador da matéria do outro órgão, emitido pela Imprensa Nacional. |
| stg_mencoes | mes | DATE | Primeiro dia do mês da publicação. |
| stg_mencoes | nome_citado | VARCHAR | O nome do conselho como apareceu na matéria. |
| stg_mencoes | orgao_id | INTEGER | Conselho citado na matéria. |
| stg_mencoes | publicador | VARCHAR | Órgão que publicou a matéria, com a hierarquia separada por barra. |
| stg_mencoes | tipo_ato | VARCHAR | Tipo do ato, como veio no XML do DOU. |
| stg_mencoes | titulo | VARCHAR | Título da matéria que cita o conselho. |
| stg_orgao | codigo_siorg | INTEGER | Código da unidade no SIORG, quando o nome casa com exatamente uma unidade. Vínculo externo, não identidade (ADR 0004). |
| stg_orgao | orgao_id | INTEGER | Identificador do órgão no OLTP (orgao.id). |
| stg_orgao | sigla | VARCHAR | Sigla do órgão (SIORG ou a da planilha). Não é única entre conselhos. |
| stg_orgao_nome | data_fim | DATE | Fim da vigência do nome. Nulo é o nome em uso. |
| stg_orgao_nome | data_inicio | DATE | Início da vigência do nome: a data do ato legal que o deu. Nulo é data não verificada (ADR 0004). |
| stg_orgao_nome | nome | VARCHAR | Nome oficial do órgão nesse período. |
| stg_orgao_nome | orgao_id | INTEGER | Identificador do órgão no OLTP (orgao.id). |
| stg_orgao_nome | orgao_nome_id | INTEGER | Identificador da linha de nome no OLTP (orgao_nome.id). |

<!-- dicionario:fim -->
