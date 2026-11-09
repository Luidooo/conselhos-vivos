# E3: camada analítica transformada, testada e orquestrada. Plano de implementação

> **Para agentes:** use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhar.

**Objetivo:** cumprir os oito itens do checklist da E3 ([enunciado](https://unb-bd2.github.io/PlanoEnsino/projeto/e3/)) e responder à pergunta da E1, *quais conselhos nacionais de participação social ainda estão funcionando?*, num painel.

**Arquitetura:** o dbt, com o adaptador do DuckDB, lê a silver em Delta, que já existe desde a E2, e lê a curadoria no Postgres, conectado só para leitura. Ele grava a gold num arquivo DuckDB, com staging e marts. O Dagster orquestra um grafo mensal: atos do mês, silver e gold. A partição mensal dá o backfill e a política de retry dá o retry. Um painel em Streamlit lê a gold. Esse é o desenho da [arquitetura final](../../site/arquitetura.md), só com as peças da E3.

**Ferramentas:** dbt-core + dbt-duckdb, Dagster + dagster-dbt, Streamlit, DuckDB 1.5.6 (o mesmo do lake), Postgres 16, Docker Compose + make.

## Restrições globais

- Tudo roda por `make` e Docker Compose, como o resto do projeto. Nada é instalado no host.
- Serviços novos seguem o molde do `lake` e do `dou`: imagem `python:3.12.14-slim`, `pip install` com o volume `pipcache` e `chown` para `DOCKER_UID:DOCKER_GID` do que gravarem em `data/`.
- Porta publicada só em `127.0.0.1`, como o banco e o pgAdmin.
- `duckdb==1.5.6`, `psycopg[binary]==3.2.5`, `deltalake==1.6.6`, `pyarrow==18.0.0`: as versões que o lake já fixa. O dbt e o Dagster vão com versão exata.
- O OLTP só é lido. A gold nunca escreve no Postgres na E3; o ETL reverso é da E4.
- Nenhum teste ou demonstração deixa o banco de trabalho diferente do que encontrou.
- Commit e push só com o ok da Luiza. Cada tarefa termina com o diff em stage.
- Toda tarefa que usa IA ganha uma entrada no `AI-USAGE.md`, no formato das existentes.
- Nos YAML do dbt, use `data_tests:` e, nos testes com parâmetro, `arguments:`. `tests:` ainda funciona, mas é a forma antiga, e o dbt 2 exige `arguments`.
- O ADR da E3 é o **0009**. O 0008 está reservado para a migração Go → Python (#57).

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `dbt/dbt_project.yml`, `dbt/profiles.yml` | projeto dbt; a gold em `/data/gold/conselhos.duckdb`; o Postgres anexado só para leitura |
| `dbt/models/staging/` | `stg_atos` (a versão mais recente de cada matéria) e `stg_orgao_nome` |
| `dbt/models/marts/` | `dim_conselho` (SCD tipo 2), `fct_ato`, `fct_conselho_mes`, `mart_vitalidade`, `freshness_vitalidade` |
| `dbt/models/*.yml` | fontes, descrição, granularidade e testes genéricos |
| `dbt/tests/` | testes singulares: volume, vigências, distribuição e SLA |
| `src/orquestracao/__init__.py` | o grafo do Dagster: assets, retry, partição, agenda |
| `src/orquestracao/requirements.txt` | dbt, Dagster e as dependências do dou e do lake |
| `src/painel/requirements.txt` | as versões do painel, fixadas já na Tarefa 1 |
| `src/painel/app.py` | o painel |
| `sql/007_*.sql` | o índice que sair da Tarefa 7 |
| `scripts/demo_retry.sh`, `scripts/demo_backfill.sh` | as duas demonstrações da orquestração |
| `docs/adr/0009-*.md`, `docs/adr/medicoes/0009-gold/` | o ADR e as medições |
| `site/entrega-e3.md` | a página da entrega, no molde da E2 |

## Quem faz o quê (sugestão)

As tarefas 2 a 5 dependem da 1. A 6 depende da 1. A 7 é independente. A 8 depende da 4. A 9 fecha tudo.

| Tarefa | Pode ir para |
|---|---|
| 1. Projeto dbt e staging | quem pegar primeiro: destrava o resto |
| 2. Dimensão SCD | uma pessoa |
| 3 e 4. Fatos, mart e testes | uma pessoa |
| 5. Freshness e SLA | junto com a 4 |
| 6. Dagster, retry e backfill | uma pessoa |
| 7. EXPLAIN antes e depois | uma pessoa, já |
| 8. Painel | uma pessoa |
| 9. ADR, página, tag | todos revisam |

---

### Tarefa 0: dados para trabalhar

O banco precisa de alguns meses do DOU para o fato mensal, o teste de distribuição e o backfill fazerem sentido. Hoje o bronze tem agosto e setembro de 2026.

- [ ] **Passo 1: subir o banco e conferir o que ele tem**

```bash
make up
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select origem, count(*), min(data_publicacao), max(data_publicacao) from ato group by 1"'
```

Esperado: `PLANILHA|215|2003-...|2020-...` e uma linha `DOU`.

- [ ] **Passo 2: conferir se todo ato aponta para um conselho**

O fato liga cada ato a `dim_conselho`, que só tem conselhos. Se esta consulta devolver linhas, a Tarefa 3 precisa decidir o que fazer com elas antes do teste de relacionamento.

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select a.orgao_id, count(*) from ato a left join conselho c using (orgao_id) where c.orgao_id is null group by 1"'
```

O `persist` aceita qualquer órgão de `orgao_nome`, não só conselho. Resultado em 06/11/2026: 92 atos do DOU, de 19 órgãos, estão fora da tabela `conselho`, que tem só os 5 da planilha. A Tarefa 3 (#70) precisa decidir o que fazer com eles. Detalhes na #68.

- [ ] **Passo 3: não baixar nada agora**

Os meses extras entram pelo backfill da Tarefa 6, que é a demonstração pedida. Até lá, as tarefas 1 a 5 usam agosto e setembro: `make ingest-mensal MES=2026-09` se setembro ainda não estiver no banco.

---

### Tarefa 1: projeto dbt, serviço e staging

**Arquivos:**
- Criar: `dbt/dbt_project.yml`, `dbt/profiles.yml`, `dbt/models/fontes.yml`, `dbt/models/staging/stg_atos.sql`, `dbt/models/staging/stg_orgao_nome.sql`, `dbt/models/staging/staging.yml`
- Criar: `src/orquestracao/requirements.txt`, `src/painel/requirements.txt`
- Modificar: `docker-compose.yml` (serviço `orquestrador`), `Makefile` (alvo `gold`), `.gitignore`, `AI-USAGE.md`

**Interfaces:**
- Produz: `ref('stg_atos')`, com uma linha por matéria (a chave `materia`), e as colunas da silver mais `mes`.
- Produz: `ref('stg_orgao_nome')`, com `orgao_nome_id, orgao_id, nome, data_inicio, data_fim`.
- Produz: o comando `make gold`, que roda `dbt build` no serviço `orquestrador`.

- [ ] **Passo 1: fixar as versões**

Versões conferidas no PyPI em 04/11/2026. O `dbt-duckdb` aceita `duckdb>=1.0.0`, o `dagster-dbt` aceita `dbt-core<1.13`, e o `dagster-dbt` 0.29.28 exige `dagster==1.13.28`. Quem prova que tudo convive é o `pip` do Passo 6.

`src/orquestracao/requirements.txt`:

```text
-r ../dou/requirements.txt
-r ../lake/requirements.txt
dbt-core==1.12.6
dbt-duckdb==1.11.1
dagster==1.13.28
dagster-webserver==1.13.28
dagster-dbt==0.29.28
```

`src/painel/requirements.txt`:

```text
duckdb==1.5.6
streamlit==1.66.1
```

Os `-r` repetem `psycopg` e `duckdb`, e isso não conflita: as versões são as mesmas.

- [ ] **Passo 2: o projeto dbt**

`dbt/dbt_project.yml`:

```yaml
name: conselhos_vivos
version: "1.0.0"
profile: conselhos_vivos
model-paths: ["models"]
test-paths: ["tests"]

models:
  conselhos_vivos:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

`dbt/profiles.yml` (versionado: não tem segredo, a senha vem do ambiente):

```yaml
conselhos_vivos:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: /data/gold/conselhos.duckdb
      extensions: [delta, postgres]
      attach:
        # A curadoria e os nomes dos órgãos vêm do OLTP, só para leitura.
        - path: "host=db dbname={{ env_var('PGDATABASE') }} user={{ env_var('PGUSER') }} password={{ env_var('PGPASSWORD') }}"
          type: postgres
          alias: oltp
          read_only: true
```

`dbt/models/fontes.yml`:

```yaml
version: 2

sources:
  - name: silver
    description: "Camada silver da E2, em Delta (ADR 0006)."
    meta:
      external_location: "delta_scan('/data/silver/{name}')"
    tables:
      - name: atos
        description: "Uma linha por versão de ato no OLTP, com o nome do órgão na época e a classificação vigente."

  - name: oltp
    description: "OLTP de curadoria (ADR 0001), anexado só para leitura."
    database: oltp
    schema: public
    tables:
      - name: orgao
      - name: orgao_nome
        description: "Histórico de nomes de cada órgão, com início e fim de vigência. É a origem da dimensão de variação lenta."
      - name: conselho
```

- [ ] **Passo 3: staging**

`dbt/models/staging/stg_atos.sql`:

```sql
-- Uma linha por matéria: a versão mais recente. Uma matéria do DOU é o id_dou; um ato da planilha é o próprio ato.
select
    *,
    date_trunc('month', data_publicacao)::date as mes,
    case when origem = 'DOU' then 'DOU:' || id_origem else 'PLANILHA:' || ato_id::varchar end as materia
from {{ source('silver', 'atos') }}
qualify row_number() over (partition by materia order by versao desc) = 1
```

`dbt/models/staging/stg_orgao_nome.sql`:

```sql
select id as orgao_nome_id, orgao_id, nome, data_inicio, data_fim
from {{ source('oltp', 'orgao_nome') }}
```

`dbt/models/staging/staging.yml`:

```yaml
version: 2

models:
  - name: stg_atos
    description: "Granularidade: uma linha por matéria publicada, na versão mais recente."
    columns:
      - name: materia
        data_tests: [unique, not_null]
      - name: ato_id
        data_tests: [unique, not_null]
      - name: data_publicacao
        data_tests: [not_null]
      - name: origem
        data_tests:
          - accepted_values:
              arguments:
                values: ['DOU', 'PLANILHA']

  - name: stg_orgao_nome
    columns:
      - name: orgao_nome_id
        data_tests: [unique, not_null]

unit_tests:
  - name: stg_atos_fica_com_a_versao_mais_recente_de_cada_materia
    description: "Retificação do DOU vira uma linha só. Atos da planilha com o mesmo id_origem continuam separados."
    model: stg_atos
    given:
      # format sql: a fonte é um delta_scan, e o dbt não consegue ler as colunas dela para montar a fixture.
      - input: source('silver', 'atos')
        format: sql
        rows: |
          select * from (values
            (1, 'DOU', 'A', 1, date '2026-08-03'),
            (2, 'DOU', 'A', 2, date '2026-08-10'),
            (3, 'PLANILHA', '7', 1, date '2003-01-08'),
            (4, 'PLANILHA', '7', 1, date '2004-02-09')
          ) as t(ato_id, origem, id_origem, versao, data_publicacao)
    expect:
      rows:
        - {materia: "DOU:A", ato_id: 2, mes: 2026-08-01}
        - {materia: "PLANILHA:3", ato_id: 3, mes: 2003-01-01}
        - {materia: "PLANILHA:4", ato_id: 4, mes: 2004-02-01}
```

O banco de trabalho não tem nenhum ato com versão acima de 1, então só este teste exercita a retificação.

- [ ] **Passo 4: o serviço `orquestrador`**

Em `docker-compose.yml`, depois do `cdc`. A porta, o `DAGSTER_HOME` e o comando do Dagster só entram na Tarefa 6, quando existir o que rodar:

```yaml
  # E3: dbt e Dagster no mesmo serviço, porque o Dagster roda o dbt, o dou e o lake.
  # Mesmo molde do lake: pip com cache em volume, chown do que gravar em data/.
  orquestrador:
    image: python:3.12.14-slim
    profiles: [e3]
    working_dir: /app
    environment:
      PYTHONPATH: /app/src:/tmp/site
      PGHOST: db
      PGUSER: ${POSTGRES_USER}
      PGPASSWORD: ${POSTGRES_PASSWORD}
      PGDATABASE: ${POSTGRES_DB}
      PIP_CACHE_DIR: /tmp/pipcache
      DBT_PROFILES_DIR: /app/dbt
      DOCKER_UID: ${DOCKER_UID:-1000}
      DOCKER_GID: ${DOCKER_GID:-1000}
    volumes:
      - ./src:/app/src:ro
      - ./dbt:/app/dbt
      - ./data/silver:/data/silver
      - ./data/gold:/data/gold
      - pipcache:/tmp/pipcache
    depends_on:
      db:
        condition: service_healthy
    entrypoint: ["sh", "-c", "pip install -q --disable-pip-version-check --root-user-action=ignore --no-warn-script-location --target /tmp/site -r /app/src/orquestracao/requirements.txt && export PATH=/tmp/site/bin:$$PATH && \"$$@\"; rc=$$?; chown -R $${DOCKER_UID}:$${DOCKER_GID} /data /app/dbt; exit $$rc", "sh"]
```

- [ ] **Passo 5: alvos no Makefile e `.gitignore`**

No `Makefile`, depois de `cdc-drop`:

```make
gold: .env ## E3: roda o dbt (modelos e testes) e grava a gold em data/gold/conselhos.duckdb (rode make lake antes)
	mkdir -p data/gold
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T orquestrador dbt build --project-dir /app/dbt
```

Acrescente `gold` à linha `.PHONY`.

No `.gitignore`, junto dos dados brutos:

```text
data/gold/**
data/dagster/**
dbt/target/
dbt/logs/
```

- [ ] **Passo 6: rodar**

```bash
make lake && make gold
```

Esperado: `Completed successfully`, com os dois modelos de staging e os testes deles em `PASS`. Se `delta_scan` não for encontrado, a extensão `delta` não carregou: confira `extensions` no `profiles.yml`.

O serviço instala as dependências a cada execução, como o `dou`. Medido em 06/11/2026: 62 s na primeira execução e 30 s nas seguintes.

Prove que o OLTP está só para leitura:

```bash
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T orquestrador dbt show --project-dir /app/dbt --inline "select database_name, readonly from duckdb_databases() where database_name = 'oltp'"
```

Esperado: `oltp | True`.

- [ ] **Passo 7: stage**

```bash
git add dbt src/orquestracao/requirements.txt src/painel/requirements.txt docker-compose.yml Makefile .gitignore AI-USAGE.md
git diff --cached --stat
```

---

### Tarefa 2: dimensão do conselho, com variação lenta

O OLTP já guarda o histórico: cada nome de órgão tem início e fim de vigência (ADR 0004). A dimensão é esse histórico como SCD tipo 2. Uma linha por nome, nunca sobrescrita.

**Arquivos:**
- Criar: `dbt/models/marts/dim_conselho.sql`, `dbt/models/marts/marts.yml`, `dbt/models/staging/stg_orgao.sql`, `dbt/models/staging/stg_conselho.sql`, `dbt/seeds/conselhos_excluidos.csv`, `dbt/tests/dim_no_maximo_uma_linha_atual_por_conselho.sql`, `dbt/tests/dim_inicio_aberto_so_no_nome_mais_antigo.sql`, `dbt/tests/dim_vigencias_nao_se_sobrepoem.sql`

**Interfaces:**
- Consome: `ref('stg_orgao_nome')`, `ref('stg_orgao')`, `ref('stg_conselho')` (só para a marca `eh_participativo`) e a seed `ref('conselhos_excluidos')`.
- Produz: `ref('dim_conselho')`, com `conselho_sk, orgao_id, nome, sigla, codigo_siorg, valido_de, inicio_nao_verificado, valido_ate, atual, eh_participativo`.
- Escopo: todo órgão que já teve um nome começando com "Conselho", menos a seed `conselhos_excluidos` ([ADR 0010](../adr/0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome.md)): 59 dos 82 órgãos. Com a tabela `conselho` seriam 5, nenhum renomeado.

- [ ] **Passo 1: os testes, antes do modelo**

`dbt/tests/dim_no_maximo_uma_linha_atual_por_conselho.sql`:

```sql
-- No máximo um nome vigente por conselho. Dois duplicam o conselho. Zero é o estado "extinto"
-- (todos os nomes encerrados) e não é erro: a pergunta da E3 é justamente quais ainda funcionam.
select orgao_id, count(*) filter (where atual) as atuais
from {{ ref('dim_conselho') }}
group by orgao_id
having count(*) filter (where atual) > 1
```

`dbt/tests/dim_inicio_aberto_so_no_nome_mais_antigo.sql`:

```sql
-- O início desconhecido (0001-01-01) só cabe no nome mais antigo do conselho. Um nome novo sem data
-- passaria despercebido, porque o coalesce da dimensão esconde o nulo do OLTP.
select a.orgao_id, a.conselho_sk
from {{ ref('dim_conselho') }} a
where a.inicio_nao_verificado
  and exists (
      select 1 from {{ ref('dim_conselho') }} b
      where b.orgao_id = a.orgao_id and b.valido_ate < a.valido_ate
  )
```

`dbt/tests/dim_vigencias_nao_se_sobrepoem.sql`:

```sql
-- Duas vigências do mesmo conselho que se cruzam fariam um ato casar com dois nomes e contar duas vezes.
select a.orgao_id, a.conselho_sk, b.conselho_sk as outro
from {{ ref('dim_conselho') }} a
join {{ ref('dim_conselho') }} b
  on a.orgao_id = b.orgao_id
 and a.conselho_sk < b.conselho_sk
 and a.valido_de <= b.valido_ate
 and b.valido_de <= a.valido_ate
```

- [ ] **Passo 2: rodar e ver falhar**

```bash
make gold
```

Esperado: erro de compilação, porque `dim_conselho` não existe.

- [ ] **Passo 3: o modelo**

`dbt/models/marts/dim_conselho.sql`:

```sql
-- SCD tipo 2: uma linha por nome que o conselho teve, com a vigência. Renomear é inserir, não sobrescrever.
-- Início nulo no OLTP (ADR 0004, ponto 4) vira limite aberto aqui, marcado em inicio_nao_verificado:
-- um valido_de nulo faria o fato descartar, sem erro, os atos desse conselho.
-- É conselho todo órgão que já teve "Conselho" no início do nome (ADR 0010), menos os da seed
-- conselhos_excluidos; vale por órgão, não por linha.
with escopo as (
    select orgao_id
    from {{ ref('stg_orgao_nome') }}
    group by orgao_id
    having bool_or(nome ilike 'conselho%')
       and not bool_or(nome in (select nome from {{ ref('conselhos_excluidos') }}))
)

select
    n.orgao_nome_id as conselho_sk,
    n.orgao_id,
    n.nome,
    o.sigla,
    o.codigo_siorg,
    coalesce(n.data_inicio, date '0001-01-01') as valido_de,
    n.data_inicio is null as inicio_nao_verificado,
    coalesce(n.data_fim, date '9999-12-31') as valido_ate,
    n.data_fim is null as atual,
    c.eh_participativo -- nulo = não avaliado pela pesquisadora, não falso
from {{ ref('stg_orgao_nome') }} n
join escopo e on e.orgao_id = n.orgao_id
join {{ ref('stg_orgao') }} o on o.orgao_id = n.orgao_id
left join {{ ref('stg_conselho') }} c on c.orgao_id = n.orgao_id
```

`dbt/models/marts/marts.yml`:

```yaml
version: 2

models:
  - name: dim_conselho
    description: >
      Dimensão de variação lenta (SCD tipo 2). Granularidade: uma linha por nome que um conselho
      teve, com valido_de e valido_ate. O nome vigente tem atual = true. O escopo é todo órgão que
      já teve "Conselho" no início do nome (ADR 0010), menos os da seed conselhos_excluidos.
    columns:
      - name: conselho_sk
        data_tests: [unique, not_null]
      - name: orgao_id
        data_tests: [not_null]
      # valido_de nunca é nulo (coalesce); o que importa é onde cabe o início aberto,
      # e isso o teste dim_inicio_aberto_so_no_nome_mais_antigo confere.
      - name: eh_participativo
        description: "Marca da pesquisadora. Nulo significa não avaliado, não falso."
      - name: inicio_nao_verificado
        description: "Verdadeiro quando o OLTP não tem a data de início do nome (ADR 0004, ponto 4). Nesse caso valido_de é 0001-01-01, um limite aberto, não uma data real."

seeds:
  - name: conselhos_excluidos
    description: "Órgãos com \"Conselho\" no nome que não são colegiados de participação social, fora da dimensão (ADR 0010, ponto 3). Chave: o nome."
    columns:
      - name: nome
        data_tests: [unique, not_null]
```

- [ ] **Passo 4: rodar e ver passar**

```bash
make gold
```

Esperado: `dim_conselho` criada e os dois testes singulares em `PASS`. Se `dim_vigencias_nao_se_sobrepoem` falhar, a falha é um achado do OLTP. Ela entra numa issue de curadoria, e o teste não é afrouxado.

- [ ] **Passo 5: conferir a variação lenta com um caso real**

```bash
docker compose --progress quiet run --rm -T --entrypoint python orquestrador -c "import duckdb; print(duckdb.connect('/data/gold/conselhos.duckdb', read_only=True).sql('select orgao_id, nome, valido_de, valido_ate, atual from dim_conselho where orgao_id in (select orgao_id from dim_conselho group by 1 having count(*) > 1) order by orgao_id, valido_de limit 12'))"
```

Esperado: conselhos com mais de um nome (CNDPI, CNDM e CNDH), cada nome numa linha, um só com `atual = true`. Esse print vai para o ADR 0009, em `docs/adr/medicoes/0009-gold/dim_conselho-renomeados.txt`.

O python do container não tem o `duckdb` fora do `dbt`. Para esta conferência, use `dbt show --project-dir /app/dbt --inline "select ... from {{ ref('dim_conselho') }}"`.

- [ ] **Passo 6: stage**

```bash
git add dbt && git diff --cached --stat
```

---

### Tarefa 3: o fato do ato

**Arquivos:**
- Criar: `dbt/models/marts/fct_ato.sql`, `dbt/tests/fct_volume_igual_ao_staging.sql`, `dbt/tests/fct_sem_data_no_futuro.sql`, `docs/adr/medicoes/0009-gold/fct_ato-fora-do-escopo.txt`
- Modificar: `dbt/models/marts/marts.yml`

**Interfaces:**
- Consome: `ref('stg_atos')`, `ref('dim_conselho')`.
- Produz: `ref('fct_ato')`, com `ato_id, materia, origem, data_publicacao, mes, orgao_id, conselho_sk, nome_aproximado, tipologia_sigla, revisor_tipo`.

**O que os dados mostraram (09/11/2026, banco com julho a setembro de 2026):**
- **Fora do escopo:** 146 dos 389 atos do DOU são de 9 órgãos que não estão na `dim_conselho`. São órgãos cujo nome não começa com "Conselho", como o Comitê-Executivo de Gestão, com 100 atos, ou órgãos excluídos pela seed, como o Conselho Monetário Nacional, com 27. Pelo ADR 0010, esses atos saem do fato. Os 215 da planilha estão todos dentro.
- **Critério de volume:** por isso, "o mesmo número de matérias da silver" vira "o mesmo número de matérias do staging dentro do escopo". O total de fora fica registrado para o ADR 0009.
- **Nome na data:** nenhum ato do escopo fica sem nome na data, graças ao início aberto da `dim_conselho`, e não há buracos entre vigências. Mesmo assim, o join tem de cobrir dois casos que o plano anterior tratava errado: o ato depois da extinção (o plano antigo daria o *primeiro* nome) e um buraco entre dois nomes. O `asof join` do DuckDB resolve os dois: escolhe o último nome que começou até a data.
- **Tipologias:** as do banco são `99`, `AUTO`, `DEF`, `FISC`, `GEST` e `IP`. Um ato sem classificação vira `SEM`.

- [ ] **Passo 1: os testes**

`dbt/tests/fct_volume_igual_ao_staging.sql`:

```sql
-- O fato tem uma linha por matéria do escopo (ADR 0010): nem perde ato no join com a dimensão, nem duplica.
-- E os 215 atos da planilha nunca podem sumir.
with esperado as (
    select count(*) as n from {{ ref('stg_atos') }}
    where orgao_id in (select orgao_id from {{ ref('dim_conselho') }})
),
real as (
    select count(*) as n, count(*) filter (where origem = 'PLANILHA') as planilha from {{ ref('fct_ato') }}
)
select esperado.n as esperado, real.n as real, real.planilha
from esperado, real
where esperado.n <> real.n or real.planilha < 215
```

`dbt/tests/fct_sem_data_no_futuro.sql`:

```sql
-- Data de publicação depois de hoje é erro de leitura do pubDate, não ato do futuro.
select ato_id, data_publicacao from {{ ref('fct_ato') }} where data_publicacao > current_date
```

Em `marts.yml`, dentro de `models:`, a granularidade por extenso, os testes de coluna e um teste unitário dos quatro casos do nome na data:

```yaml
  - name: fct_ato
    description: >
      Fato. Granularidade: uma linha por matéria publicada (a versão mais recente) de um conselho do
      escopo da dim_conselho (ADR 0010), ligada ao nome que o conselho tinha na data da publicação.
      nome_aproximado é verdadeiro quando a data cai fora da vigência do nome escolhido: antes do
      primeiro nome (fica com o mais antigo) ou depois do fim do último (fica com o último).
    columns:
      - name: ato_id
        data_tests: [unique, not_null]
      - name: materia
        data_tests: [unique, not_null]
      - name: conselho_sk
        data_tests:
          - not_null
          - relationships:
              arguments:
                to: ref('dim_conselho')
                field: conselho_sk
      - name: tipologia_sigla
        data_tests:
          - accepted_values:
              arguments:
                values: ['99', 'AUTO', 'DEF', 'FISC', 'GEST', 'IP', 'SEM']
```

Em `marts.yml`, numa chave `unit_tests:` no fim do arquivo:

```yaml
unit_tests:
  - name: fct_ato_casa_o_nome_da_data
    description: "Dentro da vigência, antes do primeiro nome, depois da extinção e órgão fora do escopo."
    model: fct_ato
    given:
      - input: ref('stg_atos')
        rows:
          - {ato_id: 1, materia: "DOU:a", origem: DOU, data_publicacao: 2005-06-01, mes: 2005-06-01, orgao_id: 1, tipologia_sigla: DEF, revisor_tipo: HUMANO}
          - {ato_id: 2, materia: "DOU:b", origem: DOU, data_publicacao: 1999-01-01, mes: 1999-01-01, orgao_id: 1, tipologia_sigla: null, revisor_tipo: null}
          - {ato_id: 3, materia: "DOU:c", origem: DOU, data_publicacao: 2012-03-01, mes: 2012-03-01, orgao_id: 1, tipologia_sigla: GEST, revisor_tipo: HUMANO}
          - {ato_id: 4, materia: "DOU:d", origem: DOU, data_publicacao: 2016-01-01, mes: 2016-01-01, orgao_id: 1, tipologia_sigla: GEST, revisor_tipo: HUMANO}
          - {ato_id: 5, materia: "DOU:e", origem: DOU, data_publicacao: 2016-01-01, mes: 2016-01-01, orgao_id: 2, tipologia_sigla: GEST, revisor_tipo: HUMANO}
      - input: ref('dim_conselho')
        rows:
          - {conselho_sk: 10, orgao_id: 1, valido_de: 2000-01-01, valido_ate: 2009-12-31}
          - {conselho_sk: 11, orgao_id: 1, valido_de: 2010-01-01, valido_ate: 2014-12-31}
    expect:
      rows:
        - {ato_id: 1, conselho_sk: 10, nome_aproximado: false, tipologia_sigla: DEF}
        - {ato_id: 2, conselho_sk: 10, nome_aproximado: true, tipologia_sigla: SEM}
        - {ato_id: 3, conselho_sk: 11, nome_aproximado: false, tipologia_sigla: GEST}
        - {ato_id: 4, conselho_sk: 11, nome_aproximado: true, tipologia_sigla: GEST}
```

- [ ] **Passo 2: rodar e ver falhar**

```bash
make gold
```

Esperado: erro de compilação, porque `fct_ato` não existe.

- [ ] **Passo 3: o modelo**

`dbt/models/marts/fct_ato.sql`:

```sql
-- Fato. Granularidade: uma linha por matéria publicada (a versão mais recente), ligada ao nome que o
-- conselho tinha na data da publicação. Atos de órgãos fora da dim_conselho (ADR 0010) saem daqui; a
-- contagem deles está em docs/adr/medicoes/0009-gold/fct_ato-fora-do-escopo.txt.
with atos as (
    select ato_id, materia, origem, data_publicacao, mes, orgao_id, tipologia_sigla, revisor_tipo
    from {{ ref('stg_atos') }}
    where orgao_id in (select orgao_id from {{ ref('dim_conselho') }})
),
primeiro_nome as (
    select orgao_id, conselho_sk from {{ ref('dim_conselho') }}
    qualify row_number() over (partition by orgao_id order by valido_de) = 1
),
-- asof: o último nome que começou até a data. Cobre o nome vigente, um buraco entre dois nomes e o ato
-- depois da extinção (fica com o último nome). Antes do primeiro nome não há par: fica com o mais antigo.
casado as (
    select a.*, d.conselho_sk, d.valido_ate
    from atos a
    asof left join {{ ref('dim_conselho') }} d
      on a.orgao_id = d.orgao_id and a.data_publicacao >= d.valido_de
)
select
    c.ato_id,
    c.materia,
    c.origem,
    c.data_publicacao,
    c.mes,
    c.orgao_id,
    coalesce(c.conselho_sk, p.conselho_sk) as conselho_sk,
    -- aproximado: a data cai fora da vigência do nome escolhido
    c.conselho_sk is null or c.data_publicacao > c.valido_ate as nome_aproximado,
    coalesce(c.tipologia_sigla, 'SEM') as tipologia_sigla,
    c.revisor_tipo
from casado c
left join primeiro_nome p on p.orgao_id = c.orgao_id
```

- [ ] **Passo 4: rodar e ver passar**

```bash
make gold
```

Esperado: `fct_ato` criada, com o teste unitário e todos os testes em `PASS`. Para ver o teste unitário pegar o erro, troque o `asof left join` por um `left join` com `between valido_de and valido_ate` e o fallback pelo primeiro nome, como no plano antigo: o ato 4 sai com o nome 10, e o teste falha. Depois, volte o arquivo.

- [ ] **Passo 5: o que ficou fora do escopo, para o ADR 0009**

```bash
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T orquestrador dbt show --project-dir /app/dbt --limit 50 --inline "select orgao_id, count(*) as atos, min(data_publicacao) as primeiro, max(data_publicacao) as ultimo from {{ ref('stg_atos') }} where orgao_id not in (select orgao_id from {{ ref('dim_conselho') }}) group by 1 order by 2 desc" > docs/adr/medicoes/0009-gold/fct_ato-fora-do-escopo.txt
```

Esperado: os 9 órgãos e os 146 atos, se o banco tiver de julho a setembro de 2026. Junte uma linha com o total do fato por origem.

- [ ] **Passo 6: stage**

```bash
git add dbt docs/adr/medicoes/0009-gold && git diff --cached --stat
```

---

### Tarefa 4: o fato mensal, a vitalidade e o teste de distribuição

O mês sem ato é o dado que a pergunta da E1 mede. Por isso o fato mensal tem linha com `atos = 0`. E por isso o teste de distribuição separa dois casos: o mês em que um conselho não publicou e o mês que não foi ingerido.

**Arquivos:**
- Criar: `dbt/models/marts/fct_conselho_mes.sql`, `dbt/models/marts/mart_vitalidade.sql`, `dbt/tests/distribuicao_mes_sem_nenhum_ato.sql`, `dbt/tests/distribuicao_fora_da_tipologia.sql`
- Modificar: `dbt/models/marts/marts.yml`

**Interfaces:**
- Consome: `ref('fct_ato')`, `ref('dim_conselho')`.
- Produz: `ref('fct_conselho_mes')`, com `orgao_id, mes, atos`.
- Produz: `ref('mart_vitalidade')`, com `orgao_id, nome, sigla, ultimo_mes_com_ato, atos_no_periodo, meses_sem_publicar, situacao`.

- [ ] **Passo 1: os testes de distribuição**

`dbt/tests/distribuicao_mes_sem_nenhum_ato.sql`:

```sql
-- Um mês do período coberto sem nenhum ato de nenhum conselho não é silêncio: é um mês que não foi
-- ingerido. Sem este teste, o painel mostraria todos os conselhos parados naquele mês.
select mes, sum(atos) as atos
from {{ ref('fct_conselho_mes') }}
group by mes
having sum(atos) = 0
```

`dbt/tests/distribuicao_fora_da_tipologia.sql`:

```sql
-- No gabarito da pesquisadora, 6 de 215 atos (3%) ficam fora da tipologia. Passar de 20% indica
-- classificação quebrada, não conselhos diferentes.
select count(*) filter (where tipologia_sigla = '99') * 1.0 / count(*) as fracao_fora
from {{ ref('fct_ato') }}
where tipologia_sigla <> 'SEM'
having count(*) > 0 and count(*) filter (where tipologia_sigla = '99') * 1.0 / count(*) > 0.2
```

- [ ] **Passo 2: os modelos**

`dbt/models/marts/fct_conselho_mes.sql`:

```sql
-- Granularidade: uma linha por conselho por mês do período coberto pela ingestão do DOU.
-- Mês sem ato vira linha com atos = 0: é o silêncio que a pergunta da E1 mede.
with limites as (
    select min(mes) as inicio, max(mes) as fim
    from {{ ref('fct_ato') }}
    where origem = 'DOU'
),
meses as (
    select unnest(generate_series(inicio, fim, interval 1 month))::date as mes
    from limites
    where inicio is not null
),
conselhos as (select distinct orgao_id from {{ ref('dim_conselho') }})
select c.orgao_id, m.mes, count(a.ato_id) as atos
from conselhos c
cross join meses m
left join {{ ref('fct_ato') }} a
  on a.orgao_id = c.orgao_id and a.mes = m.mes and a.origem = 'DOU'
group by c.orgao_id, m.mes
```

`dbt/models/marts/mart_vitalidade.sql`:

```sql
-- Granularidade: uma linha por conselho, com o nome vigente e a situação no último mês coberto.
-- É a resposta à pergunta da E1.
with cobertura as (select max(mes) as ultimo from {{ ref('fct_conselho_mes') }}),
por_conselho as (
    select orgao_id,
           max(mes) filter (where atos > 0) as ultimo_mes_com_ato,
           sum(atos) as atos_no_periodo
    from {{ ref('fct_conselho_mes') }}
    group by orgao_id
)
select
    d.orgao_id,
    d.nome,
    d.sigla,
    p.ultimo_mes_com_ato,
    coalesce(p.atos_no_periodo, 0) as atos_no_periodo,
    date_diff('month', p.ultimo_mes_com_ato, c.ultimo) as meses_sem_publicar,
    case
        when p.ultimo_mes_com_ato is null then 'sem ato no período coberto'
        when date_diff('month', p.ultimo_mes_com_ato, c.ultimo) <= {{ var('meses_ativo', 3) }} then 'ativo'
        else 'em silêncio'
    end as situacao
from {{ ref('dim_conselho') }} d
cross join cobertura c
left join por_conselho p on p.orgao_id = d.orgao_id
where d.atual
```

Em `marts.yml`:

```yaml
  - name: fct_conselho_mes
    description: "Fato agregado. Granularidade: uma linha por conselho por mês do período coberto pelo DOU, inclusive meses sem ato."
    tests:
      - unique:
          column_name: "orgao_id || '-' || mes"
    columns:
      - name: atos
        tests: [not_null]

  - name: mart_vitalidade
    description: "Consumo. Granularidade: uma linha por conselho. Responde quais conselhos ainda estão funcionando."
    columns:
      - name: orgao_id
        tests: [unique, not_null]
      - name: situacao
        tests:
          - accepted_values:
              values: ['ativo', 'em silêncio', 'sem ato no período coberto']
```

- [ ] **Passo 3: rodar e ver passar**

```bash
make gold
```

Esperado: os quatro marts e todos os testes em `PASS`. O número de linhas de `mart_vitalidade` é o de conselhos, 82.

- [ ] **Passo 4: provar que o teste de distribuição pega o erro**

Precisa de três meses seguidos de DOU, o que só existe depois do backfill da Tarefa 6. Primeiro, em `dbt/models/staging/stg_atos.sql`, entre o `from` e o `qualify`, acrescente:

```sql
{% if var('excluir_mes', none) %}
-- shortcut: só para demonstrar o teste de distribuição (Tarefa 4); nunca use em produção.
where date_trunc('month', data_publicacao)::date <> date '{{ var("excluir_mes") }}'
{% endif %}
```

Depois tire o mês do meio:

```bash
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T orquestrador dbt build --project-dir /app/dbt --vars '{excluir_mes: "2026-08-01"}' 2>&1 | tee docs/adr/medicoes/0009-gold/teste-distribuicao-pega-o-mes.txt
make gold
```

Esperado: `distribuicao_mes_sem_nenhum_ato` em `FAIL 1`, apontando `2026-08-01`. Depois o `make gold` normal volta a passar. A saída vai para o ADR.

- [ ] **Passo 5: stage**

```bash
git add dbt docs/adr/medicoes && git diff --cached --stat
```

---

### Tarefa 5: freshness e SLA

**SLA declarado:** *o mês M está em `mart_vitalidade` até o dia 20 do mês M+1.* A Imprensa Nacional publica o ZIP do mês cerca de duas semanas depois que ele acaba: setembro de 2026 saiu em 13/10. A agenda da Tarefa 6 roda no dia 15.

**Arquivos:**
- Criar: `dbt/models/marts/freshness_vitalidade.sql`, `dbt/tests/sla_vitalidade.sql`
- Modificar: `dbt/models/marts/marts.yml`

**Interfaces:**
- Produz: `ref('freshness_vitalidade')`, com uma linha e as colunas `primeiro_mes_coberto, ultimo_mes_coberto, mes_esperado, atraso_meses, dentro_do_sla`.

- [ ] **Passo 1: o modelo**

`dbt/models/marts/freshness_vitalidade.sql`:

```sql
-- Métrica de freshness da tabela de consumo. SLA: o mês M está na gold até o dia 20 do mês M+1.
-- Logo, hoje se espera o mês de (hoje - 20 dias) menos um.
with cobertura as (select min(mes) as primeiro, max(mes) as ultimo from {{ ref('fct_conselho_mes') }}),
esperado as (
    select (date_trunc('month', current_date - interval 20 day) - interval 1 month)::date as mes
)
select
    c.primeiro as primeiro_mes_coberto,
    c.ultimo as ultimo_mes_coberto,
    e.mes as mes_esperado,
    date_diff('month', c.ultimo, e.mes) as atraso_meses,
    date_diff('month', c.ultimo, e.mes) <= 0 as dentro_do_sla
from cobertura c, esperado e
```

`dbt/tests/sla_vitalidade.sql`:

```sql
-- Aviso, não erro: gold atrasada não deve impedir o resto do grafo, mas precisa aparecer.
{{ config(severity='warn') }}
select * from {{ ref('freshness_vitalidade') }} where not dentro_do_sla
```

Em `marts.yml`:

```yaml
  - name: freshness_vitalidade
    description: "Freshness de mart_vitalidade contra o SLA: o mês M está na gold até o dia 20 do mês M+1."
```

- [ ] **Passo 2: rodar**

```bash
make gold
```

Esperado: hoje, 03/11/2026, `mes_esperado = 2026-09-01`. Com setembro no banco, `sla_vitalidade` passa. Sem setembro, ele dá `WARN 1` e o build continua.

- [ ] **Passo 3: stage**

```bash
git add dbt && git diff --cached --stat
```

---

### Tarefa 6: orquestração com Dagster, retry e backfill

**Arquivos:**
- Criar: `src/orquestracao/__init__.py`, `scripts/demo_retry.sh`, `scripts/demo_backfill.sh`
- Modificar: `Makefile` (alvos `orquestrador`, `demo-retry`, `demo-backfill`), `docker-compose.yml` (o Dagster no serviço `orquestrador`)

**Interfaces:**
- Consome: `python -m dou fetch-mensal --month AAAA-MM`, `python -m dou persist ZIP`, `python -m lake /data/silver/atos` e o projeto dbt da Tarefa 1.
- Produz: os assets `atos_do_mes`, `silver/atos` e os modelos do dbt, num job `mensal` particionado por mês, com agenda no dia 15.

- [ ] **Passo 0: o Dagster no serviço**

No serviço `orquestrador` do `docker-compose.yml`, acrescente:

```yaml
    environment:
      DAGSTER_HOME: /data/dagster
      DADOS_ABERTOS_OUTPUT_DIR: /data/bronze/dados-abertos
    ports:
      - "127.0.0.1:3000:3000"
    volumes:
      - ./docs:/app/docs
      - ./data/bronze:/data/bronze
      - ./data/dagster:/data/dagster
    command: ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-m", "orquestracao"]
```

No alvo `gold` do `Makefile`, troque `mkdir -p data/gold` por `mkdir -p data/gold data/dagster`, porque o volume agora existe nesse serviço.

- [ ] **Passo 1: o grafo**

`src/orquestracao/__init__.py`:

```python
"""Orquestração da E3: ingestão do mês, silver e gold, num grafo mensal com retry e backfill."""

import subprocess
from pathlib import Path

import dagster as dg
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

DBT = DbtProject(project_dir=Path("/app/dbt"), profiles_dir=Path("/app/dbt"))
DBT.prepare_if_dev()

# O mês só existe nos dados abertos depois que acaba: a última partição é o mês passado.
MENSAL = dg.MonthlyPartitionsDefinition(start_date="2002-01-01")
# A Imprensa Nacional e o banco falham de vez em quando; 30 s dá tempo de voltar.
RETRY = dg.RetryPolicy(max_retries=3, delay=30)


def _roda(context: dg.AssetExecutionContext, *cmd: str) -> None:
    context.log.info(" ".join(cmd))
    subprocess.run(cmd, check=True)


@dg.asset(partitions_def=MENSAL, retry_policy=RETRY, group_name="ingestao")
def atos_do_mes(context: dg.AssetExecutionContext) -> None:
    """Baixa o ZIP do mês dos dados abertos e grava os atos de conselho no Postgres."""
    ano, mes = context.partition_key[:7].split("-")
    _roda(context, "python", "-m", "dou", "fetch-mensal", "--month", f"{ano}-{mes}")
    _roda(context, "python", "-m", "dou", "persist", f"/data/bronze/dados-abertos/S01{mes}{ano}.zip")


# shortcut: silver e gold são recalculadas inteiras a cada mês (MERGE idempotente, tabelas pequenas);
# particionar de verdade quando o dbt build passar de alguns minutos.
@dg.asset(key=["silver", "atos"], deps=[atos_do_mes], partitions_def=MENSAL, retry_policy=RETRY, group_name="silver")
def silver_atos(context: dg.AssetExecutionContext) -> None:
    """Atualiza a tabela Delta da E2 a partir do OLTP."""
    _roda(context, "python", "-m", "lake", "/data/silver/atos")


@dbt_assets(manifest=DBT.manifest_path, partitions_def=MENSAL)
def gold(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


mensal = dg.define_asset_job("mensal", selection="*", partitions_def=MENSAL)

defs = dg.Definitions(
    assets=[atos_do_mes, silver_atos, gold],
    jobs=[mensal],
    # dia 15: o ZIP do mês anterior costuma sair por volta do dia 13 (setembro saiu em 13/10).
    schedules=[dg.build_schedule_from_partitioned_job(mensal, day_of_month=15, hour_of_day=6)],
    resources={"dbt": DbtCliResource(project_dir=DBT)},
)
```

O `key=["silver", "atos"]` é o mesmo nome da fonte `silver.atos` do dbt. Assim o Dagster liga a silver aos modelos sem configuração a mais. Confira no grafo, no Passo 3.

O `prepare_if_dev()` só gera o manifesto do dbt dentro do `dagster dev`. Os scripts dos passos 4 e 5 usam `dagster asset materialize`, que lê o `dbt/target/manifest.json` deixado pelo último `make gold`. Por isso, rode `make gold` antes deles sempre que um modelo mudar.

- [ ] **Passo 2: alvos no Makefile**

```make
orquestrador: .env ## E3: sobe o Dagster em http://localhost:3000 (grafo, agenda, backfill pela interface)
	mkdir -p data/gold data/dagster
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --profile e3 up orquestrador

demo-retry: .env ## E3: derruba o banco no meio de um mês e mostra o retry do Dagster recuperando
	bash scripts/demo_retry.sh

demo-backfill: .env ## E3: reprocessa um intervalo de meses (DE=AAAA-MM ATE=AAAA-MM) pelo Dagster
	bash scripts/demo_backfill.sh $(DE) $(ATE)
```

- [ ] **Passo 3: o grafo aparece**

```bash
make orquestrador
```

Abra http://localhost:3000. Esperado: `atos_do_mes`, depois `silver/atos`, depois os modelos do dbt, ligados nessa ordem. A agenda `mensal_schedule` aparece em *Automation*. Tire um print para o ADR.

- [ ] **Passo 4: o backfill**

`scripts/demo_backfill.sh`:

```bash
#!/usr/bin/env bash
# Backfill de um intervalo de meses pelo Dagster: um run por mês, em ordem, cada um com retry.
# Uso: bash scripts/demo_backfill.sh 2026-06 2026-08
set -euo pipefail
cd "$(dirname "$0")/.."
de=${1:?mês inicial AAAA-MM}; ate=${2:?mês final AAAA-MM}
mkdir -p data/gold data/dagster docs/adr/medicoes/0009-gold
saida=docs/adr/medicoes/0009-gold/backfill-$de-a-$ate.txt
: > "$saida"
mes=$de
while [[ "$mes" < "$ate" || "$mes" == "$ate" ]]; do
  echo "==> partição $mes-01" | tee -a "$saida"
  DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T orquestrador \
    dagster asset materialize -m orquestracao --select '*' --partition "$mes-01" 2>&1 \
    | grep -E "RUN_SUCCESS|RUN_FAILURE|STEP_SUCCESS|STEP_FAILURE|STEP_UP_FOR_RETRY" | tee -a "$saida"
  mes=$(date -j -v+1m -f "%Y-%m-%d" "$mes-01" +%Y-%m 2>/dev/null || date -d "$mes-01 +1 month" +%Y-%m)
done
echo "==> atos por mês depois do backfill" | tee -a "$saida"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select date_trunc('"'"'month'"'"', data_publicacao)::date, count(*) from ato where origem = '"'"'DOU'"'"' group by 1 order by 1"' | tee -a "$saida"
```

Rode com três meses. O download de cada mês tem de 50 a 290 MB:

```bash
make demo-backfill DE=2026-06 ATE=2026-08
```

Esperado: `RUN_SUCCESS` nas três partições, e junho, julho e agosto na contagem final. Rodar de novo não duplica nada: o persist grava `inalteradas`. Essa segunda rodada também vai para o ADR.

- [ ] **Passo 5: o retry, com uma dependência derrubada de propósito**

`scripts/demo_retry.sh`:

```bash
#!/usr/bin/env bash
# Derruba o banco, dispara um mês no Dagster e religa o banco antes do retry: a primeira tentativa
# falha, o RetryPolicy (30 s) tenta de novo e passa. O mês usado já está no bronze: nada é baixado.
set -euo pipefail
cd "$(dirname "$0")/.."
MES=${MES:-2026-08}
mkdir -p docs/adr/medicoes/0009-gold
saida=docs/adr/medicoes/0009-gold/retry-$MES.txt
trap 'docker compose start db >/dev/null' EXIT   # o banco volta mesmo se o script cair
docker compose stop db
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T --no-deps orquestrador \
  dagster asset materialize -m orquestracao --select atos_do_mes --partition "$MES-01" > "$saida" 2>&1 &
run=$!
sleep 15                      # o pip install e a primeira tentativa, com o banco fora
docker compose start db
wait "$run"; rc=$?
grep -E "STEP_FAILURE|STEP_UP_FOR_RETRY|STEP_RESTARTED|STEP_SUCCESS|RUN_SUCCESS|RUN_FAILURE" "$saida"
grep -q STEP_UP_FOR_RETRY "$saida" || { echo "FALHOU: não houve retry"; exit 1; }
grep -q RUN_SUCCESS "$saida" || { echo "FALHOU: o retry não recuperou"; exit 1; }
echo "OK: a primeira tentativa caiu com o banco fora e o retry recuperou (rc=$rc)"
```

```bash
make demo-retry
```

Esperado: `STEP_UP_FOR_RETRY`, depois `STEP_SUCCESS` e `RUN_SUCCESS`. Se o pip demorar mais que 15 s e a primeira tentativa já encontrar o banco no ar, aumente o `sleep`. O teste confere que o retry aconteceu.

- [ ] **Passo 6: stage**

```bash
git add src/orquestracao scripts/demo_retry.sh scripts/demo_backfill.sh Makefile docs/adr/medicoes && git diff --cached --stat
```

---

### Tarefa 7: consulta otimizada pelo plano de execução

A consulta escolhida é a extração do `make lake` e do CDC, `QUERY_OLTP` em `src/lake/sync.py`. Toda a camada analítica depende dela, e ela tem os joins mais caros do OLTP: o nome do órgão pela vigência e a classificação vigente.

**Arquivos:**
- Criar: `docs/adr/medicoes/0009-gold/explain.sh`, `docs/adr/medicoes/0009-gold/explain-antes.txt`, `docs/adr/medicoes/0009-gold/explain-depois.txt`, `sql/007_indice_vigencia_orgao_nome.sql`

- [ ] **Passo 1: o script de medição**

`docs/adr/medicoes/0009-gold/explain.sh`:

```bash
#!/usr/bin/env bash
# EXPLAIN (ANALYZE, BUFFERS) da extração do lake, a mesma consulta do código (sem cópia do SQL).
# Uso: bash docs/adr/medicoes/0009-gold/explain.sh > docs/adr/medicoes/0009-gold/explain-antes.txt
set -euo pipefail
cd "$(dirname "$0")/../../../.."
docker compose --progress quiet run --rm -T lake python -c "
from lake.sync import QUERY_OLTP, obter_conexao
with obter_conexao() as c:
    for (linha,) in c.execute('EXPLAIN (ANALYZE, BUFFERS) ' + QUERY_OLTP, {'ato_ids': None}):
        print(linha)
"
```

- [ ] **Passo 2: medir antes, com o volume do backfill**

```bash
bash docs/adr/medicoes/0009-gold/explain.sh > docs/adr/medicoes/0009-gold/explain-antes.txt
grep -nE "Seq Scan|Nested Loop|Buffers|Execution Time" docs/adr/medicoes/0009-gold/explain-antes.txt
```

Leia o plano. O nó mais caro, em tempo ou em buffers lidos, é o alvo. O candidato provável é o join de `orgao_nome` pela vigência, que não tem índice: só existe o índice único parcial do nome vigente.

- [ ] **Passo 3: o índice que o plano pedir**

Se o alvo for `orgao_nome`, use `sql/007_indice_vigencia_orgao_nome.sql`:

```sql
-- E3 (ADR 0009): a extração do lake casa cada ato com o nome do órgão vigente na data
-- (orgao_id, data_inicio <= data, data_fim >= data). Medido em docs/adr/medicoes/0009-gold/.
CREATE INDEX IF NOT EXISTS ix_orgao_nome_vigencia ON orgao_nome (orgao_id, data_inicio, data_fim);
```

Se o plano apontar outro nó, o índice é o desse nó, com o mesmo formato de comentário.

```bash
make migrate
```

- [ ] **Passo 4: medir depois e comparar**

```bash
bash docs/adr/medicoes/0009-gold/explain.sh > docs/adr/medicoes/0009-gold/explain-depois.txt
grep -E "Execution Time|shared hit|shared read" docs/adr/medicoes/0009-gold/explain-antes.txt docs/adr/medicoes/0009-gold/explain-depois.txt
```

Esperado: o nó mudou, por exemplo de `Seq Scan` para `Index Scan`, e caíram o tempo ou os buffers. Se não caírem, o resultado vai para o ADR assim mesmo, com o motivo, como o volume pequeno. Um índice sem ganho medido não entra: tire o `007` e tente o próximo nó do plano.

- [ ] **Passo 5: o teste de esquema continua passando**

```bash
bash tests/db/test_schema.sh
```

Esperado: `OK`.

- [ ] **Passo 6: stage**

```bash
git add sql/007_indice_vigencia_orgao_nome.sql docs/adr/medicoes/0009-gold && git diff --cached --stat
```

---

### Tarefa 8: o painel

Ele responde só à pergunta da E1. São quatro blocos, nenhum gráfico decorativo.

**Arquivos:**
- Criar: `src/painel/app.py`
- Modificar: `docker-compose.yml` (serviço `painel`), `Makefile` (alvo `painel`)

**Interfaces:**
- Consome: `mart_vitalidade`, `freshness_vitalidade`, `fct_conselho_mes`, `fct_ato`, `dim_conselho`, em `/data/gold/conselhos.duckdb`.

- [ ] **Passo 1: dependências**

Já estão em `src/painel/requirements.txt`, da Tarefa 1.

- [ ] **Passo 2: o app**

`src/painel/app.py`:

```python
"""Painel da E3: quais conselhos nacionais de participação social ainda estão funcionando?"""

import duckdb
import streamlit as st

GOLD = "/data/gold/conselhos.duckdb"


def consulta(sql: str):
    # Abre e fecha a cada consulta: uma conexão aberta, mesmo só de leitura, impede o dbt de gravar a gold.
    with duckdb.connect(GOLD, read_only=True) as con:
        return con.sql(sql).df()


st.set_page_config(page_title="Conselhos Vivos", layout="wide")
st.title("Quais conselhos nacionais de participação social ainda estão funcionando?")

f = consulta("select * from freshness_vitalidade").iloc[0]
sla = "dentro do SLA" if f.dentro_do_sla else f"{int(f.atraso_meses)} mês(es) fora do SLA"
st.caption(
    f"DOU coberto de {f.primeiro_mes_coberto:%m/%Y} a {f.ultimo_mes_coberto:%m/%Y}. "
    f"SLA: o mês M entra até o dia 20 do mês M+1 ({sla})."
)

v = consulta("select * from mart_vitalidade order by situacao, meses_sem_publicar desc nulls last, nome")
for coluna, situacao in zip(st.columns(3), ["ativo", "em silêncio", "sem ato no período coberto"]):
    coluna.metric(situacao.capitalize(), int((v.situacao == situacao).sum()))

st.subheader("A situação de cada conselho")
st.caption("Ativo: publicou nos últimos 3 meses cobertos. Em silêncio: publicou antes, e parou.")
st.dataframe(
    v[["nome", "sigla", "situacao", "ultimo_mes_com_ato", "meses_sem_publicar", "atos_no_periodo"]],
    hide_index=True,
)

st.subheader("Atos de conselho por mês")
st.bar_chart(consulta("select mes, sum(atos) as atos from fct_conselho_mes group by mes order by mes"), x="mes", y="atos")

st.subheader("O que cada conselho decide")
st.caption("Atos por tipologia da pesquisadora. SEM: ainda não classificado.")
st.dataframe(
    consulta("""
        select d.nome, f.tipologia_sigla, count(*) as atos
        from fct_ato f join dim_conselho d on d.orgao_id = f.orgao_id and d.atual
        group by all order by d.nome, atos desc
    """),
    hide_index=True,
)
```

- [ ] **Passo 3: o serviço**

Em `docker-compose.yml`:

```yaml
  # E3: o painel lê a gold só para leitura; não fala com o Postgres.
  painel:
    image: python:3.12.14-slim
    profiles: [e3]
    working_dir: /app
    environment:
      PIP_CACHE_DIR: /tmp/pipcache
    ports:
      - "127.0.0.1:8501:8501"
    volumes:
      - ./src/painel:/app:ro
      - ./data/gold:/data/gold:ro
      - pipcache:/tmp/pipcache
    entrypoint: ["sh", "-c", "pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements.txt && exec streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"]
```

No `Makefile`:

```make
painel: .env ## E3: sobe o painel em http://localhost:8501 (rode make gold antes)
	docker compose --profile e3 up painel
```

- [ ] **Passo 4: ver o painel**

```bash
make gold && make painel
```

Abra http://localhost:8501. Esperado: o título é a pergunta da E1, há três números e a tabela tem 82 conselhos. Nenhum erro na página. Em outro terminal, rode `make gold` com o painel aberto: ele precisa passar, o que prova que o painel não segura a trava da gold.

- [ ] **Passo 5: stage**

```bash
git add src/painel docker-compose.yml Makefile && git diff --cached --stat
```

---

### Tarefa 9: ADR 0009, catálogo, página da E3 e tag

**Arquivos:**
- Criar: `docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md`, `site/entrega-e3.md`
- Modificar: `docs/adr/README.md`, `site/.vitepress/config.mts` (rewrite, menu e barra lateral), `README.md` (seção de comandos da E3), `AI-USAGE.md`, `docs/diario/` (a semana)

- [ ] **Passo 1: medir as granularidades para o ADR**

O enunciado pede as duas granularidades medidas. Rode no DuckDB da gold:

```bash
docker compose --progress quiet run --rm -T --entrypoint python orquestrador -c "
import duckdb, time
c = duckdb.connect('/data/gold/conselhos.duckdb', read_only=True)
for nome, sql in [
  ('linhas fct_ato (uma por matéria)', 'select count(*) from fct_ato'),
  ('linhas fct_conselho_mes (conselho x mês)', 'select count(*) from fct_conselho_mes'),
  ('linhas conselho x dia (hipotético)', \"select count(*) * (select date_diff('day', min(data_publicacao), max(data_publicacao)) + 1 from fct_ato where origem = 'DOU') from dim_conselho where atual\"),
]:
    t = time.perf_counter(); n = c.sql(sql).fetchone()[0]; print(f'{nome}: {n} ({(time.perf_counter()-t)*1000:.1f} ms)')
" | tee docs/adr/medicoes/0009-gold/granularidade.txt
```

- [ ] **Passo 2: escrever o ADR 0009**

Siga o formato do ADR 0006: status, data, decisores, contexto, requisitos, alternativas, decisão, medição e gatilhos de revisão. O conteúdo mínimo:

- **Modelagem.** As alternativas são estrela, one big table e Data Vault. A escolha é a estrela, com dois fatos e uma dimensão SCD tipo 2. O motivo vem da E2: há uma fonte só e o esquema da origem é estável, então o Data Vault não se paga. A one big table perde o mês sem ato, que é justamente o que a pergunta mede.
- **Granularidade.** O ADR traz os números do Passo 1. A grão fina, uma linha por matéria, guarda o detalhe. O fato conselho × mês, com zeros, responde à pergunta. A grão diária explode sem ganho.
- **Variação lenta.** Ela vem do `orgao_nome` do OLTP, com o print da Tarefa 2. O ADR registra a regra do ato publicado antes do primeiro nome registrado: ele fica com o nome mais antigo, marcado como aproximado.
- **Ferramenta.** dbt com o adaptador do DuckDB contra SQLMesh. A favor do dbt: já roda sobre o Delta e o Postgres sem servidor, e o `dbt docs` dá o catálogo da E4.
- **Orquestração.** Dagster contra a opção nula, cron com `make`, levada a sério. O ADR mostra o que o cron exigiria de código próprio para o retry e o backfill que as Tarefas 6.4 e 6.5 demonstram.
- **Testes que pegam erro silencioso.** A saída da Tarefa 4, Passo 4, com o mês tirado e o teste falhando.
- **SLA e freshness.** A regra do dia 20 e a agenda do dia 15.
- **Plano de execução.** O antes e depois da Tarefa 7.
- **Gatilhos de revisão.** Uma segunda fonte, como o Brasil Participativo, reabre a discussão do Data Vault. Um `dbt build` de mais de cinco minutos pede partição de verdade na silver e na gold.

- [ ] **Passo 3: a página da E3**

Crie `site/entrega-e3.md` no molde de `site/entrega-e2.md`. Ela traz uma tabela de entregáveis com o que foi feito, onde está e como conferir. Traz também o checklist de aceite com cada item ligado à prova: arquivo, comando ou medição. No `config.mts`, ponha a página no `rewrites`, no `nav` e na barra lateral, como a E2.

```bash
npm --prefix site run build
```

Esperado: `build complete`, sem link quebrado.

- [ ] **Passo 4: o catálogo**

No `Makefile`, depois de `gold`, e com `gold-docs` na linha `.PHONY`:

```make
gold-docs: .env ## E3: gera o catálogo e a linhagem do dbt em dbt/target/
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T orquestrador dbt docs generate --project-dir /app/dbt
```

```bash
make gold-docs
```

Esperado: `dbt/target/index.html` e `catalog.json` gerados. Publicar no site é da E4. Na E3 basta o ADR citar o comando.

- [ ] **Passo 5: conferir do zero, como a monitoria**

Faça como no fechamento da E2 (#34): um clone novo numa pasta temporária, com o compose de trabalho derrubado.

```bash
make setup && make test && make lake && make gold && make demo-retry
```

Esperado: tudo verde. Copie um ZIP já baixado para o bronze do clone antes do `demo-retry`, para não baixar de novo.

- [ ] **Passo 6: `AI-USAGE.md` e diário**

Uma entrada por tarefa feita com IA, no formato das existentes. O diário da semana registra o que foi decidido e o adiamento da entrega.

- [ ] **Passo 7: stage, revisão e tag**

```bash
git add -A docs site README.md AI-USAGE.md && git diff --cached --stat
```

Com o PR mergeado e o CI verde no `main`, a squad cria a tag:

```bash
git tag -a e3 -m "Entrega E3: camada analítica transformada, testada e orquestrada"
git push origin e3
```

---

## Fora deste plano, de propósito

- **ETL reverso, camada semântica, catálogo publicado, controle de acesso e LGPD:** são da E4.
- **RAG e app com três abas:** são do produto, depois da E4. O painel da E3 é só a aba Painel.
- **Classificador da tipologia:** continua em aberto. O fato já tem a tipologia `SEM` para o ato ainda não classificado.
- **Os meses de 2003 a 2020:** o backfill da E3 demonstra três meses. O histórico inteiro, que pesa vários GB, fica para quando o formato dos XML antigos for conferido.
- **CI rodando o dbt:** o `make test` não ganha o `make gold`, porque o CI não tem dados do DOU. Os testes do dbt rodam no `make gold`.
