---
title: Entrega E2
outline: [2, 3]
---

# Entrega E2 · Ingestão em lote e captura de mudanças

Cada item do [checklist de aceite da E2](https://unb-bd2.github.io/PlanoEnsino/projeto/e2/), na ordem da página da disciplina, com o lugar exato onde conferir. O que ainda não está no `main` aparece marcado como pendente, com a issue ou o PR em que está sendo feito.

::: tip Conferir em máquina limpa
```bash
git clone https://github.com/Luidooo/conselhos-vivos.git && cd conselhos-vivos
make setup                        # cria o .env, sobe o Postgres, aplica as migrações e carrega a planilha
make test                         # inclui a idempotência da gravação e a janela de reprocessamento
make ingest-mensal MES=2026-08    # baixa agosto de 2026 dos dados abertos e grava as matérias de conselho
make ingest-mensal MES=2026-08    # de novo: 0 gravadas, nada muda no banco
make lake                         # OLTP → tabela Delta em data/silver/atos/; de novo: 0 inseridas
make cdc-demo                     # reclassifica um ato e mostra a mudança atravessando o slot até o Delta
make cdc-chaos                    # derruba o consumidor pós-gravação e reprocessa provando que nada duplica
```
Pré-requisitos: Docker com Compose v2 e `make`. A ingestão mensal não precisa de credencial. Detalhes em [Como rodar](/visao-geral#como-rodar).
:::

## 1. Ingestão em lote da fonte pública, idempotente e reexecutável

**Fonte:** o Diário Oficial da União em XML, pelos [dados abertos da Imprensa Nacional](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados): um ZIP por mês, público e sem login, com o histórico desde 2002. O INLABS, que publica o dia, continua disponível pelo `make ingest`, mas recusa login automático; por isso a fonte automática é a mensal ([#42](https://github.com/Luidooo/conselhos-vivos/issues/42)).

- **Um comando:** `make ingest-mensal MES=AAAA-MM` baixa a Seção 1 do mês para `data/bronze/dados-abertos/` e grava as matérias de conselho em `ato`. Mês já em disco não é baixado de novo. Conferir: [Ingerir um mês pelos dados abertos](/visao-geral#ingerir-um-mes-pelos-dados-abertos).
- **Idempotente:** cada matéria é comparada com todas as versões dela no banco; igual, nada é gravado; diferente, entra como versão nova, e as anteriores ficam. Conferir: [Gravar as matérias no banco](/visao-geral#gravar-as-materias-no-banco).
- **Medido com dado real**, num banco limpo, com agosto de 2026 (8.590 matérias, 52,6 MB):

  | Execução | gravadas | inalteradas | órgão desconhecido | falhou |
  |---|---|---|---|---|
  | 1ª | 96 | 0 | 8.494 | 0 |
  | 2ª | 0 | 96 | 8.494 | 0 |

  Depois da 2ª execução, `ato`, `orgao_alias` e `classificacao` saíram idênticos linha a linha. Conferir: [diário da semana 10](/docs/diario/2026-10-13) e [PR #43](https://github.com/Luidooo/conselhos-vivos/pull/43).
- **Testado:** `TestPersistTwiceLeavesTheDatabaseIdentical` grava a mesma edição duas vezes e compara o banco linha a linha, com `id` e `criado_em`; roda no `make test` e no CI.

## 2. Fluxo de mudanças a partir do OLTP (CDC)

- **Decodificação lógica do próprio Postgres**, sem Kafka nem Debezium: o banco sobe com `wal_level=logical`, um slot (`conselhos_lake`, plugin `test_decoding`) guarda as mudanças de `classificacao`, e `make cdc` as aplica na tabela Delta. O slot só diz *quais* atos mudaram; o consumidor relê esses atos do OLTP com a mesma consulta do `make lake` e grava por `MERGE` em `ato_id`. Conferir: [Fluxo de mudanças do OLTP ao Delta](/visao-geral#fluxo-de-mudancas-do-oltp-ao-delta-cdc) e [ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica).
- **O CDC viu uma mudança de verdade:** `make cdc-demo` reclassifica um ato (um `INSERT` novo, porque `classificacao` é insert-only), consome o slot, mostra a linha nova no Delta e depois restaura a tipologia original pelo mesmo caminho. Testado por [`tests/lake/test_cdc.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_cdc.sh), que roda no `make test`.
- **Cobertura declarada:** o fluxo cobre `INSERT` em `classificacao`; ato novo do DOU, versão nova e troca de nome de órgão continuam entrando pelo `make lake`.
- **Medido** (ADR 0007, script em `docs/adr/medicoes/0007-cdc/`): recarga completa dos 215 atos ~68 ms contra ~58 ms do incremental de um ato; o slot consumido retém 56 bytes de WAL, e uma reclassificação pendente, 512 bytes.

## 3. Camada de armazenamento analítico em formato aberto

- **Tabela Delta sobre Parquet** em `data/silver/atos/`, uma tabela consolidada (ato, órgão vigente na data, tipologia vigente), particionada por ano e gravada por `MERGE` em `ato_id` a partir do OLTP com a biblioteca `deltalake` (Rust/Python, sem JVM). Lida pelo DuckDB com `delta_scan`. Conferir: [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta).
- **Idempotente:** `make lake` duas vezes com os 311 atos (215 da planilha + 96 do DOU de agosto): 1ª `inseridas=311`, 2ª `inseridas=0 atualizadas=0 inalteradas=311`. Testado por [`tests/lake/test_lake.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_lake.sh), que compara a contagem do DuckDB com o `count(*)` do banco.
- **Delta × Iceberg** com critério explícito (catálogo, `MERGE` em Python puro, leitura no DuckDB) no ADR 0006.

## 4. Semântica de entrega declarada e demonstrada

- **Declarada:** pelo menos uma vez na leitura, efetivamente uma vez no destino. O consumidor espia o slot (`pg_logical_slot_peek_changes`), grava o Delta por `MERGE` atômico na chave primária (`ato_id`) e checksum de integridade, e só então consome até o último LSN (`pg_logical_slot_get_changes`). Se o processo cair antes de avançar o slot, o evento permanece no WAL e é entregue de novo na próxima execução (*at-least-once*); o `MERGE` idempotente detecta que a versão no Delta já coincide e absorve a repetição (`inalteradas=N`, `inseridas=0`, `atualizadas=0`), assegurando semântica *effectively-once*. Conferir: [ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica), decisão 3.
- **Demonstrada por teste automatizado:** [`tests/lake/test_cdc.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_cdc.sh) (integrado ao `make test` e CI) simula a interrupção forçada (`--falhar-apos-gravar`, exit code 42), confirma que o slot permaneceu sem avançar (`pendentes > 0`), reexecuta o consumidor normal e afere via DuckDB que a contagem total de registros no Delta Lake permaneceu estritamente inalterada e com 0 duplicações.
- **Demonstrada por comando interativo:** `make cdc-chaos` roda o roteiro reproduzível [`scripts/cdc_chaos_demo.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/scripts/cdc_chaos_demo.sh): reclassifica um ato no OLTP, derruba o consumidor intencionalmente após o MERGE no Delta, inspeciona o slot e o Delta Lake durante a falha, reexecuta o consumidor e valida via DuckDB que a contagem de atos (215) se mantém idêntica, sem linhas duplicadas.

## 5. Dado atrasado e reprocessamento de janela

- **Janela de dias:** `make ingest` busca e grava de novo os últimos `JANELA` dias (padrão 7, provisório), do mais antigo para o mais novo; `make janela` lista os dias sem baixar nada. Conferir: [Gravar as matérias no banco](/visao-geral#gravar-as-materias-no-banco), no parágrafo "Dado atrasado".
- **O ato atrasado fica na data em que foi publicado**, não na data em que chegou. Testado por `TestPersistTakesAMateriaThatArrivedLate`; a conta da janela, por [`tests/ingest/test_janela.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/ingest/test_janela.sh).
- **O que chega depois da janela** não entra sozinho; está escrito o que fazer.
- **Na fonte mensal não há janela:** o ZIP de um mês fechado já traz a edição extra (`DO1E`) de todos os dias, e uma retificação sai como matéria nova, na data em que foi publicada.

- **No Delta:** como o `make lake` relê o OLTP inteiro e grava por `ato_id`, um ato que chega atrasado cai na partição do ano em que foi publicado (`ano` vem de `data_publicacao`), sem mexer nas outras. A demonstração disso com um ato de data antiga ainda está em aberto na [#31](https://github.com/Luidooo/conselhos-vivos/issues/31).

## 6. Serialização e compressão justificadas pelo padrão de acesso

- **Parquet particionado por ano**, não por dia: com os 215 atos da planilha, a partição diária dá 112 arquivos de poucos KB e a anual, 12; a agregação por conselho e tipologia no DuckDB cai de 16,7 ms para 4,9 ms. Partição por órgão foi descartada porque o indicador compara os 82 conselhos de uma vez.
- **`zstd`, medido contra `snappy`** com os dados reais: mesmo tempo de consulta (agregação e busca no texto) e 20% a 29% menos disco. A escolha não é o padrão da ferramenta: o `deltalake` grava `snappy` se nada for dito, e o código fixa `WriterProperties(compression="ZSTD")`. Script e resultados em [`docs/adr/medicoes/0006-camada-analitica/`](https://github.com/Luidooo/conselhos-vivos/tree/main/docs/adr/medicoes/0006-camada-analitica); justificativa no [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta).

## 7. ADR sobre o mecanismo de ingestão, com a opção nula considerada

- **Método de Decisão com 3 alternativas:** [ADR 0005](/docs/adr/0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc) compara formalmente a **Opção Nula** (A, recarga periódica completa agendada), o **CDC lógico nativo** (B, adotada) e **Debezium com Kafka** (C).
- **Medição reproduzível no repositório:** comando `docker compose run --rm lake python docs/adr/medicoes/0005-ingestao/bench.py` afere latência, containers, consumo de RAM permanente e comportamento no reprocessamento com os dados reais do domínio.
  - *Containers e RAM permanente:* Opção B adiciona **0 containers e 0 MB de RAM permanente** (contra 4 containers e ~2 GB de RAM JVM permanente do Debezium + Kafka).
  - *Latência de processamento:* extração pontual no OLTP é **~5,9× mais rápida** (2,8 ms vs 16,8 ms) e o tempo total de processamento é **1,26× mais rápido** do que varrer a base inteira, com ganho $O(\Delta)$ vs $O(N)$ que se amplia conforme novos anos acumulam HTMLs no OLTP.
  - *Reprocessamento e tolerância a falhas:* entrega *effectively-once* comprovada sem duplicação no Delta Lake ([ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica)).
- **Por que o DOU agora entra no OLTP:** o ADR 0001 previa o DOU apenas como bronze/OLAP. O ADR 0005 documenta a evolução: a curadoria humana em 3NF exige que `classificacao` aponte para uma chave estrangeira real em `ato(id)`, a fila de resolução de aliases de órgãos ([ADR 0004](/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada)) é transacional viva, e o OLTP não espelha o DOU (em agosto/2026, 8.494 matérias alheias a conselho foram descartadas e apenas as 96 matérias pertinentes foram gravadas).
- **Dados Abertos vs INLABS:** a ingestão automática oficial adotou os Dados Abertos mensais públicos (sem login, com histórico desde 2002 e DO1E), contornando o bloqueio de login com erro 502 que o INLABS impôs a scripts em 12/10.
- **Delta × Iceberg e compressão zstd:** critérios explícitos consolidados no [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta).


## 8. Diário de bordo das semanas 7 a 10

| Semana | Diário |
|---|---|
| 7 | [25/09](/docs/diario/2026-09-25) e [26/09](/docs/diario/2026-09-26) |
| 8 | [29/09](/docs/diario/2026-09-29) |
| 9 | [06/10](/docs/diario/2026-10-06) |
| 10 | [13/10](/docs/diario/2026-10-13) |

## Processo da squad

- Registro de uso de IA, uma entrada por uso: [AI-USAGE](/AI-USAGE).
- Histórico e revisões entre pares: [pull requests](https://github.com/Luidooo/conselhos-vivos/pulls?q=is%3Apr).
- O que a E2 deixa para a E3: [Jornada do dado](/jornada-do-dado).
