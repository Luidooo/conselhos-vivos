# 0006 — Armazenar a camada analítica em tabelas Delta particionadas por ano e comprimidas com zstd

- **Status:** proposto
- **Data:** 2026-10-13
- **Decisores:** Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

A Entrega E2 exige uma camada de armazenamento analítico em formato aberto colunar com controle transacional e suporte a reexecução. No nosso pipeline, o dado passa por duas fontes transacionais: os 215 atos históricos da planilha da pesquisadora (`origem = 'PLANILHA'`) e as matérias de conselho extraídas do DOU (`origem = 'DOU'`), ambas consolidadas no PostgreSQL 16 com suas respectivas tipologias em `classificacao_vigente` ([ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)).

A pergunta deste ADR é: **como estruturar a camada analítica para alimentar os indicadores de vitalidade e o assistente de pesquisa sem violar a restrição de operação simples pela pesquisadora.**

**Caracterização da carga analítica:**

| Dimensão | Valor | Fonte |
|---|---|---|
| Volume inicial | 215 atos históricos (2003–2020) | Carga da planilha (#3) |
| Volume recorrente | ~96 atos de conselho/mês (~1.150 atos/ano na Seção 1) | Medição de agosto/2026 nos dados abertos (#43) |
| Tamanho médio do ato | ~1,9 KB (resumo/ementa) a ~42 KB (transcrição completa em HTML) | `relatorio-planilha.md` e amostras do DOU |
| Padrão de acesso analítico | Varredura colunar filtrando por conselho e agrupando por ano e tipologia (`DEF`, `FISC`, `GEST`, `AUTO`, `IP`) + busca textual em `conteudo` | Indicador de vitalidade e página "Jornada do dado" |
| Latência tolerada | Lote (executado sob demanda com `make lake` ou agendado periodicamente) | — |
| Operação | Notebook pessoal da pesquisadora (Docker Compose, sem cluster distribuído e sem JVM) | Briefing da disciplina |

**Critérios de projeto:**
- **R1 Formato aberto:** arquivos colunares legíveis diretamente por motores analíticos leves (DuckDB, Polars);
- **R2 Idempotência estrita:** rodar a sincronização repetidas vezes não pode duplicar registros nem corromper arquivos;
- **R3 Prevenção de arquivos pequenos (*small files problem*):** o particionamento não pode gerar fragmentação excessiva de arquivos no disco local;
- **R4 Leveza operacional:** o processo de escrita analítica deve rodar em container leve, sem depender de Spark ou Java.

---

## Alternativas consideradas

### A. Opção nula: manter as análises no PostgreSQL (via views)

Viável tecnicamente para o volume atual de centenas de atos. Foi descartada porque:
1. Viola o requisito da disciplina de transição para armazenamento colunar aberto;
2. Agregações com varredura completa de texto e cálculos de séries históricas competem por recursos com a aplicação de curadoria transacional;
3. Não entrega portabilidade direta para ferramentas como DuckDB e pipelines analíticos modernos.

### B. Arquivos Parquet planos organizados em pastas (Raw Parquet)

Gravar arquivos `.parquet` diretamente no disco particionados em diretórios.  
**Desvantagem:** Parquet puro não possui log transacional ACID. Para garantir idempotência em caso de reprocessamento ou atualização de curadoria, o job é forçado a sobrescrever a partição inteira (*overwrite*) ou a tolerar duplicatas. Falhas no meio da escrita deixam arquivos corrompidos ou partições em estado inconsistente.

### C. Tabela Apache Iceberg (via PyIceberg)

O Apache Iceberg é um formato de tabela aberto maduro. Diferente do ecossistema tradicional de Big Data, o Iceberg conta com biblioteca em Python puro (`pyiceberg`, sem JVM/Spark) e suporte a leitura no DuckDB via extensão `iceberg`.

**Comparação explícita com Delta Lake:**
1. **Catálogo de metadados:** O Iceberg exige ou presume um catálogo externo (REST Catalog, Nessie, Hive Metastore ou SQLite) para coordenar os ponteiros de versão de metadados (`metadata.json`). O Delta Lake armazena seu log transacional (`_delta_log/`) diretamente no sistema de arquivos local (`file://`), tornando a tabela completamente autocontida em uma pasta única (`data/silver/atos/`), sem serviços adicionais.
2. **Maturidade de escrita e `MERGE` em Python puro:** A biblioteca `deltalake` (baseada no motor Rust `delta-rs`) oferece suporte transacional completo e maduro a operações de `MERGE INTO` com predicados arbitrários (`when_matched_update_all`, `when_not_matched_insert_all`) sobre arquivos locais. No PyIceberg, o suporte a escrita transacional e upserts em arquivos locais ainda possui restrições e depende de catálogo configurado.
3. **Ergonomia no DuckDB:** O DuckDB lê Delta Lake apontando diretamente para o diretório (`delta_scan('data/silver/atos')`). No Iceberg, consultas sem catálogo necessitam apontar para arquivos de metadados específicos (`iceberg_scan('.../metadata/v1.metadata.json')`), dificultando a automação de consultas pós-ingestão.

Por dispensar qualquer serviço de catálogo e oferecer `MERGE` ACID robusto em container leve, o Delta Lake é preferível para a operação local da pesquisadora.

### D. Tabela Delta Lake com engine leve (`deltalake`) e DuckDB (escolhida)

Delta Lake adiciona um log transacional ACID em JSON (`_delta_log/`) sobre arquivos Parquet. Permite operações de `MERGE` (upsert) na chave primária analítica, tornando a ingestão analítica idempotente por definição. A escrita é feita via biblioteca nativa em Python (`deltalake`, compilada em Rust/Apache Arrow, sem JVM), e a leitura de consumo é feita via DuckDB com a extensão `delta`.

---

## Decisões de modelagem física

### 1. Granularidade de partição: por ano (`ano = EXTRACT(YEAR FROM data_publicacao)`)

A escolha da chave de partição decorre diretamente do padrão de acesso das consultas analíticas:

- **Por que por ano e não por dia/mês:** Com ~250 dias úteis no ano e média de 3 a 5 atos de conselho por dia útil, a partição diária gera centenas de arquivos Parquet minúsculos (1 a 3 KB cada). O overhead de abertura de arquivos e leitura de metadados no sistema de arquivos supera o tempo de processamento dos dados (*small files problem*). O particionamento anual consolida a leitura em poucos I/Os sequenciais.
- **Por que por ano e não por órgão:** O indicador de vitalidade calcula o silêncio e a distribuição comparando **todos os 82 conselhos simultaneamente**. Particionar por órgão forçaria qualquer agregação global a abrir e concatenar 82 arquivos distintos por ano.
- **Eficiência de poda (*Partition Pruning*):** As consultas do observatório filtram por marcos regulatórios ou mandatos (ex.: `WHERE ano >= 2020` para a era INLABS, ou cortes de planos plurianuais). A partição por ano permite ao DuckDB realizar poda de partição diretamente na árvore de diretórios (`data/silver/atos/ano=AAAA/`), eliminando arquivos fora do escopo da consulta antes de ler qualquer byte do disco.

### 2. Algoritmo de compressão: `zstd`

A escolha do codec `zstd` (Zstandard) é justificada pelo perfil de acesso misto (agregações numéricas + varredura textual em `conteudo`) e validada por medições empíricas no DuckDB:

- **Padrão de acesso com dados volumosos de texto:** A coluna `conteudo` concentra HTMLs completos (até 42 KB por ato). O algoritmo `zstd` utiliza compressão baseada em dicionários e entropia Finely Tuned (FSE), muito mais eficiente para textos estruturados e HTML com tags repetitivas do que algoritmos baseados exclusivamente em LZ77 rápido como o Snappy.
- **Medição empírica no DuckDB (200 repetições):**

  Com os 311 atos reais (215 da planilha + 96 do DOU de agosto/2026):

  | Codec | Tamanho em disco | Agregação (tipologia por conselho e ano) | Busca no texto (`conteudo`) |
  |---|---|---|---|
  | Snappy | 1.045 KB | 0,85 ms | 9,64 ms |
  | **Zstd** | **743 KB (−29%)** | **0,86 ms** | **9,49 ms** |

  Com os 215 atos da planilha (conforme `docs/adr/medicoes/0006-camada-analitica/resultados.json`):
  - Snappy: 375,6 KB | agregação: 6,37 ms | texto: 7,09 ms
  - Zstd: 299,3 KB (−20,3%) | agregação: 5,92 ms | texto: 7,08 ms

- **Conclusão da medição:** O tempo de descompressão empata na prática em ambas as cargas analíticas (diferença inferior a 0,02 ms em agregações e ligeira vantagem para o Zstd em busca textual), enquanto o **Zstd ocupa de 20% a 29% menos espaço em disco**.
- **Fixação no código:** O codec é configurado explicitamente no código via `WriterProperties(compression="ZSTD")` tanto na escrita inicial (`write_deltalake`) quanto no merge (`DeltaTable.merge`), evitando depender de configurações implícitas das ferramentas.

### 3. Modelo da tabela: consolidada / desnormalizada (`data/silver/atos/`)

Diferente do OLTP (que é normalizado em 3NF com `orgao`, `orgao_nome`, `ato`, `classificacao` e `revisor`), a camada analítica adota **uma tabela consolidada** contendo:
- Chave OLTP e rastreabilidade: `ato_id` (PK no Postgres), `origem`, `id_origem` (`id_dou` ou `id_planilha`), `versao`;
- Atributos temporais: `data_publicacao`, `ano` (coluna de partição);
- Atributos do órgão: `orgao_id`, `orgao_nome` (vigente na data da publicação com fallback para o vigente atual via `LEFT JOIN`, conforme ADR 0004), `orgao_sigla`, `codigo_siorg`;
- Conteúdo: `ref_legal`, `ementa`, `conteudo`;
- Curadoria vigente: `tipologia_sigla` (extraída da view `classificacao_vigente`, priorizando o revisor humano caso exista), `revisor_tipo`;
- Auditoria analítica: `checksum` (hash MD5 de todos os atributos) e `atualizado_em` (timestamp UTC).

Essa desnormalização elimina a necessidade de `JOIN` em consultas analíticas e simplifica o cálculo do indicador de silêncio e distribuição de tipologia.

### 4. Idempotência por `MERGE` na chave primária do ato (`ato_id`)

O job analítico lê do OLTP e executa `MERGE` na tabela Delta usando como predicado de junção a chave primária única do ato no OLTP:
```text
predicate = "target.ato_id = source.ato_id"
```
- `WHEN MATCHED AND target.checksum != source.checksum THEN UPDATE`
- `WHEN NOT MATCHED THEN INSERT`

**Vantagens sobre a chave composta anterior com `orgao_id`:**
- **Atualização correta em unificação de conselhos:** Se o órgão de um ato for retificado no OLTP (por exemplo, decisão de identidade de conselho conforme ADR 0004), o predicado encontra a linha pelo `ato_id` e atualiza `orgao_id`, `orgao_nome` e `orgao_sigla`. A chave anterior incluía `orgao_id`, o que causava inserção de uma linha duplicada mantendo a versão antiga no lake.
- **Checksum abrangente:** O hash cobre `ementa`, `conteudo`, `tipologia`, `orgao_id`, `orgao_nome`, `orgao_sigla`, `codigo_siorg`, `revisor_tipo`, `ref_legal` e `data_publicacao`. Qualquer alteração nessas colunas dispara a atualização atômica da linha sem criar duplicações.
- **Idempotência estrita:** Reexecutar `make lake` consecutivamente resulta em `inseridas=0`, `atualizadas=0` e mantém a tabela idêntica.

---

## Medição e verificação

As medições são reproduzíveis via script dedicado no repositório:
`docker compose run --rm lake python docs/adr/medicoes/0006-camada-analitica/bench.py`

**Resultados reais medidos com os 215 atos da planilha da pesquisadora:**

| Métrica | Partição diária | Partição anual (adotada) |
|---|---|---|
| Quantidade de arquivos Parquet | 112 arquivos | 12 arquivos (anos 2003–2009, 2011, 2013, 2016, 2017, 2020) |
| Tamanho total em disco | 1.376,7 KB | 299,3 KB (4,6× menor devido ao fim do overhead de metadados) |
| Tempo de agregação no DuckDB | 16,72 ms | 4,90 ms (3,4× mais rápido) |
| Overhead de pastas no disco | Alto (112 subdiretórios `ano=.../data_publicacao=...`) | Mínimo (12 subpastas `ano=AAAA/`) |
| 1ª execução (`make lake`) | — | `inseridas=215, atualizadas=0, inalteradas=0` |
| 2ª execução (`make lake`) | — | `inseridas=0, atualizadas=0, inalteradas=215` |

*(Com a ingestão de agosto/2026, a partição anual passa para 13 arquivos e totaliza 311 atos, mantendo o mesmo comportamento).*

**Consulta de validação analítica no DuckDB:**
```sql
INSTALL delta;
LOAD delta;

SELECT 
    orgao_nome,
    tipologia_sigla,
    count(*) AS total_atos
FROM delta_scan('data/silver/atos')
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

---

## Decisão

Adotamos **Delta Lake** como formato da camada analítica em `data/silver/atos/`, particionada por **ano de publicação** (`ano`), comprimida com **`zstd`** (`WriterProperties(compression="ZSTD")`), sincronizada a partir do OLTP por um job idempotente via `MERGE` por `ato_id` encapsulado no comando **`make lake`** (serviço `lake` no Compose), e consultada analiticamente via **DuckDB**.

---

## Consequências

**O que ganhamos:**
- **Zero arquivos pequenos:** arquivos consolidados por ano mantêm a tabela saudável para leitura local;
- **Compressão eficiente sem perda de latência:** Zstd reduz em até 29% o tamanho em disco comparado ao Snappy sem impactar o tempo de leitura analítica;
- **Idempotência estrita e suporte a retificação:** `MERGE` baseado em `ato_id` suporta reclassificações e unificações de órgão sem duplicar linhas;
- **Alta performance em agregações:** o DuckDB lê as colunas de tipologia e conselho sem carregar o HTML completo da coluna `conteudo` na memória;
- **Simplicidade operacional:** executado através de um container Python leve (`deltalake`), sem JVM, sem cluster Spark e sem alterar o limite de máquina da pesquisadora.

**O que perdemos:**
- **Sincronização em lote:** a camada analítica reflete o estado do OLTP no momento do `make lake`, exigindo execução do comando para atualizar novos atos ou reclassificações humanas;
- **Histórico de versões no disco:** operações de `UPDATE`/`MERGE` geram novas versões de arquivos Parquet sem apagar os antigos imediatamente até que uma limpeza via `VACUUM` seja executada.

**O que se torna irreversível:**
- Nada estrutural. Por baixo do log Delta estão arquivos Parquet convencionais. Se no futuro a squad optar por Parquet puro ou Iceberg, os próprios dados já estão no formato colunar correto.

---

## Gatilho de revisão

- **Se o volume anual de atos de conselho ultrapassar 500.000 registros por ano** (o que justificaria subparticionamento por mês para manter os arquivos abaixo de 128 MB);
- **Se a pesquisadora exigir análise analítica em tempo real no momento exato do clique da curadoria** (o que justificaria consultar a view do PostgreSQL diretamente em vez de materializar a camada analítica em lote);
- **Se a extensão `delta` do DuckDB apresentar incompatibilidade de versão** com o protocolo gerado pela biblioteca `deltalake`.
