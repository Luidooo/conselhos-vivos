# Amostras do `article`

| Arquivo | Origem |
|---|---|
| `515_20190507_11615606.xml` | Real: matéria da DO1 de 07/05/2019, copiada sem alteração de [viniciusrpb/xml2csv_diariooficialdauniao](https://github.com/viniciusrpb/xml2csv_diariooficialdauniao/tree/master/dou_samples). Mantém o BOM UTF-8 e o CRLF do original |
| `529_20210601_13490090.xml` | Real: matéria da DO2 de 01/06/2021, mesma origem e mesmas condições |
| `conselho-construido.xml` | **Construída** à mão no formato das reais, porque nenhuma amostra pública é de conselho. Os ids começam em 900000000 para não colidir com um id do DOU, e a ementa diz que ela não foi publicada. Cobre o que as reais não cobrem: conselho no último nível do `artCategory`, `editionNumber` de edição extra, `Ementa` preenchida, tabela, `<br/>` e entidade HTML |
| `malformado.xml` | Construída: XML cortado no meio, para o caso de erro |

Atos oficiais não têm proteção de direito autoral (Lei 9.610/1998, art. 8º, IV), e
as matérias reais já são públicas no DOU.
