# Identidade dos conselhos

> Gerado por `make carga` (`python -m conselhos relatorio`); não editar à mão. As mesmas entradas geram este mesmo arquivo. Decisão de método: [ADR 0004](../adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md).

- **Planilha:** `data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx` · sha256 `635b3f0a6580fff358171b830b13ef2a2ccd2945f0f2d05a7e0c178964c7d347`
- **Decisões:** `data/referencia/conselhos-decisoes.csv` · sha256 `fad1d40f59bbba5fc834b5915b6aafc62e45b2709e0b1a6d2de6f3a257033ea8`
- **Recorte do SIORG:** `data/referencia/siorg-conselhos.csv` · sha256 `7f801e4c45eab71f4d033145ac49f2847d0591fbb122527ed96d236614f18a0d`
- **SIORG:** consultado em 2026-09-26, 95.877 unidades, sha256 `555d2a057afde4ad483dbf4ba8551431ee63a59986d8d7a0abcda637787e860a`

## Resumo

**82 conselhos distintos** nas 125 linhas da aba "Conselhos mapeados no DOU", e até **85** se cada nome ambíguo se mostrar um órgão próprio.

| Linhas | Situação |
|---|---|
| 120 | apontam para um órgão |
| 2 | indefinidas: nome genérico, sem como saber o órgão |
| 3 | ambíguas: à espera de decisão da squad ou da pesquisadora |
| **125** | toda linha tem um órgão ou está marcada, com o motivo |

## Como se chega ao número

| Passo | Nomes | Por quê |
|---|---|---|
| Linhas da aba | 125 | cada grafia conta como um nome |
| Chave normalizada | 95 | junta o que só difere em caixa, acento, espaços, quebra de linha e sigla no fim |
| Sem as pendências | 90 | 5 chaves indefinidas ou ambíguas saem da conta |
| Decisões de grafia e renomeação | **82** | 8 chaves juntadas a outra por decisão registrada, abaixo |

## Renomeações

Nome antigo em `orgao_nome`, com a vigência fechada no dia anterior ao ato; o nome novo vale a partir do ato.

| Órgão (nome vigente) | Nome antigo | Início do nome antigo | Fim | Ato |
|---|---|---|---|---|
| Conselho Nacional dos Direitos Humanos | Conselho de Defesa dos Direitos da Pessoa Humana | 16/03/1964 | 01/06/2014 | Lei nº 12.986, de 2/6/2014, art. 1º |
| Conselho Nacional dos Direitos da Pessoa Idosa | Conselho Nacional dos Direitos do Idoso | não verificada | 26/06/2019 | Decreto nº 9.893, de 27/6/2019 |
| Conselho Nacional dos Direitos das Mulheres | Conselho Nacional dos Direitos da Mulher | 29/08/1985 | 31/12/2022 | Decreto nº 11.351, de 1º/1/2023 |

## Grafias juntadas por decisão

Nomes que a chave não junta e que uma decisão registrada junta. As grafias que só diferem em caixa, acento ou sigla estão na tabela de órgãos.

| Linha | Nome na planilha | Órgão | Motivo |
|---|---|---|---|
| 54 | Conselho Nacional de Combate à Pirataria e aos Delitos Ministério da Justiça e Segurança Pública | Conselho Nacional de Combate à Pirataria e Delitos contra a Propriedade Intelectual | nome truncado seguido do ministério (artCategory sem a barra) |
| 55 | Conselho Nacional de Combate à Pirataria e Delitos de Propriedade Intelectual | Conselho Nacional de Combate à Pirataria e Delitos contra a Propriedade Intelectual | "de" no lugar de "contra a" |
| 77 | Conselho Nacional de Meio Ambiente | Conselho Nacional do Meio Ambiente | "de" no lugar de "do" |
| 83 | Conselho Nacional de Política Cultural a regulamentação do Sistema Nacional de Cultura | Conselho Nacional de Política Cultural | nome seguido de trecho da ementa |
| 120 | Conselho Nacional dos Direitos das Pessoas Lésbicas, Gays, Bissexuais, Travestis, Trans., Queers, Intersexos, | Conselho Nacional dos Direitos das Pessoas LGBTQIA+ | nome por extenso e truncado |

## Pendências

Entram em `orgao_alias` sem órgão, com o motivo. Resolvida a dúvida, a decisão muda no CSV e a próxima carga aponta o alias para o órgão.

| Linha | Nome na planilha | Situação | Motivo |
|---|---|---|---|
| 28 | Conselho de Ensino Pesquisa e Extensão | indefinido | nome genérico: há mais de 200 unidades colegiadas no SIORG com esse nome ou quase (uma por universidade ou instituto) |
| 33 | Conselho Deliberativo | indefinido | nome genérico: 9 unidades no SIORG com esse nome; falta o órgão a que pertence |
| 44 | Conselho Nacional das Populações Extrativistas Instituto Chico Mendes de Conservação da Biodiversidade | ambiguo | nome seguido do ICMBio (artCategory sem a barra); pode ser o CNS, organização da sociedade civil (antigo Conselho Nacional dos Seringueiros); sem unidade no SIORG |
| 68 | CONSELHO NACIONAL DE FERTILIZANTES | ambiguo | o Conselho Nacional de Fertilizantes e Nutrição de Plantas foi instituído pelo Decreto nº 10.991, de 11/3/2022; não achamos um conselho anterior com este nome: o mesmo órgão abreviado ou outro? |
| 69 | CONSELHO NACIONAL DE FERTILIZANTES E NUTRIÇÃO DE PLANTAS | ambiguo | par da linha 68: fica pendente junto, para não criar um órgão que depois precise ser fundido |

## Órgãos

68 dos 82 órgãos têm código SIORG. O nome vigente vem do SIORG quando a chave casa com uma unidade só; senão, da decisão "nome" no CSV. "Nome vigente desde" vem das renomeações e das decisões; os 5 conselhos da #3 têm a data de criação no `sql/004`, que a carga não altera.

| Órgão | Sigla | SIORG | Nome vigente desde | Linhas da planilha |
|---|---|---|---|---|
| Comissão Especial sobre Mortos e Desaparecidos Políticos | CEMDP | 104323 | não verificada | 5 |
| Comissão Nacional de Agroecologia e Produção Orgânica | CNAPO | 123834 | não verificada | 6 |
| Comissão Nacional de Erradicação do Trabalho Escravo | CONATRAE | 104359 | não verificada | 7 |
| Comissão Nacional de População e Desenvolvimento | CNPD | — | não verificada | 8, 9 |
| Comissão Nacional para REDD+ | CONAREDD | 214704 | não verificada | 10 |
| Comissão Tripartite Paritária Permanente | CTPP | 244832 | não verificada | 11 |
| Comissão de Objetivos do Desenvolvimento Sustentável | CNODS | — | não verificada | 3 |
| Comissão de Valores Mobiliários | CVM | 478 | não verificada | 4 |
| Comitê Executivo do CITDigital | CE-CITDigital | 453349 | não verificada | 12 |
| Comitê Gestor da CPR Furnas | — | — | não verificada | 13 |
| Comitê Gestor da CPR São Francisco e Parnaíba | — | — | não verificada | 14 |
| Comitê Gestor do Fundo Nacional sobre Mudança do Clima | FNMC | 7201 | não verificada | 15 |
| Comitê Gestor do Sistema Nacional de Informações de Registro Civil | CGSirc | 244907 | não verificada | 16 |
| Comitê Interministerial da Política Pública de Juventude | — | — | não verificada | 17 |
| Comitê Intersetorial de Acompanhamento e Monitoramento da Política Nacional para População em Situação de Rua | CIAMPNPSR | 105374 | não verificada | 18 |
| Comitê Nacional de Manejo Integrado do Fogo | CNMIF | 430709 | não verificada | 19 |
| Comitê Nacional para os Refugiados | CONARE | — | não verificada | 20 |
| Comitê-Executivo de Gestão | GECEX | 10146 | não verificada | 21 |
| Conselho Curador do FGTS | CCFGTS | — | não verificada | 22 |
| Conselho Curador do Fundo de Desenvolvimento Social | CCFDS | 14463 | não verificada | 23 |
| Conselho Deliberativo do Desenvolvimento do Centro-Oeste | CONDEL | 115628 | não verificada | 34 |
| Conselho Deliberativo do Fundo Nacional do Meio Ambiente | CDFNMA | 1992 | não verificada | 35, 37 |
| Conselho Deliberativo do Fundo de Amparo ao Trabalhador | CODEFAT | 2761 | não verificada | 36 |
| Conselho Diretor do Fundo Nacional de Desenvolvimento Científico e Tecnológico | CDFNDCT | 94467 | não verificada | 39 |
| Conselho Diretor do Fundo da Marinha Mercante | CDFMM | 92769 | não verificada | 38 |
| Conselho Federal Gestor do Fundo de Defesa dos Direitos Difusos | CFDD | 8156 | não verificada | 40 |
| Conselho Gestor do Fundo Nacional de Habitação de Interesse Social | CGFNHIS | 89595 | não verificada | 42 |
| Conselho Gestor do Fundo de Universalização dos Serviços de Telecomunicações | CGFust | 315393 | não verificada | 41 |
| Conselho Monetário Nacional | CMN | 82 | não verificada | 43 |
| Conselho Nacional das Zonas de Processamento de Exportação | CZPE | 1781 | não verificada | 45, 46 |
| Conselho Nacional de Aquicultura e Pesca | CONAPE | 77695 | não verificada | 47 |
| Conselho Nacional de Arquivos | CONARQ | 2159 | não verificada | 48 |
| Conselho Nacional de Assistência Social | CNAS | 4402 | não verificada | 49, 50 |
| Conselho Nacional de Ciência e Tecnologia | CCT | 9 | não verificada | 51, 52 |
| Conselho Nacional de Combate à Pirataria e Delitos contra a Propriedade Intelectual | CNCP | 79693 | não verificada | 53, 54, 55 |
| Conselho Nacional de Controle de Experimentação Animal | CONCEA | 103225 | não verificada | 56, 57 |
| Conselho Nacional de Desenvolvimento Científico e Tecnológico | CNPq | 8 | não verificada | 60 |
| Conselho Nacional de Desenvolvimento Econômico e Social Sustentável | — | — | não verificada | 61 |
| Conselho Nacional de Desenvolvimento Industrial | CNDI | 315997 | não verificada | 58, 62 |
| Conselho Nacional de Desenvolvimento Rural Sustentável | CONDRAF | 44396 | não verificada | 59, 63 |
| Conselho Nacional de Economia Solidária | CNES | 77694 | não verificada | 64, 65 |
| Conselho Nacional de Educação | CNE | 248 | não verificada | 66, 67 |
| Conselho Nacional de Fomento e Colaboração | CONFOCO | — | não verificada | 70, 71 |
| Conselho Nacional de Imigração | CNIg | 2766 | não verificada | 72, 73 |
| Conselho Nacional de Justiça | — | — | não verificada | 74 |
| Conselho Nacional de Juventude | CONJUVE | — | não verificada | 75, 76 |
| Conselho Nacional de Metrologia, Normalização e Qualidade Industrial | CONMETRO | 230 | não verificada | 78 |
| Conselho Nacional de Política Criminal e Penitenciária | CNPCP | 320 | não verificada | 79, 80 |
| Conselho Nacional de Política Cultural | CNPC | 1942 | não verificada | 81, 82, 83 |
| Conselho Nacional de Política Energética | CNPE | 25276 | não verificada | 84, 85 |
| Conselho Nacional de Política Fazendária | CONFAZ/MF | 87 | não verificada | 86 |
| Conselho Nacional de Política Indigenísta | CNPI | 229192 | não verificada | 87, 88 |
| Conselho Nacional de Políticas sobre Drogas | CONAD | 954 | não verificada | 89 |
| Conselho Nacional de Previdência Complementar | CNPC | 2042 | não verificada | 90 |
| Conselho Nacional de Previdência Social | CNPS | 2764 | não verificada | 91 |
| Conselho Nacional de Promoção da Igualdade Racial | CNPIR | 73242 | não verificada | 92 |
| Conselho Nacional de Proteção de Dados Pessoais e da Privacidade | CNPDPP | 241790 | não verificada | 93 |
| Conselho Nacional de Recursos Hídricos | CNRH | 23448 | não verificada | 94, 95 |
| Conselho Nacional de Saúde | CNS-MS | 306 | não verificada | 96, 97 |
| Conselho Nacional de Segurança Alimentar e Nutricional | CONSEA | 309010 | não verificada | 98, 100 |
| Conselho Nacional de Segurança Pública e Defesa Social | CNSP | 241963 | não verificada | 99, 101 |
| Conselho Nacional de Trânsito | CONTRAN | 321 | não verificada | 102 |
| Conselho Nacional de Turismo | CNT | 57612 | não verificada | 103, 104 |
| Conselho Nacional do Esporte | CNE | 47637 | não verificada | 105, 106 |
| Conselho Nacional do Meio Ambiente | CONAMA | 1023 | não verificada | 77, 107, 108 |
| Conselho Nacional do Serviço Social do Transporte | — | — | não verificada | 109 |
| Conselho Nacional do Trabalho | CNT | 110122 | não verificada | 110 |
| Conselho Nacional dos Direitos Humanos | CNDH | 319 | 02/06/2014 | 27, 123 |
| Conselho Nacional dos Direitos da Criança e do Adolescente | CONANDA | 3319 | não verificada | 112, 114 |
| Conselho Nacional dos Direitos da Pessoa Idosa | CNDPI | 68554 | 27/06/2019 | 118, 122 |
| Conselho Nacional dos Direitos da Pessoa com Deficiência | CONADE | 41036 | não verificada | 113, 117 |
| Conselho Nacional dos Direitos das Mulheres | CNDM | 1557 | 01/01/2023 | 115, 116, 119 |
| Conselho Nacional dos Direitos das Pessoas LGBTQIA+ | CNLGBTQIA+ | 318150 | não verificada | 111, 120, 121 |
| Conselho Nacional dos Povos e Comunidades Tradicionais | CNPCT | 214387 | não verificada | 124 |
| Conselho Nacional dos Regimes Próprios de Previdência Social | CNRPPS | 271532 | não verificada | 125 |
| Conselho da Justiça Federal | — | — | não verificada | 24 |
| Conselho das Cidades | ConCidades | 308752 | não verificada | 25, 26 |
| Conselho de Gestão do Patrimônio Genético | CGen | 55959 | não verificada | 29 |
| Conselho de Participação Social | CPS | — | não verificada | 30 |
| Conselho de Transparência, Integridade e Combate à Corrupção | CTICC | 74902 | não verificada | 31, 32 |
| Câmara Interministerial de Segurança Alimentar e Nutricional | CAISAN | 218801 | não verificada | 1 |
| Câmara-Executiva Federal de Identificação do Cidadão | CEFIC | 317766 | não verificada | 2 |
