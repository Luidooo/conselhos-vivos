# 0007 — Propagar mudanças do OLTP ao Delta por slot de replicação lógica, sem Kafka

- **Status:** proposto
- **Data:** 2026-10-13
- **Decisores:** Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

O `make lake` ([ADR 0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md)) relê o OLTP inteiro a cada execução. A E2 pede um fluxo de mudanças a partir do OLTP, e avisa sobre o "CDC que nunca viu uma mudança": o fluxo precisa ser demonstrado com uma mudança real. Como `classificacao` é insert-only ([ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)), uma reclassificação é um `INSERT` novo, e é isso que o fluxo precisa carregar até o Delta. O [ADR 0002](0002-manter-postgresql-como-motor-do-oltp.md) já previa o custo: `wal_level=logical`.

## Decisão

1. **Decodificação lógica do próprio Postgres** (`wal_level=logical` no serviço `db`), com um **slot** `conselhos_lake` e o plugin `test_decoding`, que vem na imagem oficial. Sem Kafka, Debezium nem outro processo permanente.
2. **O slot só diz *quais* atos mudaram.** O consumidor (`python -m lake.cdc`, `make cdc`) extrai o `ato_id` dos `INSERT` em `public.classificacao`, relê esses atos do OLTP com a mesma consulta do `make lake` e faz o `MERGE` por `ato_id`. A regra "revisão humana vence pipeline" e o checksum ficam num lugar só.
3. **Semântica de entrega: pelo menos uma vez na leitura, efetivamente uma vez no destino.** O consumidor segue um protocolo estrito de confirmação tardia:
   - **Espia:** lê os eventos pendentes sem avançar o cursor (`pg_logical_slot_peek_changes`).
   - **Aplica:** executa a consulta analítica do ato no OLTP e realiza a escrita no Delta Lake por `MERGE` atômico baseado na chave primária (`ato_id`) e no `checksum` de integridade.
   - **Confirma:** somente após o sucesso da gravação no Delta, o consumidor consome o lote e avança o cursor LSN (`pg_logical_slot_get_changes`).
   Se o consumidor sofrer queda forçada ou falhar entre a aplicação e a confirmação, o slot retém os eventos no WAL. Na reinicialização, os mesmos eventos são entregues novamente (*at-least-once*). Como o Delta Lake já contém as alterações, a condição `target.checksum != source.checksum` resulta em 0 inserções e 0 atualizações (`inalteradas=N`), absorvendo o reprocessamento de forma idempotente e garantindo entrega *effectively-once*.
4. O slot nasce vazio: **o Delta precisa de uma carga completa (`make lake`) antes**, e o consumidor recusa rodar sem ela.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Opção nula: recarga periódica agendada (`make lake` recorrente) | Varre o OLTP inteiro e relê todas as partições do Delta a cada ciclo (O(N) em vez de O(Δ)). Embora em pequeno volume o tempo total de container empate (~7 s), em escala anual (~1.150 atos com HTML de até 42 KB) gera tráfego de I/O redundante. Além disso, não cumpre o requisito de fluxo reativo de mudanças com entrega pelo menos uma vez da E2 |
| Debezium + Kafka | Dois serviços permanentes e uma JVM num notebook, para ~96 atos/mês |
| `pgoutput` | Exige parsear protocolo binário e criar publication, sem ganho nesse volume |
| `wal2json` | Não vem na imagem oficial do Postgres |
| Reaplicar a regra de vigência a partir do WAL | Duplicaria a regra de negócio; reler o OLTP evita |
| Triggers que gravam uma fila | Mudaria o esquema do OLTP e perde o que o WAL já garante |

### Medições empíricas: Opção Nula vs CDC incremental

As medições são reproduzíveis via script dedicado no repositório:
```bash
docker compose run --rm lake python docs/adr/medicoes/0007-cdc/bench.py
```

Com os 215 atos reais e medições no PostgreSQL 16 (conforme `docs/adr/medicoes/0007-cdc/resultados.json`):
- **Tempo de extração e MERGE no Python (medianas):**
  - `make lake` (recarga completa, 215 atos): **~68 ms** (11,4 ms na consulta OLTP de todos os atos + 56,8 ms no merge Delta em todas as partições).
  - `make cdc` (incremental, 1 ato alterado): **~58 ms** (1,9 ms na consulta OLTP filtrada por ID + 56,4 ms no merge Delta). A extração do OLTP é **~6× mais rápida**.
  *(Nota: no Compose sob demanda, ambos somam ~6,6 s a 7,0 s com a subida do container efêmero; a vantagem do CDC cresce com O(Δ) vs O(N) conforme os atos acumulam HTMLs volumosos no OLTP).*
- **Tamanho do WAL retido pelo slot:**
  - Slot consumido (em dia): **56 bytes** de defasagem (`pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)`).
  - Transação de reclassificação única: **512 bytes** de WAL na alteração isolada (e até **~29 KB** se envolver cadastro de metadados de novo revisor na mesma transação).
  - Risco de retenção: se o consumidor não rodar, o Postgres acumula arquivos de WAL inteiros (segmentos de 16 MB cada) sem conseguir reciclá-los.

*(Medição válida também para a análise do mecanismo de ingestão no ADR 0005 / #32).*

## Consequências

**Ganhamos:** atualização incremental do Delta a partir de uma mudança real, sem infraestrutura nova; reclassificações chegam ao Delta com o `make cdc`.

**Perdemos / riscos:**
- **Slot sem consumidor retém WAL e pode encher o disco.** Se o fluxo for abandonado, rode `make cdc-drop`.
- **Custo de memória com `test_decoding` descartando dados de outras tabelas.** O plugin `test_decoding` decodifica todas as linhas alteradas de todas as tabelas em formato texto. Durante ingestões em lote (como `make ingest-mensal`), atos novos geram centenas de KB ou MB de HTML em `ato.conteudo`; o `ler_pendentes` carrega essas linhas na memória do Python apenas para descartar via regex o que não for `classificacao`. Manter `test_decoding` sem `pgoutput` é defensável no volume do projeto, mas requer atenção a esse consumo de memória transitório.
- **Queda forçada e tolerância a falhas comprovada (#30).** A ordem operacional garante pelo menos uma vez (peek -> grava Delta -> consome LSN). A resiliência a falhas é testada de ponta a ponta em `tests/lake/test_cdc.sh` e demonstrável via `make cdc-chaos` (`scripts/cdc_chaos_demo.sh`): derrubando intencionalmente o processo consumidor (`--falhar-apos-gravar`) após a aplicação no Delta Lake e antes de avançar o slot, o reprocessamento subsequente absorve as mudanças via `MERGE` idempotente sem gerar duplicações ou alterações na contagem total da tabela analítica.
- O texto do `test_decoding` não é um contrato estável entre versões do Postgres; o consumidor depende só do formato `table public.classificacao: INSERT: ... ato_id[bigint]:N`. Está coberto por `tests/lake/test_cdc.sh` e a imagem do Postgres está fixada.
- Mudanças anteriores à criação do slot não são vistas: vale a carga completa.
- O fluxo cobre `classificacao`. Mudanças em outras tabelas (por exemplo nome de órgão) continuam dependendo do `make lake`.

## Gatilho de revisão

- Volume ou latência que o `make cdc` sob demanda não aguente, ou mais de um consumidor do mesmo fluxo: reavaliar Debezium e Kafka.
- Atualização de versão maior do Postgres: revalidar o formato do `test_decoding`.

