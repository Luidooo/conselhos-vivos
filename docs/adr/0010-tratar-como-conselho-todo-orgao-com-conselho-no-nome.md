# 0010 — É conselho todo órgão que já teve um nome começando com "Conselho", menos uma lista curta de exclusões; a marca de participação social fica à parte

- **Status:** proposto
- **Data:** 2026-11-08
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)
- **Revisa:** o ponto 6 do [ADR 0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md). O resto do 0004 continua valendo.

## Contexto

O ponto 6 do ADR 0004 manteve a tabela `conselho` com os 5 conselhos da planilha da pesquisadora e deixou com ela a decisão de quais outros órgãos são objeto da pesquisa. Na E3 (issue #69), a dimensão `dim_conselho` foi construída sobre essa tabela e ficou com 5 linhas, nenhuma com mais de um nome. Os três órgãos que o ADR 0004 registra como renomeados (CNDPI, CNDM e CNDH) são conselhos de verdade, mas ficaram de fora, porque a pesquisadora não os incluiu na planilha.

O objetivo do projeto é cobrir **todos** os conselhos, não só os 5 que a pesquisadora anotou. A planilha foi um recorte de carga inicial (ADR 0001), não a definição do escopo.

## Decisão

1. **É conselho todo órgão que tem ou já teve um nome começando com "Conselho".** A regra vale por órgão, não por linha de `orgao_nome`: um conselho que mudasse para outro tipo de nome não perderia metade do histórico. Hoje são 62 dos 82 órgãos do OLTP. Câmaras, Comissões e Comitês ficam de fora.
2. **A regra mora em `dim_conselho` (dbt), não numa cópia na tabela `conselho`.** Um órgão novo que chegue do DOU entra na dimensão sem migração.
3. **Uma lista curta de exclusões conhecidas fica de fora, registrada como decisão.** São os órgãos com "Conselho" no nome que não são colegiados de participação social: Conselho da Justiça Federal, Conselho Monetário Nacional e Conselho Nacional de Justiça. A lista é a seed `dbt/seeds/conselhos_excluidos.csv`, com o nome e o motivo de cada um, e a chave é o nome, não o `orgao_id`, que depende da ordem da carga. Com ela a dimensão fica com 59 conselhos. Sem a lista, o único jeito de separá-los seria o `eh_participativo` nulo, que também é o estado dos conselhos reais ainda não avaliados, e o painel teria de escolher entre listar o Conselho Monetário Nacional e perder esses conselhos. Quem entra na lista é decisão da squad, com a pesquisadora.
4. **`conselho.eh_participativo` continua sendo a marca de participação social, e continua com a pesquisadora.** A dimensão expõe a coluna `eh_participativo`: verdadeiro para os 5 da planilha e nulo, "não avaliado", para os demais. Nulo não é falso. O painel decide se filtra.
5. **Início de vigência desconhecido vira limite aberto na dimensão, não no OLTP.** O ADR 0004 (ponto 4) deixa `orgao_nome.data_inicio` nulo quando a data não foi verificada, e isso vale para a maioria dos órgãos. Em `dim_conselho`, `valido_de` passa a `0001-01-01` e a coluna `inicio_nao_verificado` marca a linha. Sem isso, o fato do ato, que casa `data_publicacao` com a vigência, descartaria sem erro os atos desses conselhos.

## Consequências

**O que ganhamos:**
- A dimensão cobre o escopo do projeto, e o CNDPI, o CNDM e o CNDH dão a variação lenta com dado real.
- A regra é uma linha de SQL, visível e fácil de trocar.

**O que perdemos:**
- Enquanto `eh_participativo` for nulo para 54 dos 59 conselhos, uma conta "de participação social" não pode filtrar por ele. A lista de exclusões tira os que sabemos que não são, e os demais continuam por avaliar.
- A lista de exclusões é mantida à mão: um órgão com "Conselho" no nome que não seja de participação social entra na dimensão até alguém acrescentá-lo.
- Um conselho cujo nome não comece com "Conselho" (um "Colegiado" ou uma "Câmara" que na prática é conselho) fica de fora até alguém decidir.
- O fato do ato e o painel da E3 passam de 5 conselhos para 62. O volume e o resultado mudam, e é a consequência esperada.
- Nomes genéricos (por exemplo "Conselho de Ensino Pesquisa e Extensão") dependem das decisões que o ADR 0004 deixou em aberto.

**O que se torna irreversível:** nada. A regra é um filtro no modelo. Voltar para os 5 é trocar o filtro.

## Gatilho de revisão

- **A pesquisadora ou a squad apontarem um conselho que a regra deixa de fora, ou a lista de exclusões passar de uma dezena de nomes:** trocar a regra por uma lista de decisões, como o ADR 0004 faz com a identidade.
- **A pesquisadora preencher `eh_participativo` para os demais:** o painel pode passar a filtrar por ele sem tratar nulo.
