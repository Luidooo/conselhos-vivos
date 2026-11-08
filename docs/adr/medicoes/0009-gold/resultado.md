# EXPLAIN da extração do lake (#74)

Consulta: `QUERY_OLTP` de `src/lake/sync.py`, usada pelo `make lake` (`ato_ids = NULL`) e pelo `make cdc` (`a.id = ANY(...)`).
Os planos estão neste diretório; reproduza com `explain.sh` e `testar-indice.sh`.

Volume medido: 311 atos, 262 classificações, 85 nomes de órgão, 82 órgãos. **Com esse volume nenhum índice ganha de um Seq Scan, então este resultado vale para este volume.** Ele precisa ser refeito com o backfill (#73).
O banco de trabalho de cada pessoa difere (outro banco deu 224 classificações e ~2,5 ms). Em ms, a comparação mede cache e máquina, então use buffers.

## Antes — `make lake` (`explain-antes.txt`)

22,8 ms, **1.429 buffers** (`hit=1392 read=37`). O nó mais caro é o `Seq Scan on classificacao` dentro do LATERAL da classificação vigente: **933 buffers (65%)**, repetido 311 vezes, uma por ato. O `orgao_nome` custa 2 buffers por scan.

## Antes — `make cdc`, 5 atos (`explain-antes-cdc.txt`)

1,6 ms, 519 buffers. O `ato` entra por `ato_pkey` com `ANY('{1,2,3,4,5}')`. O `Seq Scan on classificacao` continua, mas roda 5 vezes, não 311. O custo é desprezível.

## Índice do plano: `orgao_nome (orgao_id, data_inicio, data_fim)`

Criado numa transação desfeita (`testar-indice.sh`, melhor de 5 execuções; planos em `explain-com-indice*.txt`):

| Cenário | Tempo | Buffers |
|---|---|---|
| sem índice | ~20,8 ms | 1.429 |
| com o índice | 20,7 ms (o planner não o usa) | 1.412 |

**Sem ganho neste volume: o índice não entra, não há migração `007`.**

## Próximo nó: o índice que já existe, `ix_classificacao_recente (ato_id, …)`

Com `enable_seqscan = off` (`INDICE='' testar-indice.sh`, plano em `explain-seqscan-off.txt`), o planner **consegue** usar o índice através da view `classificacao_vigente`: o LATERAL vira `Index Scan` (0,002 ms por ato).

| Cenário | Tempo | Buffers |
|---|---|---|
| planner livre (Seq Scan) | ~20,8 ms | 1.429 |
| `enable_seqscan = off` | 15,4 ms | 1.325 (−7%) |

O ganho é pequeno e está no ruído desta escala; o planner escolhe o Seq Scan porque, com 3 páginas, ele é mais barato. Não há índice a criar.

**Cuidado ao repetir a medição:** o `seqscan off` infla o custo estimado e liga o JIT, que sozinho gasta ~335 ms de 351 ms. O script desliga o JIT nesse cenário (`SET LOCAL jit = off`). Uma versão anterior deste texto publicou "~15× pior" por causa disso, e estava errada.

## O que fazer depois

- Remedir com o volume do backfill (#73): `bash explain.sh` e `INDICE='' bash testar-indice.sh`. Se o Seq Scan em `classificacao` passar de milhares de linhas, o planner passa a escolher o índice sozinho; se não passar, o caminho é reescrever o LATERAL.
- Levar este resultado ao ADR 0009 (#76). `tests/db/test_schema.sh` roda em `OK` nesta branch (não há migração).
