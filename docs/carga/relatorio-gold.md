# Gold e menções (E3)

O que a camada analítica da E3 tem dentro, medido em 09/11/2026 com o DOU de julho a setembro de 2026 na silver e a planilha da pesquisadora. As menções de outros órgãos cobrem de julho a outubro, porque o ZIP de outubro já estava no bronze. Cada número tem a prova em `docs/adr/medicoes/0009-gold/`.

## Resumo

| O que | Quanto | Prova |
|---|---|---|
| Conselhos no escopo ([ADR 0010](/docs/adr/0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome)) | 59 | [vitalidade-por-situacao.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/vitalidade-por-situacao.txt) |
| Ativos | 26 | idem |
| Sem ato no período coberto | 33 | idem |
| Matérias no `fct_ato` (uma por matéria) | 458 | [granularidade.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/granularidade.txt) |
| Linhas no `fct_conselho_mes` (conselho × mês) | 177 | idem |
| Menções de outros órgãos, julho a outubro | 139 | [mencoes-carga.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/mencoes-carga.txt) |
| Conselhos sem ato próprio que outros órgãos citam | 10 de 33 | idem |
| Testes do dbt | 77 de 77 em `PASS` | idem |

## A granularidade

O grão diário teria 5.428 linhas, quase todas vazias, contra 177 no grão mensal ([granularidade.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/granularidade.txt)). O fato mensal ficou no mês porque o SLA e o limite de silêncio também se contam em meses ([ADR 0009](/docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster)).

## As menções

O nome do conselho é procurado só no título, na ementa, na identificação e nos primeiros 600 caracteres do texto. No texto inteiro, 471 matérias citariam algum conselho, quase sempre numa lista de referências. Na janela curta são 136 ([mencoes-janela.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/mencoes-janela.txt)). A matéria publicada pelo próprio conselho não conta, em qualquer nível da hierarquia do órgão.

| Situação | Conselhos | Citados por outros | Menções |
|---|---|---|---|
| ativo | 26 | 7 | 61 |
| sem ato no período coberto | 33 | 10 | 47 |

O mais citado sem ato próprio é o CNE, com 28 menções. Rodar a carga de novo dá `inseridas=0 atualizadas=0 inalteradas=139`.

## O que os testes e as conferências mostram

- **O mês que some.** Tirar agosto da carga faz o teste de distribuição falhar: nenhum mês coberto pelo DOU pode ficar sem ato ([teste-distribuicao-pega-o-mes.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/teste-distribuicao-pega-o-mes.txt)).
- **O DOU vazio.** Sem nenhum mês carregado, como num clone limpo, ninguém fica "em silêncio" e o SLA acusa atraso em vez de passar. Os dois casos têm teste unitário em `dbt/models/marts/marts.yml`.
- **A tipologia fora da lista.** Se mais de 20% dos atos classificados caírem fora da tipologia, o teste falha. A prova baixa o limite a zero para mostrar a falha ([teste-distribuicao-fora-da-tipologia.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/teste-distribuicao-fora-da-tipologia.txt)).
- **O que fica fora do escopo.** A lista dos atos de órgãos fora da dimensão, que não entram no fato ([fct_ato-fora-do-escopo.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/fct_ato-fora-do-escopo.txt)).
- **O nome da época.** Um conselho renomeado aparece com o nome que valia na data do ato ([dim_conselho-renomeados.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/dim_conselho-renomeados.txt)).
- **O SLA atrasado.** Ele avisa sem travar o build ([sla-vitalidade-avisa.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/sla-vitalidade-avisa.txt)).

## Pendências

- **O limite de três meses para "ativo" é provisório.** Com só três meses cobertos, nenhum conselho pode ficar em silêncio, então a contagem ainda não testa o limite. A pesquisadora define o valor.
- **Siglas repetidas.** CNE e CNPC aparecem duas vezes cada, em órgãos diferentes. A sigla não serve de chave; o painel usa o `orgao_id`.
- **O escopo do ADR 0010 traz órgãos que não são de participação social.** O CNPq, o CONTRAN e o CCFGTS entram porque o nome começa com "Conselho". O painel mostra a marca `eh_participativo` da pesquisadora ao lado, sem filtrar, e a lista de exclusões aguarda a squad.
- **Os rótulos mudam com outubro.** Quando o ZIP de outubro entrar na silver, parte dos 33 "sem ato no período coberto" vai mudar de situação.
