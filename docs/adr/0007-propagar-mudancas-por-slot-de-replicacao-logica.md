# 0007 — Propagar mudanças do OLTP ao Delta por slot de replicação lógica, sem Kafka

- **Status:** proposto
- **Data:** 2026-10-13
- **Decisores:** Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

O `make lake` ([ADR 0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md)) relê o OLTP inteiro a cada execução. A E2 pede um fluxo de mudanças a partir do OLTP, e avisa sobre o "CDC que nunca viu uma mudança": o fluxo precisa ser demonstrado com uma mudança real. Como `classificacao` é insert-only ([ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)), uma reclassificação é um `INSERT` novo, e é isso que o fluxo precisa carregar até o Delta. O [ADR 0002](0002-manter-postgresql-como-motor-do-oltp.md) já previa o custo: `wal_level=logical`.

## Decisão

1. **Decodificação lógica do próprio Postgres** (`wal_level=logical` no serviço `db`), com um **slot** `conselhos_lake` e o plugin `test_decoding`, que vem na imagem oficial. Sem Kafka, Debezium nem outro processo permanente.
2. **O slot só diz *quais* atos mudaram.** O consumidor (`python -m lake.cdc`, `make cdc`) extrai o `ato_id` dos `INSERT` em `public.classificacao`, relê esses atos do OLTP com a mesma consulta do `make lake` e faz o `MERGE` por `ato_id`. A regra "revisão humana vence pipeline" e o checksum ficam num lugar só.
3. **Entrega pelo menos uma vez.** O consumidor espia o slot (`pg_logical_slot_peek_changes`), grava o Delta e só então consome até o último LSN visto (`pg_logical_slot_get_changes`). Se cair no meio, o evento volta, e o `MERGE` idempotente absorve a repetição.
4. O slot nasce vazio: **o Delta precisa de uma carga completa (`make lake`) antes**, e o consumidor recusa rodar sem ela.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Debezium + Kafka | Dois serviços permanentes e uma JVM num notebook, para ~96 atos/mês |
| `pgoutput` | Exige parsear protocolo binário e criar publication, sem ganho nesse volume |
| `wal2json` | Não vem na imagem oficial do Postgres |
| Reaplicar a regra de vigência a partir do WAL | Duplicaria a regra de negócio; reler o OLTP evita |
| Triggers que gravam uma fila | Mudaria o esquema do OLTP e perde o que o WAL já garante |

## Consequências

**Ganhamos:** atualização incremental do Delta a partir de uma mudança real, sem infraestrutura nova; reclassificações chegam ao Delta com o `make cdc`.

**Perdemos / riscos:**
- **Slot sem consumidor retém WAL e pode encher o disco.** Se o fluxo for abandonado, rode `make cdc-drop`.
- O texto do `test_decoding` não é um contrato estável entre versões do Postgres; o consumidor depende só do formato `table public.classificacao: INSERT: ... ato_id[bigint]:N`. Está coberto por `tests/lake/test_cdc.sh` e a imagem do Postgres está fixada.
- Mudanças anteriores à criação do slot não são vistas: vale a carga completa.
- O fluxo cobre `classificacao`. Mudanças em outras tabelas (por exemplo nome de órgão) continuam dependendo do `make lake`.

## Gatilho de revisão

- Volume ou latência que o `make cdc` sob demanda não aguente, ou mais de um consumidor do mesmo fluxo: reavaliar Debezium e Kafka.
- Atualização de versão maior do Postgres: revalidar o formato do `test_decoding`.

