# 0004 — A identidade de um conselho sai de uma chave normalizada mais decisões registradas, nunca de similaridade de texto

- **Status:** proposto
- **Data:** 2026-09-26
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

O indicador do projeto é **por conselho**: "este conselho está silencioso" só faz sentido se cada conselho for uma entidade só. Hoje não é. A aba "Conselhos mapeados no DOU" da planilha da pesquisadora tem **125 linhas**, e o mesmo conselho aparece com grafias diferentes e com nomes que mudaram por lei (issue #4). A professora não sabe o número: *"tem 90, tá 120, né?"*.

Este ADR decide **como** dois nomes viram o mesmo conselho, e como isso fica no OLTP. A execução da #4 (a tabela final, a migração e a carga) vem depois da validação deste ADR.

**O que a lista é** (medido em `docs/adr/medicoes/0004-identidade/`):

| Dimensão | Valor |
|---|---|
| Linhas | 125, uma coluna, sem data nem código |
| Origem | nomes copiados do DOU à mão. Duas linhas trazem o órgão pai colado sem a barra do `artCategory` ("...aos Delitos Ministério da Justiça e Segurança Pública", "...Extrativistas Instituto Chico Mendes...") |
| Nomes distintos, normalização do diário de 25/09 | 96 |
| Nomes distintos, chave normalizada (B, abaixo) | 95 |
| Grupos com mais de uma linha no gabarito | 32 |
| Grupos que a normalização não fecha | 7: 3 renomeações, 3 grafias com erro ou lixo colado, 1 com o nome truncado |
| Linhas que o código não resolve | 5: 2 genéricas ("Conselho Deliberativo", "Conselho de Ensino Pesquisa e Extensão") e 3 ambíguas |
| Siglas repetidas entre conselhos diferentes | CNE (Educação e Esporte) e CNT (Trabalho e Turismo): a sigla não serve de chave |

**Renomeações conferidas no texto da lei** (planalto.gov.br, 26/09):

| Nome antigo | Nome novo | Ato |
|---|---|---|
| Conselho de Defesa dos Direitos da Pessoa Humana | Conselho Nacional dos Direitos Humanos | Lei nº 12.986, de 2/6/2014, art. 1º: "passa a denominar-se" |
| Conselho Nacional dos Direitos do Idoso | Conselho Nacional dos Direitos da Pessoa Idosa | Decreto nº 9.893, de 27/6/2019: dispõe sobre o conselho já com o nome novo, sem "passa a denominar-se" |
| Conselho Nacional dos Direitos da Mulher | Conselho Nacional dos Direitos das Mulheres | Lei nº 7.353, de 29/8/1985, cria com "da Mulher"; o Decreto nº 11.351, de 1º/1/2023 (estrutura do Ministério das Mulheres), escreve "das Mulheres", sem "passa a denominar-se"; o SIORG já usa o nome novo |

E um caso que parece renomeação e pode não ser: o **Conselho Nacional de Fertilizantes e Nutrição de Plantas** foi *instituído* pelo Decreto nº 10.991, de 11/3/2022. Não achamos um "Conselho Nacional de Fertilizantes" anterior. As duas linhas podem ser o mesmo conselho (nome abreviado) ou dois órgãos.

**O que vem depois:** a #6 traz o DOU desde 2020, ~300 matérias por dia útil na Seção 1, cada uma com o nome do órgão emissor no `artCategory`. Nomes novos vão continuar chegando: renomeação de conselho, de ministério (o CONAMA muda de pai em 2023) e erro de digitação da Imprensa Nacional. A regra decidida aqui é a que vai casar esses nomes.

**O que tem que valer:**

- **R1** nenhuma fusão errada: juntar dois conselhos diferentes soma a produção de um ao outro, e o conselho silencioso desaparece do indicador. Deixar de juntar é menos grave, porque aparece como duplicata e se corrige.
- **R2** renomeação é **mudança legal com data**, não sinônimo: o ato de 2013 foi do CDDPH, o de 2015 do CNDH.
- **R3** toda linha aponta para um conselho ou está marcada como "indefinido", com o motivo (critério de aceite da #4).
- **R4** caso ambíguo não se resolve por código: vai para a squad ou para a pesquisadora.
- **R5** reproduzível, como o resto do projeto.

## Alternativas consideradas

### A. Opção nula: o nome literal é a identidade

Cada grafia é um conselho: 125 entidades. É o que existe hoje.

### B. Chave normalizada, automática

Remove o que não muda a identidade: caixa, acento, espaços e quebras de linha, sigla entre parênteses ou com hífen no fim. Duas linhas com a mesma chave são o mesmo conselho.

### C. B + similaridade de texto, automática

Junta nomes com similaridade acima de um limiar (`difflib.SequenceMatcher`, com agrupamento: basta um par parecido para juntar os grupos). É o que pega "de/do Meio Ambiente" e "da Mulher/das Mulheres". Medida em 4 limiares.

### D. O SIORG como cadastro canônico

O SIORG, o cadastro oficial de órgãos do Executivo federal, tem uma API pública, sem autenticação, com código estável por unidade. A identidade seria o código SIORG do nome casado. É também o candidato natural ao censo de conselhos, decisão em aberto nº 2 do `docs/adr/README.md`.

### E. B + decisões registradas (escolhida)

A chave B junta o que é certo. Todo o resto é uma **decisão escrita**, com tipo, motivo e fonte, num arquivo versionado que a squad revisa no PR:
- fusão de grafia;
- renomeação, com o ato legal e a data;
- "indefinido";
- "ambíguo", à espera de resposta.

## Medição

**Como reproduzir**, da raiz do repositório (só biblioteca padrão; baixa o SIORG, ~96 MB, uma vez para `data/interim/siorg/`, fora do git):

```bash
python3 docs/adr/medicoes/0004-identidade/bench.py
```

**Gabarito:** `docs/adr/medicoes/0004-identidade/gabarito.csv`. Cada uma das 125 linhas tem um grupo e um status: `certo` (120 linhas em 82 grupos), `ambiguo` (3) ou `indefinido` (2), com a nota do porquê. **É uma proposta, a validar no PR**: foi montado lendo as 125 linhas e conferindo as renomeações na lei.

**Métrica, por pares de linhas:** "certos" são os pares do mesmo grupo que a alternativa juntou; "faltou" são os pares do mesmo grupo que ela deixou separados (há 43 no gabarito); "errados" são os pares de grupos diferentes que ela juntou. Linhas ambíguas ficam fora da conta.

**Condição:** Python 3.14, Linux x86_64; SIORG consultado em 26/09/2026 (sha256 `555d2a05…`, 95.877 unidades, 2.010 delas colegiadas). A medição roda em ~2 s e é determinística.

| Alternativa | Entidades | Pares certos | Faltou juntar | **Fusões erradas** |
|---|---|---|---|---|
| A nome literal | 125 | 0 | 43 | 0 |
| B0 normalização do diário de 25/09 | 96 | 29 | 14 | 0 |
| B chave normalizada | 95 | 30 | 13 | 0 |
| C similaridade ≥ 0,95 | 93 | 34 | 9 | 0 |
| C similaridade ≥ 0,90 | 92 | 35 | 8 | 0 |
| C similaridade ≥ 0,85 | 84 | 36 | 7 | **19** |
| C similaridade ≥ 0,80 | 68 | 36 | 7 | **240** |
| D SIORG (código da unidade casada pela chave B) | 99 | 26 | 17 | 0 |
| **E** B + decisões registradas | 82 + 3 ambíguos | 43 | 0 | 0 |

A linha E é o gabarito por construção. O que se mede em E é o **custo**: 7 decisões de fusão, cada uma com a fonte, e 5 linhas levadas à squad.

**Onde a similaridade quebra.** Os pares que B não junta, com a similaridade de cada um:

| Par (mesmo conselho) | Similaridade |
|---|---|
| "de Meio Ambiente" × "do Meio Ambiente" | 0,97 |
| "da Mulher" × "das Mulheres" | 0,96 |
| Pirataria: "contra a" × "de" | 0,94 |
| **"Pessoa Idosa" × "do Idoso"** | **0,889** |
| CDDPH × CNDH (renomeação) | 0,67 |
| Pirataria com o ministério colado | 0,66 |
| Política Cultural com trecho da ementa colado | 0,61 |
| LGBTQIA+ × nome por extenso, truncado | 0,59 |

E os pares de **conselhos diferentes** mais parecidos:

| Par (conselhos diferentes) | Similaridade |
|---|---|
| **"Pessoa Idosa" × "Pessoas LGBTQIA+"** | **0,887** |
| Conselho Diretor do FNDCT × CNPq | 0,878 |
| Trânsito × Turismo | 0,877 |
| Política Energética × Política Fazendária | 0,875 |

**Leitura.**
- **Nenhum limiar serve.** O mesmo conselho renomeado (0,889) e dois conselhos diferentes (0,887) ficam a 0,002 de distância. Abaixo de 0,89 começam as fusões erradas, e com elas Assistência Social vira Previdência Social e Juventude vira Saúde. Acima, a similaridade só pega o que é quase idêntico, e as renomeações CDDPH → CNDH (0,67) e "do Idoso" → "Pessoa Idosa" (0,889) e as grafias com lixo colado (0,59 a 0,66) ficam de fora. Similaridade mede texto, e uma renomeação legal muda o texto de propósito.
- **O SIORG não serve de identidade.** Das 125 linhas, 95 casam com exatamente uma unidade (93 colegiadas), 68 dos 82 grupos ganham código, 28 linhas não casam com nada e 2 casam com várias. O que falta é justamente o que importa aqui: o SIORG só tem o nome **vigente**, então nomes antigos (CDDPH, "do Idoso", "da Mulher") não casam e as renomeações se partem; e ele não cobre o que não é do Executivo federal (Conselho da Justiça Federal) nem o que foi extinto. Com isso, D tem **mais** entidades que B (99 contra 95). Mas o SIORG serve como **evidência**. Ele confirmou que "Comitê-Executivo de Gestão" é uma unidade só (o GECEX) e que "Conselho de Ensino Pesquisa e Extensão" é um nome genérico: há mais de 200 unidades colegiadas com esse nome ou quase, uma por universidade ou instituto.
- **B é seguro e insuficiente:** 0 fusões erradas, mas faltam 13 pares, entre eles os das três renomeações.

## Decisão

1. **A identidade sai da chave normalizada (B) mais decisões registradas (E).** B junta automaticamente. Toda fusão além dela é uma linha num arquivo versionado de decisões, com o tipo (`grafia`, `renomeacao`, `indefinido`, `ambiguo`), o motivo e a fonte. **A similaridade de texto nunca decide.** Ela pode ordenar candidatos para alguém revisar.
2. **Renomeação vai para `orgao_nome`, com vigência**, como o ADR 0001 previu: o nome antigo ganha `data_fim` e o novo `data_inicio` na data do ato legal. Só entra como renomeação o que tiver o ato conferido.
3. **Grafia vai para uma tabela nova, `orgao_alias`**: o nome como foi visto, a chave, a fonte (a planilha, e depois o DOU) e o `orgao_id`. Não tem vigência, porque grafia não é mudança legal. Linha "indefinido" entra em `orgao_alias` com `orgao_id` nulo e o motivo, então ela aparece, e não some.
4. **`orgao_nome.data_inicio` passa a aceitar nulo, com o significado "data não verificada"** (migração nova). Dos 82 órgãos, só têm hoje a data de um ato conferida os 5 da #3 e os das renomeações acima. Inventar uma data fixa, como 01/01/1900, seria gravar um dado falso. Deixar de fora quem não tem data tiraria do cadastro justamente os conselhos que ninguém pesquisou.
5. **O código SIORG é guardado quando o casamento é único**, como vínculo externo e não como identidade. Ele serve à decisão do censo (em aberto nº 2) sem que a identidade dependa dele.
6. **Os canônicos entram como `orgao`, não como `conselho`.** Decidir quais deles são objeto da pesquisa (`conselho.eh_participativo`) não é identidade: a lista tem a CVM, o Conselho Monetário Nacional e o CNJ. Isso fica com a pesquisadora. Os 5 conselhos da #3 continuam como estão.

**Número de conselhos distintos:** **82** com certeza, e **até 85** conforme se resolverem as 3 ambiguidades (Fertilizantes: 1 ou 2 órgãos; Populações Extrativistas: órgão de governo ou não). As 2 linhas indefinidas não entram na conta. É a primeira resposta com justificativa ao *"tem 90, tá 120"*.

## Consequências

**O que ganhamos:**
- **Zero fusões erradas** por construção: a única coisa automática é B, que não errou nenhuma. O indicador não esconde um conselho dentro de outro.
- **Toda fusão é auditável:** quem abrir o arquivo de decisões sabe por que duas linhas são o mesmo conselho e de onde veio a data.
- **A série histórica atravessa a renomeação:** os atos do CDDPH e do CNDH somam no mesmo órgão, e cada um fica com o nome da época.
- **Nome novo do DOU não é engolido em silêncio.** Se a chave dele já existe, casa; se não, vai para a fila de decisão.

**O que perdemos:**
- **Trabalho humano que não acaba.** Cada nome novo do DOU que B não reconhece espera alguém decidir. Com ~300 matérias por dia útil, o tamanho dessa fila **não foi medido** (depende da #6).
- **Um arquivo de decisões para manter**, que a pesquisadora precisa conseguir ler e corrigir, além da tabela nova `orgao_alias`.
- **`data_inicio` nulo muda o contrato de `orgao_nome`.** Toda consulta por vigência (`data_inicio <= x`) precisa tratar o nulo, e quem esquecer perde esses órgãos da consulta sem erro.
- **O gabarito e as decisões são nossos**, feitos por quem não é especialista, até a pesquisadora revisar. Um erro nosso ali vira uma fusão errada que o código não tem como pegar.
- **O SIORG vira uma dependência a mais**, de um arquivo de 96 MB que muda com o tempo. Guardamos o sha256 e a data da consulta, mas o casamento pode mudar entre duas consultas.

**O que se torna irreversível:** nada. Uma decisão errada se desfaz com uma linha nova no arquivo; `orgao_alias` e a coluna do SIORG saem com uma migração; e `data_inicio` volta a ser obrigatório quando todas as datas forem conferidas.

## Em aberto (a comentar na issue #4)

- **Conselho Nacional de Fertilizantes** × **Conselho Nacional de Fertilizantes e Nutrição de Plantas** (instituído em 2022): um órgão ou dois?
- **"Conselho Nacional das Populações Extrativistas Instituto Chico Mendes..."**: é o CNS, organização da sociedade civil (antigo Conselho Nacional dos Seringueiros), citado em ato do ICMBio? Se for, não é órgão de governo.
- **"Conselho Deliberativo"** e **"Conselho de Ensino Pesquisa e Extensão"**: de qual órgão? Sem isso, ficam indefinidos.
- **"da Mulher" → "das Mulheres"**: qual é a data? Nenhum ato achado diz "passa a denominar-se".
- **CNPq** está na lista, mas é fundação, não colegiado. Fica como órgão, e o `eh_participativo` é da pesquisadora.

## Gatilho de revisão

- **A #6 medir a fila de nomes novos:** se mais de ~20 nomes novos por mês pedirem decisão, reavaliar C como sugestão ordenada na tela de curadoria, ainda sem decidir sozinha.
- **O ADR do censo (em aberto nº 2) adotar o SIORG:** o código SIORG pode virar a chave dos órgãos vigentes, com as decisões registradas cobrindo só o histórico.
- **A pesquisadora corrigir o gabarito:** refazer a medição; se alguma fusão de B se mostrar errada, B deixa de ser automática para aquele padrão.
- **Todas as datas de criação forem conferidas:** voltar `orgao_nome.data_inicio` para `NOT NULL`.
