# EXPLAIN da extração do lake (#74)

Consulta: `QUERY_OLTP` de `src/lake/sync.py` (`make lake` e `make cdc`), `ato_ids = NULL`.
Plano completo em `explain-antes.txt`; reproduza com `bash docs/adr/medicoes/0009-gold/explain.sh`.

Volume medido: 311 atos, 262 classificações, 85 nomes de órgão, 82 órgãos.

## Antes

Execution Time 22,8 ms numa execução (`explain-antes.txt`), `shared hit=1392 read=37`. Nas medições abaixo, o melhor de 5 fica em ~20 ms.

O nó mais caro em buffers é o `Seq Scan on classificacao` dentro do LATERAL da classificação vigente:
930 dos 1.386 buffers, repetido 311 vezes (um por ato). O `orgao_nome` custa 2 buffers por scan; não é o alvo.

## Índice testado: `orgao_nome (orgao_id, data_inicio, data_fim)`

O candidato do plano, aplicado numa transação desfeita pelo `testar-indice.sh` (melhor de 5 execuções; a variação entre rodadas é de alguns ms, e a de `seqscan off` é bem maior):

| Cenário | Execution Time |
|---|---|
| sem índice | 20,8 ms |
| com o índice | 20,8 ms (o planner não o usa) |
| com o índice, `enable_seqscan = off` | 298 ms (~15× pior) |

**Sem ganho: o índice não entra, não há migração `007`.**

## Por que, e o que fazer depois

- As tabelas são minúsculas: `orgao_nome` ocupa 2 páginas e `classificacao` 3 (`ato`, a maior, 32). Nesse tamanho o Seq Scan é mais barato que qualquer índice, e o planner está certo.
- O alvo real, a busca em `classificacao` por `ato_id`, **já tem** índice: `ix_classificacao_recente (ato_id, revisor_id, criado_em DESC, id DESC)`. Ele deve passar a ser usado quando a tabela crescer; não há o que criar.
- Remedir com o volume do backfill (#73), rodando `explain.sh` de novo. Se o `Seq Scan on classificacao` continuar com muitos milhares de linhas, o problema deixa de ser índice e passa a ser reescrever o LATERAL.
- Este resultado vai para o ADR 0009 (#76).

`tests/db/test_schema.sh` roda em `OK` nesta branch (não há migração nova).
