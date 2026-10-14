# 0005 — Ingerir atos de conselho do DOU no OLTP e propagar ao Delta Lake por CDC lógico

- **Status:** proposto
- **Data:** 2026-10-13
- **Decisores:** Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

A Entrega E2 requer a ingestão em lote de fontes públicas, o armazenamento analítico colunar transacional com suporte a reprocessamento e um fluxo de mudanças (CDC) demonstrado a partir do OLTP. 

No domínio do Conselhos Vivos, o pipeline opera sobre duas cargas:
1. **Carga histórica:** 215 atos rotulados pela pesquisadora (2003–2020), consolidados no PostgreSQL com suas respectivas tipologias ([ADR 0003](0003-carregar-a-planilha-como-rotulo-da-curadoria.md)).
2. **Fluxo contínuo do DOU:** ~96 atos de conselhos identificados por mês na Seção 1 (~1.150 atos/ano), extraídos de um universo de ~8.500 matérias mensais da Imprensa Nacional, com textos e ementas variando de ~1,9 KB até transcrições completas em HTML de ~42 KB.
Juntas, as duas cargas somam **311 atos na base de referência** da E2.

A pergunta central deste ADR é: **como estruturar a ingestão pública e o mecanismo de propagação de mudanças para alimentar a camada analítica sem violar a restrição de operação simples pela pesquisadora (notebook pessoal, sem JVM, sem operadores dedicados)?**

---

## Por que o DOU agora entra no OLTP (revisão da premissa do ADR 0001)

No [ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md), a squad definiu:
> *"O espelho do DOU é a camada bronze, que é OLAP e vem na E2. (...) copiá-lo é ingestão, não transação."*

Contudo, na E2 o dado passa a sair do OLTP para o Delta Lake, e as matérias do DOU são gravadas na tabela `public.ato` do PostgreSQL via `make persist` e `make ingest-mensal`. Essa evolução arquitetural responde à pergunta central da arguição da E2 por cinco razões concretas do domínio:

1. **A curadoria humana exige uma entidade transacional:** Uma classificação humana ou de máquina não pode classificar "o nada" nem referenciar um ponteiro solto de arquivo XML sem chave primária. Na modelagem normalizada em 3NF ([ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)), a tabela `classificacao` impõe uma chave estrangeira estrita `ato_id REFERENCES ato(id)`. Se o DOU ficasse restrito a arquivos XML na camada bronze, o revisor humano não teria como registrar retificações no banco sem quebrar a integridade referencial.
2. **Resolução de identidade e aliases de órgãos ([ADR 0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)):** No XML do DOU, os conselhos aparecem sob dezenas de variações textuais não padronizadas. O ato precisa passar pela normalização de chave e, se não reconhecido, entrar transacionalmente na fila de decisão da pesquisadora (`orgao_alias` com status `INDEFINIDO` ou `AMBIGUO`). Essa gestão de pendências é uma transação viva da curadoria.
3. **Idempotência de retificações e controle de versões:** Matérias do DOU sofrem republicações, erratas e edições extras (`DO1E`). O controle de versão (`uq_ato_dou_versao`) e a regra de que uma matéria idêntica não cria linha nova, enquanto um texto alterado cria versão subsequente, exigem garantias transacionais ACID de unicidade e isolamento no PostgreSQL.
4. **O OLTP NÃO é um espelho indiscriminado do DOU:** Na medição real de agosto de 2026 (8.590 matérias no total), apenas **96 matérias foram gravadas na tabela `ato`** como atos de conselhos reconhecidos. As outras 8.494 matérias não entraram como registros em `ato`: delas foram extraídos **626 nomes novos de órgãos** não mapeados, que foram inseridos na fila de decisão da pesquisadora (`orgao_alias` expandido de 125 para 751 aliases, status `INDEFINIDO`), enquanto os textos das matérias alheias foram descartados do OLTP. O banco armazena exclusivamente os atos de conselho que compõem o universo sob curadoria.
5. **Fonte única para a camada analítica:** Centralizar os 215 atos da planilha (`origem = 'PLANILHA'`) e os atos contínuos do DOU (`origem = 'DOU'`) na tabela `ato` permite que o pipeline analítico e o CDC tratem ambos sob o mesmo esquema unificado de vigência e auditoria.

### O que NÃO mudou em relação ao ADR 0001

Para manter as garantias da modelagem original:
- **O OLTP continua sendo a curadoria:** a missão primordial do PostgreSQL permanece sendo o registro do julgamento humano e do ciclo de vida das classificações insert-only.
- **O `ato` do DOU entra estritamente como a entidade que a `classificacao` referencia:** o próprio ADR 0001 já previa na modelagem os atributos `origem = 'DOU' | 'PLANILHA'` e `versao` para retificações.
- **O espelho integral segue no bronze:** o PostgreSQL não armazena a totalidade bruta do Diário Oficial da União; todos os arquivos XML originais de todas as matérias continuam preservados integralmente na camada bronze (`data/bronze/`), que é OLAP.

---

## Fonte de ingestão em lote: Dados Abertos (mensal) vs INLABS (diário)

O checklist da E2 exige ingestão em lote automatizada de fonte pública, idempotente e reproduzível. Avaliamos duas fontes oficiais da Imprensa Nacional:

| Dimensão | INLABS (diário) | Dados Abertos (`make ingest-mensal`, adotada) |
|---|---|---|
| **Formato e granularidade** | ZIP diário por seção (`DO1`, `DO1E`) | ZIP mensal consolidado da Seção 1 (contendo todos os dias e extras) |
| **Autenticação e acesso** | Exige credenciais; desde 12/10 o endpoint `logar.php` responde `502 Bad Gateway` a scripts automatizados | **Público, sem autenticação**, sem restrição a scripts |
| **Histórico disponível** | Apenas dias recentes | **Série histórica completa desde janeiro de 2002** (cobre todo o intervalo 2003–2020 da planilha) |
| **Operação da pesquisadora** | Frágil: login via script bloqueado; dia corrente depende de baixar o ZIP no navegador e rodar `make persist` | **Robusta:** um comando `make ingest-mensal MES=AAAA-MM` baixa e ingere sem login |

**Decisão de ingestão:** Adotamos os **Dados Abertos da Imprensa Nacional** como fonte automatizada principal para a E2. O cliente INLABS tem seu login automático de script recusado com `502 Bad Gateway`; para obter publicações do dia corrente, a operação é baixar o ZIP manualmente pelo navegador na interface web do INLABS e rodar `make persist` (ou `make persist DATA=AAAA-MM-DD`).

---

## Alternativas consideradas para a propagação ao Delta Lake

### A. Opção nula: recarga periódica completa agendada (`make lake` via cron/lote)

Nenhum mecanismo de captura de eventos em tempo real é configurado. Em intervalos fixos (ex.: a cada 1 hora ou diariamente) ou sob demanda da pesquisadora, um job lê todas as linhas de `ato` e `classificacao_vigente` no PostgreSQL e executa `MERGE` em todas as partições do Delta Lake (`make lake`).

- **Vantagens:** Simplicidade máxima. Zero configuração no PostgreSQL (`wal_level=replica` padrão), zero retenção de WAL no banco e sem slots para monitorar.
- **Desvantagens:** Escala em O(N) em vez de O(Δ), onde hoje N = 311 atos (215 históricos + 96 de agosto/2026), acumulando ~1.150 atos/ano. Toda execução relê a tabela inteira do banco e abre todas as partições do Delta Lake, gerando tráfego de I/O redundante que piora à medida que novos anos acumulam HTMLs de até 42 KB. Não entrega um fluxo reativo de mudanças com semântica demonstrada conforme exigido pelo checklist da E2.
- **Comparativo real:** Em tempo de CPU no Python, a opção nula e o CDC praticamente empatam (92,5 ms vs 65,4 ms no volume atual, speedup total de apenas 1,41×), porque a etapa de `MERGE` no Delta Lake domina o tempo. Em tempo de parede no Compose, ambos levam ~7 s por execução efêmera (`docker compose run`). A extração pontual no OLTP é sim significativamente mais rápida no CDC (1,7 ms vs 25,8 ms), mas como a extração é a parte leve do pipeline, essa diferença não é o argumento decisivo no volume atual. Escolhemos o CDC porque o checklist da E2 exige fluxo de mudanças com semântica demonstrada, e porque ele custa zero containers e zero RAM permanente a mais.

### B. CDC lógico com consumidor próprio via slot nativo do PostgreSQL (escolhida)

Decidido e detalhado no [ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md). O PostgreSQL opera com `wal_level=logical` e um slot de replicação lógica (`conselhos_lake`, plugin nativo `test_decoding`). O consumidor Python (`lake.cdc`, `make cdc`) espia o slot (`pg_logical_slot_peek_changes`), busca apenas as entidades alteradas no OLTP (O(Δ)), aplica no Delta Lake via `MERGE` idempotente e confirma o LSN (`pg_logical_slot_get_changes`) somente após a gravação.

- **Vantagens:** Custo de infraestrutura nulo (0 containers permanentes adicionais, sem JVM, aproveitando o slot nativo do Postgres); isolamento transacional; entrega *effectively-once* comprovada com tolerância a quedas bruscas ([ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md)).
- **Latência operacional:** No projeto não há daemon rodando continuamente; `make cdc` roda sob demanda ou agendado em lote, pertencendo à mesma categoria operacional da opção A (tempo de parede de ~6,8 s no Compose efêmero). A diferença é o trabalho por execução: O(Δ) versus O(N).
- **Desvantagens:** Se o slot for abandonado sem consumidor ativo, o PostgreSQL retém segmentos de WAL em disco (mitigado por `make cdc-drop`); o plugin `test_decoding` gera tráfego de texto em memória que precisa ser filtrado.

### C. Debezium com Apache Kafka

Arquitetura distribuída clássica de Big Data: conector Debezium rodando em cluster Kafka Connect sobre Apache Kafka (com KRaft ou ZooKeeper), emitindo tópicos Avro/JSON com Schema Registry para um consumidor distribuído persistente escrevendo em Delta Lake.

- **Vantagens:** Padrão industrial para múltiplos consumidores concorrentes e desacoplamento total entre produtores e consumidores de eventos.
- **Desvantagens:** Inviável para o contexto do projeto. Como sintetizado no ADR 0007, seriam "dois serviços permanentes e uma JVM num notebook, para ~96 atos/mês". Exigiria 3 a 4 containers Java/JVM rodando continuamente, alocando 1,5 GB a 2,5 GB de memória RAM permanente apenas para manter a infraestrutura ociosa aguardando ~3 a 5 atos por dia útil. Viola diretamente a restrição operacional de execução no notebook da pesquisadora.

---

## Medição empírica e reproduzível

As medições comparativas foram executadas com os dados reais do domínio e consolidadas no repositório.

Como reproduzir (não altera o banco; executa apenas consultas de leitura no OLTP e gravações em diretórios temporários efêmeros, atualizando `resultados.json`):
```bash
docker compose run --rm lake python docs/adr/medicoes/0005-ingestao/bench.py
```

Resultados aferidos com os **311 atos da base de referência** (215 atos da planilha histórica 2003–2020 + 96 atos da ingestão de agosto de 2026 do DOU), a mesma base utilizada no ADR 0006 e no `make lake` (`docs/adr/medicoes/0005-ingestao/resultados.json`):

| Dimensão de medição | (A) Opção Nula (Recarga completa) | (B) CDC Lógico Próprio (Adotada) | (C) Debezium + Apache Kafka |
|---|---|---|---|
| **Tempo de extração no OLTP** | 25,76 ms (todos os atos) | **1,71 ms (apenas o ato alterado, 15× mais rápido na extração)** | ~1 ms *(estimativa, não medida)* |
| **Tempo total de processamento (Python)** | 92,47 ms (leitura geral + merge global) | **65,40 ms (leitura de 1 ato + merge pontual; 1,41× mais rápido)** | ~1.500 ms *(estimativa, não medida)* |
| **Tempo de parede no Compose efêmero** | ~7,0 s (overhead de subir container domina) | ~6,8 s (overhead de subir container domina) | N/A (opera com containers permanentes) |
| **Latência de chegada efetiva** | Sob demanda (`make lake`) ou agendado (~7 s por execução) | Sob demanda (`make cdc`) ou agendado (~6,8 s por execução; mesma categoria de A) | 1 a 3 segundos *(estimativa de streaming, não medida)* |
| **Containers permanentes adicionais** | **0** (apenas o PostgreSQL) | **0** (apenas o PostgreSQL com slot nativo) | **4 containers** *(estimativa típica: ZooKeeper/KRaft, Kafka, Connect, Consumidor)* |
| **Consumo de RAM permanente** | **0 MB** adicionais | **0 MB** adicionais (slot aloca bytes no PG) | **~2.048 MB (2 GB)** *(estimativa de heap JVM típica, não medida)* |
| **Pico de RAM transitória** | ~45 MB *(estimativa do container efêmero)* | ~45 MB *(estimativa do container efêmero)* | ~2.560 MB *(estimativa, não medida)* |
| **Retenção de log/WAL no banco** | 0 bytes adicionais | 56 bytes (em dia) / 512 bytes (uma reclassificação pendente) [ADR 0007] | Sem retenção de WAL após commit no connector *(estimativa)* |
| **Comportamento no reprocessamento** | Relê tudo de novo do zero (O(N)), redundante e pesado em I/O | **Idempotência atômica:** entrega *at-least-once* absorvida no Delta via `checksum` (*effectively-once* comprovado no ADR 0007) | Replay complexo por alteração de offset nos tópicos do consumidor *(estimativa)* |

---

## Síntese das escolhas colunares e de serialização

As decisões de armazenamento analítico e de replicação lógica foram decididas e medidas em detalhes em seus respectivos ADRs:
- **Delta Lake sobre Parquet, partição por ano (`ano`) e compressão `zstd`:** formalizado e medido com dados reais no [ADR 0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md).
- **CDC lógico por slot nativo, confirmação tardia e semântica *effectively-once*:** formalizado e demonstrado no [ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md).

---

## Decisão

1. **Ingerir as matérias de conselho do DOU no OLTP** (`public.ato`) a partir dos **Dados Abertos da Imprensa Nacional** (`make ingest-mensal MES=AAAA-MM`), filtrando apenas os atos pertinentes (96 matérias em agosto/2026) e enviando órgãos não mapeados (626 nomes novos) para a fila de curadoria de aliases ([ADR 0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)).
2. **Propagar mudanças para o Delta Lake via CDC lógico com consumidor próprio** ([ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md)), utilizando decodificação nativa do PostgreSQL (`test_decoding`), protocolo de confirmação tardia (*peek* -> grava Delta -> confirma LSN) e `MERGE` idempotente por `ato_id` via biblioteca leve `deltalake`.
3. **Descartar Debezium com Kafka** em razão do custo de 4 containers permanentes e ~2 GB de RAM ociosa em máquina local, desproporcional ao volume de ~96 atos/mês do domínio.

---

## Consequências

**O que ganhamos:**
- **Operação leve e sustentável:** todo o ambiente roda no notebook pessoal da pesquisadora consumindo recursos mínimos, sem dependência de Java ou serviços de mensageria complexos.
- **Rastreabilidade completa de curadoria:** atos do DOU possuem integridade referencial 3NF com revisores e classificações humanas, permitindo auditoria rigorosa de versões e retificações.
- **Tolerância a falhas e reprocessamento idempotente:** a semântica *at-least-once* na leitura combinada com *MERGE* idempotente no destino garante que quedas forçadas do consumidor não gerem linhas duplicadas nem inconsistência nos indicadores analíticos ([ADR 0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md)).
- **Independência de login no DOU:** ingestão mensal pública e sem bloqueio, cobrindo o histórico desde 2002.

**O que perdemos:**
- **Risco operacional de retenção de WAL:** se o slot de replicação lógica for criado e abandonado sem um consumidor ativo, o PostgreSQL acumula arquivos de WAL e pode encher o disco da máquina (mitigado pelo comando de limpeza `make cdc-drop`).
- **Sobrecarga transitória no decodificador:** o plugin `test_decoding` decodifica transações de todas as tabelas em formato textual; durante ingestões volumosas em lote, linhas de `conteudo` precisam ser filtradas e descartadas na memória do processo Python.
- **Latência de disponibilidade do lote mensal:** os dados abertos mensais são consolidados pela Imprensa Nacional cerca de 10 a 15 dias após o fechamento do mês; para publicações do dia corrente, a operação requer baixar o ZIP no navegador e rodar `make persist`.
- **Duplicação de armazenamento entre camadas:** o texto do ato reside em XML no bronze (`data/bronze/`), em `public.ato` no PostgreSQL e na tabela consolidada do Delta Lake (`data/silver/atos/`).

**O que se torna irreversível:**
- Nada estrutural. Os dados na camada analítica permanecem em formato padrão Parquet/Delta Lake. Se no futuro o volume exigir migração para Kafka ou Iceberg, o modelo de chave primária (`ato_id`), particionamento anual e checksums já está consolidado.

---

## Gatilho de revisão

Esta decisão deve ser revista se:
1. **O volume de atos ou a exigência de latência ultrapassar o que o `make cdc` sob demanda aguenta**, ou se múltiplos sistemas heterogêneos passarem a consumir as mudanças do OLTP concorrentemente (justificando reavaliar Debezium e Apache Kafka, conforme ADR 0007).
2. **O slot de replicação lógica acumular mais de 1 GB de WAL retido** por ausência prolongada de execução do consumidor.
3. **A Imprensa Nacional disponibilizar uma API oficial autenticada e pública** sem bloqueio a scripts automatizados para ingestão diária em lote.
