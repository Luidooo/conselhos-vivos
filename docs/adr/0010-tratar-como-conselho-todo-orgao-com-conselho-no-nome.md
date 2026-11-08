# 0010 — É conselho todo órgão que tem ou já teve "Conselho" no nome; a marca de participação social fica à parte

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
3. **`conselho.eh_participativo` continua sendo a marca de participação social, e continua com a pesquisadora.** A dimensão expõe a coluna `eh_participativo`: verdadeiro para os 5 da planilha e nulo, "não avaliado", para os demais. Nulo não é falso. O painel decide se filtra.
4. **Início de vigência desconhecido vira limite aberto na dimensão, não no OLTP.** O ADR 0004 (ponto 4) deixa `orgao_nome.data_inicio` nulo quando a data não foi verificada, e isso vale para a maioria dos órgãos. Em `dim_conselho`, `valido_de` passa a `0001-01-01` e a coluna `inicio_nao_verificado` marca a linha. Sem isso, o fato do ato, que casa `data_publicacao` com a vigência, descartaria sem erro os atos desses conselhos.

## Consequências

**O que ganhamos:**
- A dimensão cobre o escopo do projeto, e o CNDPI, o CNDM e o CNDH dão a variação lenta com dado real.
- A regra é uma linha de SQL, visível e fácil de trocar.

**O que perdemos:**
- Entram conselhos que não são de participação social (CNJ, Conselho Monetário Nacional, Conselho da Justiça Federal). Enquanto `eh_participativo` for nulo, uma conta "de participação social" precisa filtrar por ele.
- Um conselho cujo nome não comece com "Conselho" (um "Colegiado" ou uma "Câmara" que na prática é conselho) fica de fora até alguém decidir.
- O fato do ato e o painel da E3 passam de 5 conselhos para 62. O volume e o resultado mudam, e é a consequência esperada.
- Nomes genéricos (por exemplo "Conselho de Ensino Pesquisa e Extensão") dependem das decisões que o ADR 0004 deixou em aberto.

**O que se torna irreversível:** nada. A regra é um filtro no modelo. Voltar para os 5 é trocar o filtro.

## Gatilho de revisão

- **A pesquisadora ou a squad apontarem um conselho que a regra deixa de fora, ou um órgão que entra e não é conselho:** trocar a regra por uma lista de decisões, como o ADR 0004 faz com a identidade.
- **A pesquisadora preencher `eh_participativo` para os demais:** o painel pode passar a filtrar por ele sem tratar nulo.
