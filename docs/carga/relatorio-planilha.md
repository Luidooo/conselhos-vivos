# Relatório de carga da planilha da pesquisadora

> Gerado por `make carga` (`python -m planilha relatorio`); não editar à mão. Rodar de novo sobre a mesma planilha gera este mesmo arquivo.

**Arquivo:** `data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx` · sha256 `635b3f0a6580fff358171b830b13ef2a2ccd2945f0f2d05a7e0c178964c7d347`

## Resumo

| Aba | Conselho | Linhas no arquivo¹ | Com valor | Atos | Descartadas | Com classificação |
|---|---|---|---|---|---|---|
| CNAS | Conselho Nacional de Assistência Social | 366 | 53 | 53 | 0 | 53 |
| CONAMA | Conselho Nacional do Meio Ambiente | 98 | 98 | 98 | 0 | 98 |
| CONCIDADES | Conselho das Cidades | 848 | 28 | 28 | 0 | 28 |
| CONDRAF | Conselho Nacional de Desenvolvimento Rural Sustentável | 951 | 24 | 24 | 0 | 24 |
| CNPIR | Conselho Nacional de Promoção da Igualdade Racial | 374 | 12 | 12 | 0 | 12 |
| **Total** |  | **2.637** | **215** | **215** | **0** | **215** |

¹ Abaixo do cabeçalho, contando as que só têm formatação de célula. Linha sem nenhum valor não é registro. O 2.638 do diário de 25/09 é a soma do `max_row` − 1 do openpyxl, que no CONAMA conta também o cabeçalho, porque ele está na linha 2.

Toda linha com valor virou ato ou descarte: 215 + 0 = 215.

## Descartes

Nenhuma linha descartada.

## Atos sem classificação

Todo ato tem classificação da pesquisadora.

## Tipologia por aba

| Aba | DEF | FISC | GEST | AUTO | IP | 99 | sem |
|---|---|---|---|---|---|---|---|
| CNAS | 14 | 3 | 1 | 33 | 1 | 1 | 0 |
| CONAMA | 28 | 28 | 3 | 34 | 3 | 2 | 0 |
| CONCIDADES | 19 | 0 | 1 | 3 | 3 | 2 | 0 |
| CONDRAF | 7 | 0 | 1 | 16 | 0 | 0 | 0 |
| CNPIR | 0 | 0 | 0 | 11 | 0 | 1 | 0 |
| **Total** | **68** | **31** | **6** | **97** | **7** | **6** | **0** |

## Conversões

215 datas convertidas do serial do Excel (dia 0 = 30/12/1899). Além delas:

| Aba | Linha | Conversão |
|---|---|---|
| CNPIR | 2 | DIS_LEG 38353 (o Excel leu como 2005-01-01) → '1/2005' |
| CNPIR | 3 | DIS_LEG 38749 (o Excel leu como 2006-02-01) → '2/2006' |
| CNPIR | 4 | DIS_LEG 39142 (o Excel leu como 2007-03-01) → '3/2007' |
| CNPIR | 5 | DIS_LEG 40634 (o Excel leu como 2011-04-01) → '4/2011' |
| CNPIR | 6 | tipologia '99 MOÇÃO' → 99 (a anotação fica no CSV) |
| CNPIR | 7 | DIS_LEG 42401 (o Excel leu como 2016-02-01) → '2/2016' |
| CNPIR | 8 | DIS_LEG 42370 (o Excel leu como 2016-01-01) → '1/2016' |
| CNPIR | 9 | DIS_LEG 42736 (o Excel leu como 2017-01-01) → '1/2017' |
| CNPIR | 10 | DIS_LEG 43891 (o Excel leu como 2020-03-01) → '3/2020' |
| CNPIR | 11 | DIS_LEG 43862 (o Excel leu como 2020-02-01) → '2/2020' |
| CNPIR | 12 | DIS_LEG 44044 (o Excel leu como 2020-08-01) → '8/2020' |
| CNPIR | 13 | DIS_LEG 44075 (o Excel leu como 2020-09-01) → '9/2020' |

## Avisos

| Aba | Linha | Aviso |
|---|---|---|
| CNPIR | 5 | célula G5 fora das colunas do cabeçalho, não carregada: 'Obs.: só em parágrafos adiante a resolução informa que se trata de criar Comissões e Grupos de Trabalho do Conselho' |

## Mapeamento

Cada coluna da planilha vira um campo do vocabulário único (`src/planilha/abas.py`).

### CNAS → Conselho Nacional de Assistência Social

Cabeçalho na linha 1.

| Coluna na planilha | Campo | Destino | Por quê |
|---|---|---|---|
| `ID_VERSAO` | id_versao | ato.id_planilha | chave do ato na planilha, junto com o conselho (sql/003) |
| `ANO` | ano | não carregado | redundante com a data; conferido, e a divergência vira aviso |
| `DATA` | data | ato.data_publicacao | serial do Excel convertido; a planilha não diz se é a data de publicação ou de assinatura |
| `TEMA` | ementa | ato.ementa | resumo do ato escrito pela pesquisadora |
| `AUTOR` | autor | não carregado | a aba já identifica o conselho; os valores encontrados estão no relatório |
| `REFERENTE` | referente | não carregado | outro rótulo dela (a quem o ato se dirige); o esquema não tem onde guardar, fica no CSV normalizado |
| `TIPOL_DECIS (M e J)` | tipologia | classificacao.tipologia_sigla | rótulo da pesquisadora, não atributo do ato: vai para classificacao, com ela como revisora |

Valores de `AUTOR`, não carregada: 'Conselho Nacional de Assistência Social' (53).

### CONAMA → Conselho Nacional do Meio Ambiente

Cabeçalho na linha 2.

| Coluna na planilha | Campo | Destino | Por quê |
|---|---|---|---|
| `ID_VERSAO` | id_versao | ato.id_planilha | chave do ato na planilha, junto com o conselho (sql/003) |
| `ANO E DATA` | data | ato.data_publicacao | serial do Excel convertido; a planilha não diz se é a data de publicação ou de assinatura |
| `ANO` | ano | não carregado | redundante com a data; conferido, e a divergência vira aviso |
| `TEMA` | conteudo | ato.conteudo | texto do ato transcrito pela pesquisadora, inteiro ou em trecho |
| `DISP_LEG` | ref_legal | ato.ref_legal | como está na planilha; informativa, não é chave |
| `REFERENTE` | referente | não carregado | outro rótulo dela (a quem o ato se dirige); o esquema não tem onde guardar, fica no CSV normalizado |
| `TIPO Incidência (geral)` | tipologia | classificacao.tipologia_sigla | rótulo da pesquisadora, não atributo do ato: vai para classificacao, com ela como revisora |

### CONCIDADES → Conselho das Cidades

Cabeçalho na linha 1.

| Coluna na planilha | Campo | Destino | Por quê |
|---|---|---|---|
| `ID_VERSAO` | id_versao | ato.id_planilha | chave do ato na planilha, junto com o conselho (sql/003) |
| `ANO` | ano | não carregado | redundante com a data; conferido, e a divergência vira aviso |
| `DATA` | data | ato.data_publicacao | serial do Excel convertido; a planilha não diz se é a data de publicação ou de assinatura |
| `TEMA` | conteudo | ato.conteudo | texto do ato transcrito pela pesquisadora, inteiro ou em trecho |
| `DIS_LEG` | ref_legal | ato.ref_legal | como está na planilha; informativa, não é chave |
| `REF_EMI_CON` | emissao | não carregado | diz quem emitiu; os valores encontrados estão no relatório |
| `AUTOR` | autor | não carregado | a aba já identifica o conselho; os valores encontrados estão no relatório |
| `REFERENTE` | referente | não carregado | outro rótulo dela (a quem o ato se dirige); o esquema não tem onde guardar, fica no CSV normalizado |
| `TEMA_RESUM` | ementa | ato.ementa | resumo do ato escrito pela pesquisadora |
| `TIPOL_DECIS` | tipologia | classificacao.tipologia_sigla | rótulo da pesquisadora, não atributo do ato: vai para classificacao, com ela como revisora |

Valores de `AUTOR`, não carregada: 'Conselho das Cidades' (28).

Valores de `REF_EMI_CON`, não carregada: 'Emitida pelo conselho' (28).

### CONDRAF → Conselho Nacional de Desenvolvimento Rural Sustentável

Cabeçalho na linha 1.

| Coluna na planilha | Campo | Destino | Por quê |
|---|---|---|---|
| `ID_VERSAO` | id_versao | ato.id_planilha | chave do ato na planilha, junto com o conselho (sql/003) |
| `ANO` | ano | não carregado | redundante com a data; conferido, e a divergência vira aviso |
| `DATA` | data | ato.data_publicacao | serial do Excel convertido; a planilha não diz se é a data de publicação ou de assinatura |
| `TEMA` | ementa | ato.ementa | resumo do ato escrito pela pesquisadora |
| `DIS_LEG` | ref_legal | ato.ref_legal | como está na planilha; informativa, não é chave |
| `REF_EMI_CON` | emissao | não carregado | diz quem emitiu; os valores encontrados estão no relatório |
| `AUTOR` | autor | não carregado | a aba já identifica o conselho; os valores encontrados estão no relatório |
| `REFERENTE` | referente | não carregado | outro rótulo dela (a quem o ato se dirige); o esquema não tem onde guardar, fica no CSV normalizado |
| `TIPOL_DECIS` | tipologia | classificacao.tipologia_sigla | rótulo da pesquisadora, não atributo do ato: vai para classificacao, com ela como revisora |

Valores de `AUTOR`, não carregada: 'Conselho Nacional de Desenvolvimento Sustentável' (24).

Valores de `REF_EMI_CON`, não carregada: 'Emitida pelo conselho' (24).

### CNPIR → Conselho Nacional de Promoção da Igualdade Racial

Cabeçalho na linha 1.

| Coluna na planilha | Campo | Destino | Por quê |
|---|---|---|---|
| `ID_VERSAO` | id_versao | ato.id_planilha | chave do ato na planilha, junto com o conselho (sql/003) |
| `ANO` | ano | não carregado | redundante com a data; conferido, e a divergência vira aviso |
| `DATA (MÊS/DIA/ANO)` | data | ato.data_publicacao | serial do Excel convertido; a planilha não diz se é a data de publicação ou de assinatura |
| `TEMA` | conteudo | ato.conteudo | texto do ato transcrito pela pesquisadora, inteiro ou em trecho |
| `DIS_LEG (ATO/ANO)` | ref_legal | ato.ref_legal | como está na planilha; informativa, não é chave |
| `TIPOL_DECIS` | tipologia | classificacao.tipologia_sigla | rótulo da pesquisadora, não atributo do ato: vai para classificacao, com ela como revisora |
