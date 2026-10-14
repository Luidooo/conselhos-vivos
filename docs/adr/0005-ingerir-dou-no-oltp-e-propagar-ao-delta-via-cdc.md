# 0005 — Ingerir atos de conselho do DOU no OLTP e propagar ao Delta Lake por CDC lógico

- **Status:** proposto
- **Data:** 2026-10-13
- **Decisores:** Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

A Entrega E2 requer a ingestão em lote de fontes públicas, o armazenamento analítico colunar transacional com suporte a reprocessamento e um fluxo de mudanças (CDC) demonstrado a partir do OLTP. 

No domínio do Conselhos Vivos, o pipeline opera sobre duas cargas:
1. **Carga histórica:** 215 atos rotulados pela pesquisadora (2003–2020), consolidados no PostgreSQL com suas respectivas tipologias ([ADR 0003](0003-carregar-a-planilha-como-rotulo-da-curadoria.md)).
2. **Fluxo contínuo do DOU:** ~96 atos de conselhos identificados por mês na Seção 1 (~1.150 atos/ano), extraídos de um universo de ~8.500 matérias mensais da Imprensa Nacional, com textos e ementas variando de ~1,9 KB até transcrições completas em HTML de ~42 KB.

A pergunta central deste ADR é: **como estruturar a ingestão pública e o mecanismo de propagação de mudanças para alimentar a camada analítica sem violar a restrição de operação simples pela pesquisadora (notebook pessoal, sem JVM, sem operadores dedicados)?**

---

## Por que o DOU agora entra no OLTP (revisão da premissa do ADR 0001)

No [ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md), a squad definiu:
> *"O espelho do DOU é a camada bronze, que é OLAP e vem na E2. (...) copiá-lo é ingestão, não transação."*

Contudo, na E2 o dado passa a sair do OLTP para o Delta Lake, e as matérias do DOU são gravadas na tabela `public.ato` do PostgreSQL via `make persist` e `make ingest-mensal`. Essa evolução arquitetural responde à pergunta central da arguição da E2 por cinco razões concretas do domínio:

1. **A curadoria humana exige uma entidade transacional:** Uma classificação humana ou de máquina não pode classificar "o nada" nem referenciar um ponteiro solto de arquivo XML sem chave primária. Na modelagem normalizada em 3NF ([ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)), a tabela `classificacao` impõe uma chave estrangeira estrita `ato_id REFERENCES ato(id)`. Se o DOU ficasse restrito a arquivos XML na camada bronze, o revisor humano não teria como registrar retificações no banco sem quebrar a integridade referencial.
2. **Resolução de identidade e aliases de órgãos ([ADR 0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)):** No XML do DOU, os conselhos aparecem sob dezenas de variações textuais não padronizadas. O ato precisa passar pela normalização de chave e, se não reconhecido, entrar transacionalmente na fila de decisão da pesquisadora (`orgao_alias` com status `INDEFINIDO` ou `AMBIGUO`). Essa gestão de pendências é uma transação viva da curadoria.
3. **Idempotência de retificações e controle de versões:** Matérias do DOU sofrem republicações, erratas e edições extras (`DO1E`). O controle de versão (`uq_ato_dou_versao`) e a regra de que uma matéria idêntica não cria linha nova, enquanto um texto alterado cria versão subsequente, exigem garantias transacionais ACID de unicidade e isolamento no PostgreSQL.
4. **O OLTP NÃO é um espelho indiscriminado do DOU:** Na medição real de agosto de 2026 (8.590 matérias no total), **8.494 matérias de órgãos desconhecidos ou alheios a conselhos foram descartadas** da tabela `ato` (restando apenas como registro na fila de aliases). Apenas 96 matérias foram gravadas como atos. O banco não espelha o Diário Oficial: ele armazena exclusivamente os atos de conselho que compõem o universo sob curadoria.
5. **Fonte única para a camada analítica:** Centralizar os 215 atos da planilha (`origem = 'PLANILHA'`) e os atos contínuos do DOU (`origem = 'DOU'`) na tabela `ato` permite que o pipeline analítico e o CDC tratem ambos sob o mesmo esquema unificado de vigência e auditoria.

---

## Fonte de ingestão em lote: Dados Abertos (mensal) vs INLABS (diário)

O checklist da E2 exige ingestão em lote automatizada de fonte pública, idempotente e reproduzível. Avaliamos duas fontes oficiais da Imprensa Nacional:

| Dimensão | INLABS (`make ingest`) | Dados Abertos (`make ingest-mensal`, adotada) |
|---|---|---|
| **Formato e granularidade** | ZIP diário por seção (`DO1`, `DO1E`) | ZIP mensal consolidado da Seção 1 (contendo todos os dias e extras) |
| **Autenticação e acesso** | Exige credenciais; desde 12/10 o endpoint `logar.php` responde `502 Bad Gateway` a scripts automatizados | **Público, sem autenticação**, sem restrição a scripts |
| **Histórico disponível** | Apenas dias recentes | **Série histórica completa desde janeiro de 2002** (cobre todo o intervalo 2003–2020 da planilha) |
| **Operação da pesquisadora** | Frágil: depende de contornar proteções antibot ou intervenção manual | **Robusta:** um comando `make ingest-mensal MES=AAAA-MM` baixa e ingere sem login |

**Decisão de ingestão:** Adotamos os **Dados Abertos da Imprensa Nacional** como fonte automatizada principal para a E2, mantendo o cliente INLABS no repositório exclusivamente para ingestões manuais sob demanda do dia corrente.

---

## Alternativas consideradas para a propagação ao Delta Lake

### A. Opção nula: recarga periódica completa agendada (`make lake` via cron/lote)

Nenhum mecanismo de captura de eventos em tempo real é configurado. Em intervalos fixos (ex.: a cada 1 hora ou diariamente) ou sob demanda da pesquisadora, um job lê todas as linhas de `ato` e `classificacao_vigente` no PostgreSQL e executa `MERGE` em todas as partições do Delta Lake (`make lake`).

- **Vantagens:** Simplicidade máxima. Zero configuração no PostgreSQL (`wal_level=replica` padrão), zero retenção de WAL no banco e sem slots para monitorar.
- **Desvantagens:** Escala em $O(N)$ em vez de $O(\Delta)$. Toda execução relê a tabela inteira do banco e abre todas as partições do Delta Lake, gerando tráfego de I/O redundante que piora à medida que novos anos acumulam HTMLs de até 42 KB. Não entrega um fluxo reativo de mudanças conforme exigido pelo checklist da E2.

### B. CDC lógico com consumidor próprio via slot nativo do PostgreSQL (escolhida)

O PostgreSQL é configurado com `wal_level=logical`. Um slot de replicação lógica (`conselhos_lake`) utiliza o plugin nativo `test_decoding`. O consumidor Python (`lake.cdc`) opera em protocolo de confirmação tardia: espia o slot (`pg_logical_slot_peek_changes`), filtra os `ato_id` alterados, busca apenas essas entidades no OLTP ($O(\Delta)$), grava no Delta Lake via `MERGE` atômico idempotente e confirma o LSN (`pg_logical_slot_get_changes`) somente após a persistência em disco.

- **Vantagens:** Custo de infraestrutura nulo (0 containers permanentes adicionais, sem JVM); latência sub-segundo; isolamento transacional; entrega *effectively-once* comprovada com tolerância a quedas bruscas ([ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md)).
- **Desvantagens:** Se o slot for esquecido sem consumidor ativo, o PostgreSQL retém segmentos de WAL em disco (mitigado pelo comando `make cdc-drop`); o plugin `test_decoding` gera tráfego de texto em memória que precisa ser descartado via regex.

### C. Debezium com Apache Kafka

Arquitetura distribuída clássica de Big Data: conector Debezium rodando em cluster Kafka Connect sobre Apache Kafka (com KRaft ou ZooKeeper), emitindo tópicos Avro/JSON com Schema Registry para um consumidor distribuído persistente (Spark Structured Streaming ou Flink) escrevendo em Delta Lake.

- **Vantagens:** Padrão industrial para múltiplos consumidores concorrentes e desacoplamento total entre produtores e consumidores de eventos.
- **Desvantagens:** Inviável para o contexto do projeto. Exige 3 a 4 containers Java/JVM rodando continuamente, alocando 1,5 GB a 2,5 GB de memória RAM permanente apenas para manter a infraestrutura ociosa aguardando ~3 a 5 atos por dia útil. Viola diretamente a restrição operacional de execução no notebook da pesquisadora.

---

## Medição empírica e reproduzível

As medições comparativas foram executadas com os dados reais do domínio e consolidadas no repositório:
```bash
docker compose run --rm lake python docs/adr/medicoes/0005-ingestao/bench.py
```

Resultados aferidos com os 215 atos da base real (`docs/adr/medicoes/0005-ingestao/resultados.json`):

| Dimensão de medição | (A) Opção Nula (Recarga completa) | (B) CDC Lógico Próprio (Adotada) | (C) Debezium + Apache Kafka |
|---|---|---|---|
| **Tempo de extração no OLTP** | 16,77 ms (todos os atos) | **2,85 ms (apenas o ato alterado, 5,9× mais rápido)** | ~1 ms (leitura direta de streaming no WAL) |
| **Tempo total de processamento** | 92,52 ms (leitura geral + merge global) | **73,40 ms (leitura de 1 ato + merge pontual)** | ~1.500 ms (latência de pipeline nos tópicos) |
| **Latência de chegada efetiva** | Lote (0 a 60 min, conforme o agendamento) | **Sub-segundo (< 1 s sob evento / ~6,6 s efêmero)** | 1 a 3 segundos (streaming contínuo) |
| **Containers permanentes adicionais** | **0** (apenas o PostgreSQL) | **0** (apenas o PostgreSQL com slot) | **4 containers** (ZooKeeper/KRaft, Kafka, Connect, Consumidor) |
| **Consumo de RAM permanente** | **0 MB** adicionais | **0 MB** adicionais (slot aloca bytes no PG) | **~2.048 MB (2 GB)** constantes de heap JVM |
| **Pico de RAM transitória** | ~45 MB (container efêmero) | ~45 MB (container efêmero) | ~2.560 MB |
| **Retenção de log/WAL no banco** | 0 bytes adicionais | 56 bytes (em dia) / ~25 KB (transação pendente) | Sem retenção de WAL após commit no connector |
| **Comportamento no reprocessamento** | Relê tudo de novo do zero ($O(N)$), I/O redundante | **Idempotência atômica:** entrega *at-least-once* absorvida no Delta via `checksum` (*effectively-once*) | Replay complexo por alteração de offset nos tópicos do consumidor |

---

## Síntese das escolhas colunares e de serialização

Para complementar a decisão de ingestão e propagação, ratificamos os critérios decididos no [ADR 0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md):

1. **Delta Lake × Apache Iceberg:**
   - O Delta Lake armazena seu log transacional (`_delta_log/`) diretamente no diretório local de arquivos (`file://data/silver/atos/`), dispensando serviços de catálogo externo (Hive Metastore, Nessie ou REST Catalog).
   - Oferece suporte completo e nativo a `MERGE INTO` atômico via Python/Rust puro (`deltalake`) sem qualquer dependência de JVM/Spark.
   - Integração nativa e simplificada no DuckDB (`delta_scan`).
2. **Particionamento por ano (`ano`):**
   - Evita o *small files problem*: com 215 atos, a partição diária gera 112 microarquivos Parquet, enquanto a partição anual consolida em apenas 12 arquivos saudáveis, reduzindo o tamanho em disco de 1.376 KB para 299 KB e acelerando as agregações analíticas no DuckDB de 16,7 ms para 4,9 ms (3,4× mais rápido).
3. **Compressão Zstandard (`zstd`):**
   - Configurada explicitamente via `WriterProperties(compression="ZSTD")`.
   - Gera redução de 20% a 29% no tamanho em disco em comparação ao Snappy para matérias com transcrições volumosas de HTML em `conteudo`, sem penalidade no tempo de consulta analítica no DuckDB.

---

## Decisão

1. **Ingerir as matérias de conselho do DOU no OLTP** (`public.ato`) a partir dos **Dados Abertos da Imprensa Nacional** (`make ingest-mensal MES=AAAA-MM`), filtrando apenas os atos pertinentes e enviando órgãos não mapeados para a fila de curadoria de aliases ([ADR 0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)).
2. **Propagar mudanças para o Delta Lake via CDC lógico com consumidor próprio** ([ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md)), utilizando decodificação nativa do PostgreSQL (`test_decoding`), protocolo de confirmação tardia (*peek* -> grava Delta -> confirma LSN) e `MERGE` idempotente por `ato_id` via biblioteca leve `deltalake`.
3. **Descartar Debezium com Kafka** em razão do custo de 4 containers permanentes e ~2 GB de RAM ociosa em máquina local, desproporcional ao volume de ~96 atos/mês do domínio.

---

## Consequências

**O que ganhamos:**
- **Operação leve e sustentável:** todo o ambiente roda no notebook pessoal da pesquisadora consumindo recursos mínimos, sem dependência de Java ou serviços de mensageria complexos.
- **Rastreabilidade completa de curadoria:** atos do DOU possuem integridade referencial 3NF com revisores e classificações humanas, permitindo auditoria rigorosa de versões e retificações.
- **Tolerância a falhas e reprocessamento idempotente:** a semântica *at-least-once* na leitura combinada com *MERGE* idempotente no destino garante que quedas forçadas do consumidor não gerem linhas duplicadas nem inconsistência nos indicadores analíticos.
- **Independência de login no DOU:** ingestão mensal pública e sem bloqueio, cobrindo o histórico desde 2002.

**O que perdemos:**
- **Risco operacional de retenção de WAL:** se o slot de replicação lógica for criado e abandonado sem um consumidor ativo, o PostgreSQL acumula arquivos de WAL e pode encher o disco da máquina (mitigado pelo comando de limpeza `make cdc-drop`).
- **Sobrecarga transitória no decodificador:** o plugin `test_decoding` decodifica transações de todas as tabelas em formato textual; durante ingestões volumosas em lote, linhas de `conteudo` precisam ser filtradas e descartadas na memória do processo Python.
- **Latência de disponibilidade do lote mensal:** os dados abertos mensais são consolidados pela Imprensa Nacional cerca de 10 a 15 dias após o fechamento do mês, exigindo o uso manual do cliente INLABS para obter publicações do dia corrente.
- **Duplicação de armazenamento entre camadas:** o texto do ato reside em XML no bronze (`data/bronze/`), em `public.ato` no PostgreSQL e na tabela consolidada do Delta Lake (`data/silver/atos/`).

**O que se torna irreversível:**
- Nada estrutural. Os dados na camada analítica permanecem em formato padrão Parquet/Delta Lake. Se no futuro o volume exigir migração para Kafka ou Iceberg, o modelo de chave primária (`ato_id`), particionamento anual e checksums já está consolidado.

---

## Gatilho de revisão

Esta decisão deve ser revista se:
1. **O volume de atos de conselho ultrapassar 100.000 eventos/mês** ou se múltiplos sistemas heterogêneos passarem a consumir as mudanças do OLTP concorrentemente (justificando adotar Debezium e Apache Kafka).
2. **O slot de replicação lógica acumular mais de 1 GB de WAL retido** por ausência prolongada de execução do consumidor.
3. **A Imprensa Nacional disponibilizar uma API oficial autenticada e pública** sem bloqueio a scripts automatizados para ingestão diária em lote.
4. **A pesquisadora exigir que consultas analíticas reflitam reclassificações em tempo real no clique da interface gráfica**, sem tolerar a latência do comando `make cdc` (justificando direcionar o consumo diretamente à view do PostgreSQL).

