# 0005 — Armazenar a camada analítica em tabelas Delta particionadas por ano e comprimidas com snappy

- **Status:** proposto
- **Data:** 2026-10-13
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

A Entrega E2 exige uma camada de armazenamento analítico em formato aberto colunar com controle transacional e suporte a reexecução. No nosso pipeline, o dado passa por duas fontes transacionais: os 215 atos históricos da planilha da pesquisadora (`origem = 'PLANILHA'`) e as matérias de conselho extraídas do DOU (`origem = 'DOU'`), ambas consolidadas no PostgreSQL 16 com suas respectivas tipologias em `classificacao_vigente` ([ADR 0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)).

A pergunta deste ADR é: **como estruturar a camada analítica para alimentar os indicadores de vitalidade e o assistente de pesquisa sem violar a restrição de operação simples pela pesquisadora.**

**Caracterização da carga analítica:**

| Dimensão | Valor | Fonte |
|---|---|---|
| Volume inicial | 215 atos históricos (2003–2020) | Carga da planilha (#3) |
| Volume recorrente | ~96 atos de conselho/mês (~1.150 atos/ano na Seção 1) | Medição de agosto/2026 nos dados abertos (#43) |
| Tamanho médio do ato | ~1,9 KB (resumo/ementa) a ~42 KB (transcrição completa em HTML) | `relatorio-planilha.md` e amostras do DOU |
| Padrão de acesso analítico | Varredura colunar filtrando por conselho e agrupando por ano e tipologia (`DEF`, `FISC`, `GEST`, `AUTO`, `IP`) | Indicador de vitalidade e página "Jornada do dado" |
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

### C. Lakehouse completo com Apache Spark / Apache Iceberg

Padrão de mercado para grandes volumes corporativos.  
**Desvantagem:** Incompatível com o princípio da squad e a restrição da pesquisadora. Exige JVM, download de imagens pesadas (>1 GB), alocação massiva de memória RAM e complexidade de manutenção desnecessária para menos de 10.000 registros por ano.

### D. Tabela Delta Lake consolidada com escrita via engine leve (`deltalake`) e consulta via DuckDB (escolhida)

Delta Lake adiciona um log transacional ACID em JSON (`_delta_log/`) sobre arquivos Parquet. Permite operações de `MERGE` (upsert) na chave primária analítica, tornando a ingestão analítica idempotente por definição. A escrita é feita via biblioteca nativa em Python (`deltalake`, baseada em Rust/Apache Arrow, sem dependência de JVM), e a leitura de consumo é feita via DuckDB com a extensão `delta`.

---

## Decisões de modelagem física

### 1. Granularidade de partição: por ano (`ano = EXTRACT(YEAR FROM data_publicacao)`)

A escolha da chave de partição decorre diretamente do padrão de acesso das consultas analíticas:

- **Por que por ano e não por dia/mês:** Com ~250 dias úteis no ano e média de 3 a 5 atos de conselho por dia útil, a partição diária geraria ~250 arquivos Parquet minúsculos (1 a 3 KB cada). O overhead de abertura de arquivos e leitura de metadados no sistema de arquivos superaria o tempo de processamento dos dados (*small files problem*). O arquivo anual (~50 a 100 KB) consolida a leitura em um único I/O sequencial por ano.
- **Por que por ano e não por órgão:** O indicador de vitalidade calcula o silêncio e a distribuição comparando **todos os 82 conselhos simultaneamente**. Particionar por órgão forçaria qualquer agregação global a abrir e concatenar 82 arquivos distintos por ano.
- **Eficiência de poda (*Partition Pruning*):** As consultas do observatório filtram por marcos regulatórios ou mandatos (ex.: `WHERE ano >= 2020` para a era INLABS, ou cortes de planos plurianuais). A partição por ano permite ao DuckDB realizar poda de partição diretamente na árvore de diretórios (`data/silver/atos/ano=AAAA/`), eliminando até 80% dos arquivos do escopo da consulta antes de ler qualquer byte do disco.

### 2. Algoritmo de compressão: `snappy`

A escolha do codec `snappy` é orientada pela assimetria entre as colunas e o perfil de leitura do DuckDB:

- **Isolamento de colunas pesadas:** A coluna `conteudo` concentra a maior parte dos bytes (HTMLs de até 42 KB), enquanto as consultas analíticas de vitalidade agregam apenas colunas leves (`orgao_sigla`, `tipologia_sigla`, `ano`). Por ser um formato colunar, o DuckDB lê e descomprime apenas os blocos dessas colunas leves, ignorando completamente os blocos da coluna `conteudo`.
- **Foco em taxa de descompressão (CPU-bound):** Para o volume total do projeto (algumas dezenas de megabytes ao ano), o armazenamento local em disco não é gargalo. O objetivo primordial da camada de consumo é resposta sub-milisegundo no notebook da pesquisadora. O `snappy` prioriza velocidade extrema de descompressão (~250 a 500 MB/s por núcleo de CPU) com baixíssimo custo computacional, superando o `gzip` (lento para descompressão analítica) e o `zstd` em níveis altos (cujo ganho marginal de compressão em datasets pequenos não compensa o ciclo de CPU gasto).
- **Interoperabilidade nativa:** O `snappy` é o codec padrão compilado nativamente no leitor do DuckDB e no `deltalake` (Rust), garantindo funcionamento hermético em qualquer ambiente sem necessidade de bibliotecas ou flags de compilação adicionais.

### 3. Modelo da tabela: consolidada / desnormalizada (`data/silver/atos/`)

Diferente do OLTP (que é normalizado em 3NF com `orgao`, `orgao_nome`, `ato`, `classificacao` e `revisor`), a camada analítica adota **uma tabela consolidada** contendo:
- Chave do ato: `origem`, `id_origem` (`id_dou` ou `id_planilha`), `versao`;
- Atributos temporais: `data_publicacao`, `ano` (coluna de partição);
- Atributos do órgão: `orgao_id`, `orgao_nome` (vigente na data da publicação com fallback para o vigente atual, conforme ADR 0004), `orgao_sigla`, `codigo_siorg`;
- Conteúdo: `ref_legal`, `ementa`, `conteudo`;
- Curadoria vigente: `tipologia_sigla` (extraída da view `classificacao_vigente`, priorizando o revisor humano caso exista), `revisor_tipo`;
- Auditoria analítica: `checksum` (hash MD5 dos campos mutáveis) e `atualizado_em` (timestamp UTC).

Essa desnormalização elimina a necessidade de `JOIN` em consultas analíticas e simplifica o cálculo do indicador de silêncio e distribuição de tipologia.

### 4. Idempotência por `MERGE`

O job analítico lê do OLTP e executa `MERGE` na tabela Delta usando como predicado de junção `(origem, id_origem, versao, orgao_id)`:
- `WHEN MATCHED AND target.checksum != source.checksum THEN UPDATE`
- `WHEN NOT MATCHED THEN INSERT`

O `checksum` garante que alterações em `conteudo`, `ementa`, `tipologia_sigla` ou `orgao_id` sejam atualizadas atômica e corretamente, enquanto linhas idênticas não geram novas versões de arquivos. Rodar o comando `make lake` repetidas vezes com os mesmos dados no OLTP resulta em 0 inserções, 0 atualizações e mantém o estado do Delta inalterado.

---

## Medição e verificação

**Condição de teste:** Carga dos 215 atos da planilha da pesquisadora, processados pelo serviço `lake` do Docker Compose.

| Métrica | Partição diária (simulada) | Partição anual (adotada) |
|---|---|---|
| Quantidade de arquivos Parquet | > 120 arquivos | 18 arquivos (2003 a 2020 históricos) |
| Tamanho médio por arquivo | 1,8 KB | ~65 KB |
| Tempo de agregação no DuckDB (Q2) | 14,2 ms | 2,1 ms (6,7× mais rápido) |
| Overhead de pastas no disco | Alto (dezenas de subpastas `ano=.../mes=.../dia=...`) | Mínimo (`ano=AAAA/`) |
| 1ª execução (`make lake`) | — | `inseridas=215, atualizadas=0, inalteradas=0` |
| 2ª execução (`make lake`) | — | `inseridas=0, atualizadas=0, inalteradas=215` |

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

Adotamos **Delta Lake** como formato da camada analítica em `data/silver/atos/`, particionada por **ano de publicação** (`ano`), comprimida com **`snappy`**, populada a partir do OLTP por um job idempotente via `MERGE` encapsulado no comando **`make lake`** (serviço `lake` no Compose), e consultada analiticamente via **DuckDB**.

---

## Consequências

**O que ganhamos:**
- **Zero arquivos pequenos:** arquivos consolidados por ano mantêm a tabela saudável para leitura local;
- **Idempotência nativa:** o log transacional Delta impede duplicação mesmo se o job for reexecutado múltiplas vezes;
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
---
