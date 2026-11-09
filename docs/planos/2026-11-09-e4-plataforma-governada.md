# E4: plataforma completa, governada e defendida. Plano de implementação

> **Para agentes:** use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhar.

**Objetivo:** cumprir os oito itens do checklist da E4 ([enunciado](https://unb-bd2.github.io/PlanoEnsino/projeto/e4/)) até 24/11/2026, com a tag `e4`. A E4 vale 14% da nota e tem defesa de 20 minutos na mesma semana.

**Arquitetura:**
- **Camada semântica:** as métricas passam a ser definidas uma vez, em YAML, no MetricFlow do dbt.
- **Consumo duplo:** o painel e quem quiser os números fora dele leem as mesmas consultas salvas, exportadas em CSV depois da gold.
- **ETL reverso:** a situação de cada conselho, já tratada na `mart_vitalidade`, volta ao Postgres como alerta. A pesquisadora age sobre ele numa página nova do painel, Revisar.
- **Controle de acesso:** cada serviço fala com o Postgres por um papel com privilégio mínimo. O papel do app não enxerga o e-mail de quem classifica, que é o recorte de coluna.
- **Fechamento:** a análise de LGPD, o ADR 0011, a linhagem até o alerta, a retrospectiva e o roteiro da defesa.

Esse é o desenho da [arquitetura final](../../site/arquitetura.md), menos a aba Perguntar, que é do produto, depois das entregas.

**Ferramentas:**
- **Novo:** `dbt-metricflow[dbt-duckdb]==0.15.0`. Ele aceita `dbt-core` de 1.11 até antes da 1.13 e o DuckDB 1.5, e saiu em 10/09/2026.
- **Já existentes:** dbt-core 1.12.6, dbt-duckdb 1.11.1, Dagster 1.13.28, Streamlit 1.66.1, Postgres 16, `psycopg[binary]==3.2.5`, Docker Compose + make.

## O que o enunciado pede, e onde cada item cai

| # | Item do checklist | Tarefa |
|---|---|---|
| 1 | Consumo duplo: painel e camada semântica, com definição versionada de cada métrica | 1, 4 e 5 |
| 2 | Um caminho de ETL reverso: uma métrica tratada volta a um sistema operacional onde alguém agiria | 2, 3, 4 e 5 |
| 3 | Catálogo e linhagem publicados, da fonte ao consumo | 7 (a linhagem até a gold já saiu na E3) |
| 4 | Análise de LGPD: dado pessoal, base legal, retenção e descarte | 6 |
| 5 | Controle de acesso em ao menos um recorte de linha ou de coluna, com privilégio mínimo | 2 |
| 6 | Portfólio dos ADRs, com os gatilhos de revisão | 8 (os dez ADRs já têm a seção "Gatilho de revisão") |
| 7 | Retrospectiva do ciclo de vida no diário | 9 |
| 8 | Defesa de 20 minutos, para público técnico e de gestão | 9 |

O enunciado lista erros comuns:
- **Métrica sem definição única:** a Tarefa 5 tira do painel o cálculo que hoje duplica a métrica.
- **ETL reverso que não sai do papel:** a Tarefa 3 grava de verdade, e a Tarefa 5 deixa agir sobre o alerta.
- **LGPD genérica:** a Tarefa 6 mede o dado pessoal que está no banco.
- **Linhagem que para na metade:** a Tarefa 7 leva a linhagem até o alerta.
- **Defesa só técnica:** a Tarefa 9 escreve o roteiro para as duas metades da banca.
- **Deixar a E4 para o fim:** está na seção de prazos, mais abaixo.

## Decisão a confirmar antes de começar

**A camada semântica vai para o MetricFlow, e não para visões materializadas escritas à mão.** O enunciado aceita as duas.

**A favor do MetricFlow:**
- a definição fica num lugar só, em YAML, e é validada pelo `mf validate-configs`;
- ele dá métricas de razão sem SQL novo;
- a mesma definição atende o painel e quem pedir os números em CSV.

**Contra:** é uma dependência a mais no serviço do orquestrador, e o MetricFlow abre o DuckDB da gold para escrita. Por isso a exportação roda em sequência, logo depois do dbt, no mesmo job.

A opção nula é um modelo `metricas` no dbt, com a definição na descrição de cada coluna. Ela fica medida no ADR 0011 (Tarefa 8). **Se o Passo 1 da Tarefa 1 falhar** (o `pip` não resolve ou o `mf validate-configs` não roda), pare e volte à squad: o plano passa para a opção nula.

## Restrições globais

- Tudo roda por `make` e Docker Compose, como o resto do projeto. Nada é instalado no host.
- Imagem `python:3.12.14-slim`, `pip install` com o volume `pipcache` e `chown` para `DOCKER_UID:DOCKER_GID` do que for gravado em `data/`, como nos serviços da E3.
- Porta publicada só em `127.0.0.1`.
- Versões exatas: `dbt-metricflow[dbt-duckdb]==0.15.0`, e as da E3 sem mudança (`dbt-core==1.12.6`, `dbt-duckdb==1.11.1`, `duckdb==1.5.6`, `psycopg[binary]==3.2.5`, `streamlit==1.66.1`).
- Senha nenhuma no repositório. Os papéis novos leem a senha do ambiente, com o padrão de desenvolvimento igual ao nome do papel, como o `POSTGRES_PASSWORD` do `.env.example`.
- Nenhum teste ou demonstração deixa o banco de trabalho diferente do que encontrou: os testes de banco rodam em transação desfeita.
- Nos YAML do dbt, use `data_tests:` e, nos testes com parâmetro, `arguments:`, como na E3.
- **Chaves duplas do Jinja só dentro de bloco de código cercado, nos `.md`.** Em código inline, elas quebram a renderização do site, e o CI de documentação falha desde o 65ad2a1. Os filtros do MetricFlow, com `Dimension(...)` entre chaves duplas, moram nos YAML do dbt; numa página, só em bloco cercado.
- O ADR da E4 é o **0011**. A migração nova é a **`sql/007_*.sql`**.
- Commit e push só com o ok da Luiza. Cada tarefa termina com o diff em stage.
- Toda tarefa feita com IA ganha uma entrada no `AI-USAGE.md`, no formato das existentes, **sem chaves duplas em código inline**.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/orquestracao/requirements.txt` | ganha o `dbt-metricflow[dbt-duckdb]` |
| `dbt/dbt_project.yml` | a pasta `metricas` materializada como tabela |
| `dbt/models/metricas/metricflow_time_spine.sql` | a espinha de tempo diária que o MetricFlow exige |
| `dbt/models/metricas/metricas.yml` | a espinha e as consultas salvas (`atividade_por_mes`, `atividade_por_conselho`) |
| `dbt/models/marts/marts.yml` | o modelo semântico e as métricas de `fct_ato` e `fct_mencao` |
| `src/metricas/__init__.py`, `__main__.py` | exporta cada consulta salva do manifesto para `data/gold/metricas/<nome>.csv` |
| `tests/metricas/test_metricas.py` | o exportador, sem dbt nem banco |
| `sql/007_alertas_e_papeis.sql` | a tabela `alerta` e os papéis `etl_reverso`, `app_curadoria` e `leitor_analitico` |
| `docker-compose.yml`, `.env.example` | as senhas dos papéis e as variáveis de cada serviço |
| `dbt/profiles.yml` | o dbt lê o OLTP como `leitor_analitico` |
| `tests/db/test_acesso.sh` | o que cada papel pode e não pode fazer, e o descarte do revisor |
| `tests/db/test_schema.sh` | a contagem de tabelas passa de 9 para 10 |
| `src/alertas/__init__.py`, `__main__.py` | o ETL reverso: a regra e a gravação idempotente no Postgres |
| `tests/alertas/test_regra.py`, `tests/dou_db/test_alertas.py` | a regra, sem banco; a gravação, em transação desfeita |
| `src/orquestracao/__init__.py` | os assets `metricas` e `alertas`, depois da gold |
| `src/painel/app.py`, `src/painel/requirements.txt` | o gráfico mensal e a autorregulação lidos da camada semântica |
| `src/painel/pages/1_Revisar.py` | a página Revisar, onde a pesquisadora trata o alerta |
| `tests/painel/test_app.py`, `tests/painel/test_revisar.py` | o painel com e sem as métricas exportadas, e a página Revisar sem banco |
| `scripts/anonimizar_revisor.sh` | o descarte do dado pessoal de um revisor que saiu |
| `docs/lgpd.md`, `docs/lgpd/medir.sql`, `docs/lgpd/medicoes.txt` | a análise de LGPD e a medição do dado pessoal no banco |
| `src/linhagem/__init__.py`, `tests/linhagem/test_linhagem.py` | o diagrama gerado passa a ter as métricas e as consultas salvas |
| `site/.vitepress/theme/LinhagemInterativa.vue` | os nós da camada semântica e do alerta |
| `docs/adr/0011-*.md`, `docs/adr/medicoes/0011-disponibilizacao/` | o ADR e as medições |
| `docs/adr/README.md` | o portfólio: cada ADR com o item da disciplina que ele cobre |
| `site/entrega-e4.md`, `site/.vitepress/config.mts`, `site/arquitetura.md` | a página da entrega, o menu e os estados das peças |
| `docs/diario/2026-11-24.md` | a retrospectiva do ciclo de vida |
| `docs/defesa.md` | o roteiro da defesa e a demonstração |

## Quem faz o quê (sugestão)

Issues: Tarefa 1 #94, 2 #95, 3 #96, 4 #97, 5 #98, 6 #99, 7 #100, 8 #101, 9 #102.

- A Tarefa 1 e a 2 são independentes e destravam o resto.
- A 3 depende da 2. A 4 depende da 1 e da 3. A 5 depende da 1, da 2 e da 3.
- A 6 depende da 2. A 7 depende da 1 e da 3. A 8 depende das 1 a 5. A 9 fecha tudo.

| Tarefa | Pode ir para |
|---|---|
| 1. Camada semântica | uma pessoa, já |
| 2. Alerta e papéis | uma pessoa, já |
| 3. ETL reverso | quem fez a 2 |
| 4. Orquestração | quem fez a 1 |
| 5. Painel: métricas e Revisar | uma pessoa |
| 6. LGPD | uma pessoa, a partir da 2 |
| 7. Linhagem e catálogo | uma pessoa |
| 8. ADR 0011 e portfólio | quem fez a 1 e a 3 |
| 9. Retrospectiva, defesa, página e tag | todos |

**Prazos sugeridos:** 1 a 3 até 14/11; 4 a 7 até 18/11; 8 até 20/11; 9 e o ensaio da defesa até 23/11.

---

### Tarefa 1: camada semântica no MetricFlow

**Arquivos:**
- Modificar: `src/orquestracao/requirements.txt`, `dbt/dbt_project.yml`, `dbt/models/marts/marts.yml`, `Makefile`
- Criar: `dbt/models/metricas/metricflow_time_spine.sql`, `dbt/models/metricas/metricas.yml`, `src/metricas/__init__.py`, `src/metricas/__main__.py`, `tests/metricas/test_metricas.py`

**Interfaces:**
- Produz:
  - as métricas `atos_publicados`, `atos_classificados`, `atos_de_autorregulacao`, `proporcao_autorregulacao` (no modelo semântico `atos`) e `mencoes_recebidas` (no `mencoes`);
  - as consultas salvas `atividade_por_mes` e `atividade_por_conselho`;
  - `metricas.consultas(manifesto: dict) -> list[str]`;
  - `python -m metricas DESTINO`, que grava `DESTINO/<consulta>.csv`;
  - o alvo `make metricas`.
- Colunas dos CSVs:
  - `atividade_por_mes`: `metric_time__month`, `atos_publicados`, `mencoes_recebidas`;
  - `atividade_por_conselho`: `conselho`, `atos_publicados`, `mencoes_recebidas`, `proporcao_autorregulacao`.

- [ ] **Passo 1: o MetricFlow instala e conversa com o nosso dbt.** Acrescente ao fim de `src/orquestracao/requirements.txt`:

```
dbt-metricflow[dbt-duckdb]==0.15.0
```

Rode:

```bash
make gold
docker compose --progress quiet run --rm -T orquestrador sh -c 'cd /app/dbt && mf --version && dbt parse -q && mf validate-configs'
```

Esperado: a versão do MetricFlow e `mf validate-configs` sem erro. Ainda não há modelo semântico, então ele valida um projeto vazio de métricas. Se o `pip` não resolver as versões, ou o `mf` não rodar, **pare**: volte à squad com o erro (veja "Decisão a confirmar").

- [ ] **Passo 2: a espinha de tempo.** Em `dbt/dbt_project.yml`, dentro de `models: conselhos_vivos:`, acrescente:

```yaml
    metricas:
      +materialized: table
```

Crie `dbt/models/metricas/metricflow_time_spine.sql`:

```sql
-- A espinha de tempo diária que o MetricFlow exige (ADR 0011): um dia por linha, de 2002, o primeiro ano
-- dos dados abertos, até 2030.
-- shortcut: o fim é fixo; estender quando a gold chegar perto de 2030.
select cast(range as date) as date_day
from range(date '2002-01-01', date '2031-01-01', interval 1 day)
```

- [ ] **Passo 3: o modelo semântico e as métricas.** Em `dbt/models/marts/marts.yml`, troque a entrada do `fct_ato` inteira por:

```yaml
  - name: fct_ato
    description: >
      Fato. Granularidade: uma linha por matéria publicada (a versão mais recente) de um conselho do
      escopo da dim_conselho (ADR 0010), ligada ao nome que o conselho tinha na data da publicação.
      nome_aproximado é verdadeiro quando a data cai fora da vigência do nome escolhido: antes do
      primeiro nome (fica com o mais antigo), num buraco entre dois nomes (fica com o anterior) ou depois do fim do último (fica com o último).
    semantic_model:
      enabled: true
      name: atos
    agg_time_dimension: data_publicacao
    columns:
      - name: ato_id
        entity: {type: primary, name: ato}
        data_tests: [unique, not_null]
      - name: materia
        data_tests: [unique, not_null]
      - name: orgao_id
        entity: {type: foreign, name: conselho}
      - name: data_publicacao
        granularity: day
        dimension: {type: time}
      - name: origem
        dimension: {type: categorical}
      - name: conselho_sk
        data_tests:
          - not_null
          - relationships:
              arguments:
                to: ref('dim_conselho')
                field: conselho_sk
      - name: tipologia_sigla
        dimension: {type: categorical}
        data_tests:
          - accepted_values:
              arguments:
                values: ['99', 'AUTO', 'DEF', 'FISC', 'GEST', 'IP', 'SEM']
    metrics:
      - name: atos_publicados
        label: Atos publicados no DOU
        description: >
          Matérias publicadas pelo próprio conselho no DOU, na versão mais recente. Não conta os atos da
          planilha, que não são uma amostra do DOU. É a métrica do "Atos por mês" do painel.
        type: simple
        agg: sum
        expr: 1
        filter: "{{ Dimension('ato__origem') }} = 'DOU'"
      - name: atos_classificados
        label: Atos classificados
        description: "Atos, do DOU ou da planilha, com tipologia atribuída: fora o SEM (não classificado) e o 99 da planilha."
        type: simple
        agg: sum
        expr: 1
        filter: "{{ Dimension('ato__tipologia_sigla') }} not in ('SEM', '99')"
      - name: atos_de_autorregulacao
        label: Atos de autorregulação
        description: "Atos classificados como AUTO: o conselho cuidando de si, não da política pública."
        type: simple
        agg: sum
        expr: 1
        filter: "{{ Dimension('ato__tipologia_sigla') }} = 'AUTO'"
      - name: proporcao_autorregulacao
        label: Proporção de autorregulação
        description: >
          Atos AUTO sobre os atos classificados. Um conselho perto de 1 está se administrando, não decidindo
          política pública (pergunta P2 da E1).
        type: ratio
        numerator: atos_de_autorregulacao
        denominator: atos_classificados
```

E a entrada do `fct_mencao` inteira por:

```yaml
  - name: fct_mencao
    description: >
      Fato. Granularidade: uma linha por matéria publicada por outro órgão × conselho citado nela, no escopo
      da dim_conselho (ADR 0010). O nome é procurado só no título, na ementa e no começo do texto, para o
      conselho ser o assunto do ato e não uma citação de passagem (plano 2026-11-09).
    semantic_model:
      enabled: true
      name: mencoes
    agg_time_dimension: data_publicacao
    columns:
      - name: mencao_id
        entity: {type: primary, name: mencao}
        data_tests: [unique, not_null]
      - name: orgao_id
        entity: {type: foreign, name: conselho}
        data_tests:
          - not_null
          - relationships:
              arguments:
                to: ref('dim_conselho')
                field: orgao_id
      - name: data_publicacao
        granularity: day
        dimension: {type: time}
        data_tests: [not_null]
      - name: assunto
        dimension: {type: categorical}
        data_tests:
          - accepted_values:
              arguments:
                values: ['extinção', 'criação', 'estrutura', 'regimento', 'homologação', 'composição', 'outro']
    metrics:
      - name: mencoes_recebidas
        label: Menções de outros órgãos
        description: "Matérias de outro órgão que têm o conselho como assunto: o segundo sinal de vida (ADR 0009)."
        type: simple
        agg: sum
        expr: 1
```

- [ ] **Passo 4: a espinha e as consultas salvas.** Crie `dbt/models/metricas/metricas.yml`:

```yaml
version: 2

models:
  - name: metricflow_time_spine
    description: "Espinha de tempo do MetricFlow (ADR 0011). Granularidade: um dia por linha, de 2002 a 2030."
    time_spine:
      standard_granularity_column: date_day
    columns:
      - name: date_day
        granularity: day
        data_tests: [unique, not_null]

# As consultas que saem da camada semântica. O painel lê as duas; quem quiser os números fora do painel
# roda make metricas e abre o CSV. Consulta nova entra aqui, e o exportador a pega sozinho.
saved_queries:
  - name: atividade_por_mes
    description: "Atos publicados pelos conselhos no DOU e menções de outros órgãos, por mês."
    query_params:
      metrics: [atos_publicados, mencoes_recebidas]
      group_by: ["TimeDimension('metric_time', 'month')"]
  - name: atividade_por_conselho
    description: "As mesmas métricas e a proporção de autorregulação, por conselho, em todo o período carregado."
    query_params:
      metrics: [atos_publicados, mencoes_recebidas, proporcao_autorregulacao]
      group_by: ["Entity('conselho')"]
```

- [ ] **Passo 5: validar e consultar à mão.** Rode:

```bash
make gold
docker compose --progress quiet run --rm -T orquestrador sh -c 'cd /app/dbt && dbt parse -q && mf validate-configs && mf query --saved-query atividade_por_mes && mf query --saved-query atividade_por_conselho --limit 5'
```

Esperado:
- `make gold` passa, agora com os testes da espinha;
- `mf validate-configs` sem erro;
- a primeira consulta tem uma linha por mês, com `atos_publicados` igual à contagem da gold em SQL direto, pelo comando abaixo. Os 161, 96 e 132 do backfill **não** servem de conferência: são o que o `persist` gravou para todos os órgãos conhecidos, antes do escopo do ADR 0010 e da versão mais recente por matéria;
- a segunda tem a coluna `conselho`.

```bash
docker compose --progress quiet run --rm -T orquestrador dbt show --project-dir /app/dbt --inline "select mes, count(*) as atos from fct_ato where origem = 'DOU' group by mes order by mes"
```

Confira o cabeçalho das duas. Se o nome da coluna de tempo não for `metric_time__month`, troque-o na Tarefa 5 e no `medir.py` da Tarefa 8.

- [ ] **Passo 6: o teste do exportador, que falha.** Crie `tests/metricas/test_metricas.py`:

```python
"""O exportador da camada semântica (src/metricas): lê as consultas salvas do semantic_manifest.json do dbt.
Sem dbt nem banco: o manifesto é montado à mão e o mf é trocado por um registro das chamadas."""

import unittest
from unittest import mock

from metricas import consultas, exportar

MANIFESTO = {"saved_queries": [{"name": "b_consulta"}, {"name": "a_consulta"}], "metrics": []}


class Consultas(unittest.TestCase):
    def test_todas_as_consultas_salvas_em_ordem(self):
        self.assertEqual(consultas(MANIFESTO), ["a_consulta", "b_consulta"])

    def test_manifesto_sem_consultas(self):
        self.assertEqual(consultas({}), [])


class Exportar(unittest.TestCase):
    def test_um_csv_por_consulta_no_destino(self):
        with mock.patch("metricas.subprocess.run") as run:
            run.return_value.returncode = 0
            exportar(["a_consulta"], "/tmp/m", projeto="/app/dbt")
        run.assert_called_once_with(
            ["mf", "query", "--saved-query", "a_consulta", "--csv", "/tmp/m/a_consulta.csv"],
            cwd="/app/dbt", check=True,
        )


if __name__ == "__main__":
    unittest.main()
```

Rode: `docker compose --progress quiet run --rm -T --no-deps orquestrador python -m unittest discover -s tests/metricas`

Esperado: `ModuleNotFoundError: No module named 'metricas'`.

- [ ] **Passo 7: o exportador.** Crie `src/metricas/__init__.py`:

```python
"""A camada semântica fora do dbt (ADR 0011): cada consulta salva do MetricFlow vira um CSV em data/gold/metricas/,
lido pelo painel e por quem quiser os números. A lista vem do semantic_manifest.json: consulta nova no YAML
entra sem mexer aqui."""

import json
import os
import subprocess


def consultas(manifesto: dict) -> list[str]:
    """Os nomes das consultas salvas do manifesto semântico, em ordem."""
    return sorted(q["name"] for q in manifesto.get("saved_queries", []))


def exportar(nomes: list[str], destino: str, projeto: str) -> None:
    """Roda o mf de cada consulta no projeto dbt e grava DESTINO/<nome>.csv. Falha na primeira que falhar."""
    for nome in nomes:
        subprocess.run(["mf", "query", "--saved-query", nome, "--csv", os.path.join(destino, f"{nome}.csv")],
                       cwd=projeto, check=True)


def ler_manifesto(projeto: str) -> dict:
    with open(os.path.join(projeto, "target", "semantic_manifest.json"), encoding="utf-8") as f:
        return json.load(f)
```

Crie `src/metricas/__main__.py`:

```python
"""python -m metricas DESTINO: exporta as consultas salvas da camada semântica para DESTINO/<nome>.csv.
O projeto dbt precisa de um dbt parse antes (o make metricas e o asset do Dagster fazem isso)."""

import os
import sys

from . import consultas, exportar, ler_manifesto

if __name__ == "__main__":
    projeto = os.environ.get("METRICAS_PROJETO", "/app/dbt")
    destino = sys.argv[1]
    os.makedirs(destino, exist_ok=True)
    nomes = consultas(ler_manifesto(projeto))
    exportar(nomes, destino, projeto)
    print(f"[INFO] done consultas={len(nomes)} destino={destino}", file=sys.stderr)
```

- [ ] **Passo 8: o teste passa.** Rode o comando do Passo 6. Esperado: `Ran 3 tests` e `OK`.

- [ ] **Passo 9: os alvos do Makefile.** Acrescente ao `Makefile`, perto do `gold`:

```make
metricas: .env ## E4: exporta as consultas salvas da camada semântica para data/gold/metricas/ (rode make gold antes)
	@test -f data/gold/conselhos.duckdb || { echo "falta a gold: rode make gold antes"; exit 1; }
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T orquestrador sh -c 'cd /app/dbt && dbt parse -q && mf validate-configs && python -m metricas /data/gold/metricas'

test-metricas: ## testes do exportador da camada semântica, no serviço orquestrador, sem rede nem banco
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T --no-deps orquestrador python -m unittest discover -s tests/metricas
```

Ponha `test-metricas` na lista de pré-requisitos do `test:`, ao lado de `test-mencoes`.

Rode: `make metricas && head -3 data/gold/metricas/*.csv`

Esperado: os dois CSVs, com os cabeçalhos da seção Interfaces.

- [ ] **Passo 10: stage.**

```bash
git add src/orquestracao/requirements.txt dbt/dbt_project.yml dbt/models/marts/marts.yml dbt/models/metricas src/metricas tests/metricas Makefile
git diff --cached --stat
```

---

### Tarefa 2: a tabela de alertas e os papéis com privilégio mínimo

**Arquivos:**
- Criar: `sql/007_alertas_e_papeis.sql`, `tests/db/test_acesso.sh`, `scripts/anonimizar_revisor.sh`
- Modificar: `docker-compose.yml`, `.env.example`, `dbt/profiles.yml`, `tests/db/test_schema.sh`, `Makefile`

**Interfaces:**
- Produz:
  - a tabela `alerta (id, orgao_id, tipo, mes_referencia, detalhe, criado_em, tratado_em, tratado_por, nota)`, única em `(orgao_id, tipo, mes_referencia)`, com `tipo` em `em_silencio` e `citado_sem_ato_proprio`;
  - os papéis `etl_reverso`, `app_curadoria` e `leitor_analitico`, com login;
  - a função `anonimizar_revisor(id INT)`, só para o superusuário;
  - as variáveis `ETL_REVERSO_PASSWORD`, `APP_CURADORIA_PASSWORD` e `LEITOR_ANALITICO_PASSWORD`;
  - o alvo `make anonimizar-revisor ID=n`.

**O que cada papel pode:**

| Papel | Quem usa | Pode | Não pode |
|---|---|---|---|
| `etl_reverso` | o ETL reverso (Tarefa 3) | ler e inserir em `alerta`; atualizar só a coluna `detalhe` | ler qualquer outra tabela; marcar alerta como tratado |
| `app_curadoria` | a página Revisar (Tarefa 6) | ler `alerta`, `orgao_nome`, `conselho`; ler `revisor` só em `id`, `nome` e `tipo`; atualizar só `tratado_em`, `tratado_por` e `nota` em `alerta` | ler o `email` do revisor (o recorte de coluna); inserir ou apagar alerta |
| `leitor_analitico` | o dbt, ao anexar o OLTP | ler `orgao`, `orgao_nome`, `conselho` | qualquer escrita; ler `ato`, `classificacao`, `revisor` |

O superusuário `conselhos` continua com a migração, a carga, o lake e o CDC, que precisa de replicação. Tirar os privilégios dele fica para depois; isso entra no ADR 0011 como limite.

- [ ] **Passo 1: os testes de acesso, que falham.** Crie `tests/db/test_acesso.sh`:

```bash
#!/usr/bin/env bash
# Controle de acesso da E4 (ADR 0011): o que cada papel pode e não pode, e o descarte do dado pessoal do revisor.
# Cada caso roda numa transação desfeita: o superusuário cria um órgão e um ato de teste, e o comando roda depois
# de SET LOCAL ROLE, com os privilégios do papel. Não depende da carga: roda num banco só migrado, como no CI.
# Pré-requisito: banco no ar e migrado (make migrate). Uso: bash tests/db/test_acesso.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

falhas=0
ok()    { echo "  ok    $1"; }
falha() { echo "  FALHA $1"; falhas=$((falhas + 1)); }

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1" 2>&1
}

# O órgão e o ato de teste. O id do órgão fica numa configuração da transação, que qualquer papel lê
# sem privilégio: o etl_reverso não lê a tabela conselho.
BASE="INSERT INTO orgao DEFAULT VALUES;
INSERT INTO ato (origem, id_dou, orgao_id, data_publicacao, conteudo)
  VALUES ('DOU', 'TESTE-ACESSO', currval('orgao_id_seq'), '2026-09-01', 'texto');
SELECT set_config('teste.orgao', currval('orgao_id_seq')::text, true)"

como() { psql_db "BEGIN; $BASE; SET LOCAL ROLE $1; $2; ROLLBACK;"; }  # como PAPEL SQL
pode()     { if out=$(como "$2" "$3"); then ok "$1"; else falha "$1 — recusado: $out"; fi; }
nao_pode() { if out=$(como "$2" "$3"); then falha "$1 — o banco aceitou"; elif grep -q "permission denied" <<<"$out"; then ok "$1"; else falha "$1 — recusou por outro motivo: $out"; fi; }

ALERTA="INSERT INTO alerta (orgao_id, tipo, mes_referencia, detalhe)
  VALUES (current_setting('teste.orgao')::int, 'em_silencio', DATE '2026-09-01', 'x')"

echo "etl_reverso"
pode     "insere alerta"                        etl_reverso "$ALERTA"
pode     "atualiza o detalhe"                   etl_reverso "$ALERTA; UPDATE alerta SET detalhe = 'y'"
nao_pode "não marca alerta como tratado"        etl_reverso "$ALERTA; UPDATE alerta SET nota = 'y'"
nao_pode "não lê os atos"                       etl_reverso "SELECT count(*) FROM ato"
nao_pode "não lê os revisores"                  etl_reverso "SELECT count(*) FROM revisor"

echo "app_curadoria"
pode     "lê alerta e nome do conselho"         app_curadoria "SELECT count(*) FROM alerta a JOIN orgao_nome n ON n.orgao_id = a.orgao_id"
pode     "lê id, nome e tipo do revisor"        app_curadoria "SELECT id, nome, tipo FROM revisor"
nao_pode "não lê o e-mail do revisor"           app_curadoria "SELECT email FROM revisor"
nao_pode "não insere alerta"                    app_curadoria "$ALERTA"
nao_pode "não apaga alerta"                     app_curadoria "DELETE FROM alerta"

echo "leitor_analitico"
pode     "lê órgãos, nomes e conselhos"         leitor_analitico "SELECT count(*) FROM orgao o JOIN orgao_nome n ON n.orgao_id = o.id JOIN conselho c ON c.orgao_id = o.id"
nao_pode "não lê os atos"                       leitor_analitico "SELECT count(*) FROM ato"
nao_pode "não escreve"                          leitor_analitico "UPDATE conselho SET descricao = descricao"

echo "descarte do revisor (LGPD)"
anon=$(psql_db "BEGIN; $BASE;
  INSERT INTO revisor (nome, tipo, email) VALUES ('Fulana', 'HUMANO', 'fulana@exemplo.org');
  INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'GEST', currval('revisor_id_seq'));
  SELECT anonimizar_revisor(currval('revisor_id_seq')::int);
  SELECT (SELECT count(*) FROM classificacao WHERE revisor_id = r.id) || ',' || coalesce(r.email, 'nulo') || ',' || r.nome
    FROM revisor r WHERE r.id = currval('revisor_id_seq');
  ROLLBACK;" | tail -1)
[ "$anon" = "1,nulo,Revisor removido" ] && ok "anonimiza e mantém a classificação" || falha "anonimizar — veio: $anon"

echo
[ "$falhas" -eq 0 ] && echo "acesso: todos os casos passaram" || { echo "acesso: $falhas falha(s)"; exit 1; }
```

Rode: `bash tests/db/test_acesso.sh`

Esperado: falha, com `role "etl_reverso" does not exist`. O teste não lê conselho nem ato da carga: no CI, ele roda logo depois da migração, com o banco vazio.

- [ ] **Passo 2: a migração.** Crie `sql/007_alertas_e_papeis.sql`:

```sql
-- E4 (ADR 0011): os alertas do ETL reverso e os papéis com privilégio mínimo.
-- As senhas vêm do ambiente do container do banco (docker-compose.yml), nunca do repositório.

CREATE TABLE IF NOT EXISTS alerta (
    id BIGSERIAL PRIMARY KEY,
    orgao_id INT NOT NULL REFERENCES orgao(id) ON DELETE RESTRICT,
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('em_silencio', 'citado_sem_ato_proprio')),
    mes_referencia DATE NOT NULL,
    detalhe TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tratado_em TIMESTAMPTZ NULL,
    tratado_por INT NULL REFERENCES revisor(id) ON DELETE RESTRICT,
    nota TEXT NULL,
    CONSTRAINT uq_alerta UNIQUE (orgao_id, tipo, mes_referencia),
    CONSTRAINT ck_alerta_tratado CHECK ((tratado_em IS NULL) = (tratado_por IS NULL))
);
COMMENT ON TABLE alerta IS 'ETL reverso (E4): a situação de um conselho, tratada na gold, que pede ação da curadoria. Um alerta por conselho, tipo e mês de referência.';
COMMENT ON COLUMN alerta.tratado_em IS 'Quando a curadoria tratou o alerta, na página Revisar. Nulo: aberto.';

\getenv senha_etl ETL_REVERSO_PASSWORD
\getenv senha_app APP_CURADORIA_PASSWORD
\getenv senha_leitor LEITOR_ANALITICO_PASSWORD

-- Descarte do dado pessoal de um revisor que saiu (LGPD, docs/lgpd.md). Ele não pode ser apagado: as classificações
-- dele são o histórico da curadoria (ADR 0001). Perde o nome e o e-mail, e o registro fica.
CREATE FUNCTION anonimizar_revisor(p_id INT) RETURNS VOID LANGUAGE sql AS $$
    UPDATE revisor SET nome = 'Revisor removido', email = NULL WHERE id = p_id AND tipo = 'HUMANO';
$$;
REVOKE EXECUTE ON FUNCTION anonimizar_revisor(INT) FROM PUBLIC;

CREATE ROLE etl_reverso LOGIN PASSWORD :'senha_etl';
CREATE ROLE app_curadoria LOGIN PASSWORD :'senha_app';
CREATE ROLE leitor_analitico LOGIN PASSWORD :'senha_leitor';

-- etl_reverso: escreve alerta e só atualiza o texto dele; quem trata é a curadoria.
GRANT SELECT, INSERT ON alerta TO etl_reverso;
GRANT UPDATE (detalhe) ON alerta TO etl_reverso;
GRANT USAGE ON SEQUENCE alerta_id_seq TO etl_reverso;

-- app_curadoria: lê o que a página Revisar mostra e marca o alerta como tratado.
-- O recorte de coluna (LGPD): do revisor, só id, nome e tipo; o e-mail fica de fora.
GRANT SELECT ON alerta, orgao_nome, conselho TO app_curadoria;
GRANT SELECT (id, nome, tipo) ON revisor TO app_curadoria;
GRANT UPDATE (tratado_em, tratado_por, nota) ON alerta TO app_curadoria;

-- leitor_analitico: o dbt anexa o OLTP só para ler os órgãos.
GRANT SELECT ON orgao, orgao_nome, conselho TO leitor_analitico;
```

- [ ] **Passo 3: as senhas no ambiente.** No `docker-compose.yml`, no `environment:` do serviço `db`, acrescente:

```yaml
      # E4 (ADR 0011): a migração 007 cria os papéis com estas senhas. Padrão de desenvolvimento: o nome do papel.
      ETL_REVERSO_PASSWORD: ${ETL_REVERSO_PASSWORD:-etl_reverso}
      APP_CURADORIA_PASSWORD: ${APP_CURADORIA_PASSWORD:-app_curadoria}
      LEITOR_ANALITICO_PASSWORD: ${LEITOR_ANALITICO_PASSWORD:-leitor_analitico}
```

No `environment:` do `orquestrador`, acrescente:

```yaml
      # E4: o dbt lê o OLTP como leitor_analitico, e o ETL reverso grava como etl_reverso (ADR 0011)
      DBT_PGUSER: leitor_analitico
      DBT_PGPASSWORD: ${LEITOR_ANALITICO_PASSWORD:-leitor_analitico}
      ALERTAS_PGUSER: etl_reverso
      ALERTAS_PGPASSWORD: ${ETL_REVERSO_PASSWORD:-etl_reverso}
```

No `.env.example`, logo abaixo do `POSTGRES_PASSWORD`, acrescente:

```
# E4: senhas dos papéis com privilégio mínimo (ADR 0011). Sem elas, vale o nome do papel.
ETL_REVERSO_PASSWORD=etl_reverso
APP_CURADORIA_PASSWORD=app_curadoria
LEITOR_ANALITICO_PASSWORD=leitor_analitico
```

O container do banco só lê o ambiente novo quando é recriado. Rode: `docker compose up -d db && make migrate`

Esperado: `→ aplicando 007_alertas_e_papeis.sql` e `migrações em dia`.

- [ ] **Passo 4: o descarte do revisor.** Crie `scripts/anonimizar_revisor.sh`:

```bash
#!/usr/bin/env bash
# Descarte do dado pessoal de um revisor que saiu do projeto (LGPD, docs/lgpd.md): chama a função
# anonimizar_revisor da migração 007, a mesma que o tests/db/test_acesso.sh testa.
# Uso: bash scripts/anonimizar_revisor.sh ID   (ou make anonimizar-revisor ID=n)
set -euo pipefail
cd "$(dirname "$0")/.."
id=${1:?id do revisor}
[[ "$id" =~ ^[0-9]+$ ]] || { echo "o id é um número"; exit 1; }
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT anonimizar_revisor($1)"' sh "$id"
```

E no `Makefile`:

```make
anonimizar-revisor: .env ## E4 (LGPD): apaga o nome e o e-mail do revisor ID e mantém as classificações dele
	bash scripts/anonimizar_revisor.sh $(ID)
```

- [ ] **Passo 5: os testes passam.** Rode: `bash tests/db/test_acesso.sh`

Esperado: todos os casos com `ok` e `acesso: todos os casos passaram`.

- [ ] **Passo 6: o teste de esquema com a tabela nova.** Em `tests/db/test_schema.sh`, troque:

```bash
espera_valor "8 tabelas + schema_migrations" "9" \
```

por:

```bash
espera_valor "9 tabelas + schema_migrations" "10" \
```

E, no `Makefile`, na receita do `test:`, logo depois de `bash tests/db/test_schema.sh`, acrescente:

```make
	bash tests/db/test_acesso.sh
```

Rode: `bash tests/db/test_schema.sh`. Esperado: todos `ok`.

- [ ] **Passo 7: o dbt lê o OLTP como `leitor_analitico`.** Em `dbt/profiles.yml`, na linha do `attach`, troque o usuário e a senha para lerem as variáveis novas, com as antigas de reserva:

```yaml
        - path: "host=db dbname={{ env_var('PGDATABASE') }} user={{ env_var('DBT_PGUSER', env_var('PGUSER')) }} password={{ env_var('DBT_PGPASSWORD', env_var('PGPASSWORD')) }}"
```

Rode: `make gold`. Esperado: `PASS=` igual ao total, sem erro de permissão: o dbt só lê `orgao`, `orgao_nome` e `conselho` do OLTP.

- [ ] **Passo 8: stage.**

```bash
git add sql/007_alertas_e_papeis.sql tests/db/test_acesso.sh tests/db/test_schema.sh scripts/anonimizar_revisor.sh docker-compose.yml .env.example dbt/profiles.yml Makefile
git diff --cached --stat
```

---

### Tarefa 3: o ETL reverso

**Arquivos:**
- Criar: `src/alertas/__init__.py`, `src/alertas/__main__.py`, `tests/alertas/test_regra.py`, `tests/dou_db/test_alertas.py`
- Modificar: `Makefile`

**Interfaces:**
- Consome:
  - a `mart_vitalidade` da gold (`orgao_id`, `nome`, `sigla`, `situacao`, `mes_referencia`, `meses_sem_publicar`, `mencoes_no_periodo`);
  - a tabela `alerta` e o papel `etl_reverso` da Tarefa 2.
- Produz:
  - `alertas.Alerta(orgao_id: int, tipo: str, mes_referencia: date, detalhe: str)`;
  - `alertas.alertas(linhas: list[dict]) -> list[Alerta]`;
  - `alertas.gravar(conn, lista: list[Alerta]) -> tuple[int, int, int]`, que devolve (novos, atualizados, inalterados);
  - `python -m alertas`, que lê a gold de `ALERTAS_GOLD` (padrão `/data/gold/conselhos.duckdb`) e grava como `ALERTAS_PGUSER`;
  - o alvo `make alertas`.

**A regra:**
- **`em_silencio`:** a situação é "em silêncio". A ação esperada é conferir se o conselho foi extinto, mudou de nome ou publica por outro órgão.
- **`citado_sem_ato_proprio`:** a situação não é "ativo", e há menções no período. A ação esperada é conferir se os atos dele saem com outro nome, que estaria na fila de órgãos (`orgao_alias`).
- Os dois podem valer para o mesmo conselho.
- No banco de trabalho de hoje, com julho a setembro, só o segundo dispara: são 10 conselhos. O primeiro precisa de mais de 3 meses cobertos.

- [ ] **Passo 1: o teste da regra, que falha.** Crie `tests/alertas/test_regra.py`:

```python
"""A regra do ETL reverso (src/alertas): que situação da mart_vitalidade vira alerta para a curadoria. Sem banco."""

import unittest
from datetime import date

from alertas import alertas

SET = date(2026, 9, 1)


def linha(**k):
    base = dict(orgao_id=1, nome="Conselho Um", sigla="C1", situacao="ativo", mes_referencia=SET,
                meses_sem_publicar=0, mencoes_no_periodo=0)
    return {**base, **k}


class Regra(unittest.TestCase):
    def test_ativo_nao_alerta(self):
        self.assertEqual(alertas([linha(mencoes_no_periodo=5)]), [])

    def test_em_silencio_alerta(self):
        [a] = alertas([linha(situacao="em silêncio", meses_sem_publicar=5)])
        self.assertEqual((a.orgao_id, a.tipo, a.mes_referencia), (1, "em_silencio", SET))
        self.assertIn("5 meses sem ato próprio", a.detalhe)

    def test_em_silencio_sem_nunca_publicar(self):
        [a] = alertas([linha(situacao="em silêncio", meses_sem_publicar=None)])
        self.assertIn("nenhum ato próprio no período coberto", a.detalhe)

    def test_sem_ato_mas_citado(self):
        [a] = alertas([linha(situacao="sem ato no período coberto", meses_sem_publicar=None, mencoes_no_periodo=2)])
        self.assertEqual(a.tipo, "citado_sem_ato_proprio")
        self.assertIn("citado 2 vez(es)", a.detalhe)

    def test_silencio_e_citado_dao_dois_alertas(self):
        tipos = [a.tipo for a in alertas([linha(situacao="em silêncio", meses_sem_publicar=4, mencoes_no_periodo=1)])]
        self.assertEqual(tipos, ["em_silencio", "citado_sem_ato_proprio"])

    def test_sem_mes_de_referencia_nao_alerta(self):
        # gold sem DOU, como num clone limpo: não há período coberto para afirmar nada
        self.assertEqual(alertas([linha(situacao="em silêncio", mes_referencia=None)]), [])


if __name__ == "__main__":
    unittest.main()
```

Rode: `docker compose --progress quiet run --rm -T --no-deps orquestrador python -m unittest discover -s tests/alertas`

Esperado: `ModuleNotFoundError: No module named 'alertas'`.

- [ ] **Passo 2: a regra e a gravação.** Crie `src/alertas/__init__.py`:

```python
"""ETL reverso (E4, ADR 0011): a situação de cada conselho, tratada na gold, volta ao Postgres como alerta, onde a
curadoria age (página Revisar do painel). A regra mora aqui; a situação vem pronta da mart_vitalidade."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Alerta:
    orgao_id: int
    tipo: str
    mes_referencia: date
    detalhe: str


def alertas(linhas: list[dict]) -> list[Alerta]:
    """Os alertas de cada linha da mart_vitalidade. Sem mês de referência (gold sem DOU), nenhum."""
    out = []
    for l in linhas:
        if l["mes_referencia"] is None:
            continue
        nome = l["sigla"] or l["nome"]
        if l["situacao"] == "em silêncio":
            quanto = (f"{l['meses_sem_publicar']} meses sem ato próprio no DOU" if l["meses_sem_publicar"] is not None
                      else "nenhum ato próprio no período coberto")
            out.append(Alerta(l["orgao_id"], "em_silencio", l["mes_referencia"],
                              f"{nome}: {quanto}. Confira se o conselho foi extinto, mudou de nome ou publica por outro órgão."))
        if l["situacao"] != "ativo" and (l["mencoes_no_periodo"] or 0) > 0:
            out.append(Alerta(l["orgao_id"], "citado_sem_ato_proprio", l["mes_referencia"],
                              f"{nome}: sem ato próprio recente, mas citado {l['mencoes_no_periodo']} vez(es) por outros órgãos. "
                              "Confira se os atos dele saem com outro nome (fila de órgãos em orgao_alias)."))
    return out


# Idempotente: o mesmo alerta não duplica (uq_alerta), e um alerta já tratado não é reescrito.
# xmax = 0 só na linha recém-inserida: separa novo de atualizado sem outra consulta.
UPSERT = """
insert into alerta (orgao_id, tipo, mes_referencia, detalhe) values (%s, %s, %s, %s)
on conflict (orgao_id, tipo, mes_referencia) do update set detalhe = excluded.detalhe
  where alerta.tratado_em is null and alerta.detalhe is distinct from excluded.detalhe
returning (xmax = 0) as novo
"""


def gravar(conn, lista: list[Alerta]) -> tuple[int, int, int]:
    """Grava os alertas na transação de `conn`, sem commit. Devolve (novos, atualizados, inalterados).
    shortcut: alerta que deixou de valer não é fechado sozinho; a curadoria fecha na página Revisar."""
    novos = atualizados = 0
    for a in lista:
        linha = conn.execute(UPSERT, (a.orgao_id, a.tipo, a.mes_referencia, a.detalhe)).fetchone()
        if linha is None:
            continue
        if linha[0]:
            novos += 1
        else:
            atualizados += 1
    return novos, atualizados, len(lista) - novos - atualizados
```

Crie `src/alertas/__main__.py`:

```python
"""python -m alertas: lê a mart_vitalidade da gold e grava os alertas no Postgres como etl_reverso (ADR 0011)."""

import os
import sys

import duckdb
import psycopg

from . import alertas, gravar

COLUNAS = "orgao_id, nome, sigla, situacao, mes_referencia, meses_sem_publicar, mencoes_no_periodo"

if __name__ == "__main__":
    with duckdb.connect(os.environ.get("ALERTAS_GOLD", "/data/gold/conselhos.duckdb"), read_only=True) as con:
        cur = con.execute(f"select {COLUNAS} from mart_vitalidade")
        nomes = [d[0] for d in cur.description]
        linhas = [dict(zip(nomes, r)) for r in cur.fetchall()]
    lista = alertas(linhas)
    with psycopg.connect(host=os.environ.get("PGHOST", "db"), dbname=os.environ["PGDATABASE"],
                         user=os.environ["ALERTAS_PGUSER"], password=os.environ["ALERTAS_PGPASSWORD"]) as conn:
        novos, atualizados, inalterados = gravar(conn, lista)
    print(f"[INFO] done novos={novos} atualizados={atualizados} inalterados={inalterados}", file=sys.stderr)
```

- [ ] **Passo 3: a regra passa.** Rode o comando do Passo 1. Esperado: `Ran 6 tests` e `OK`.

- [ ] **Passo 4: o teste da gravação, em transação desfeita.** Crie `tests/dou_db/test_alertas.py`. Ele roda no `dou-db-test`, que já tem o `dbtest`:

```python
"""A gravação do ETL reverso no Postgres (src/alertas.gravar), em transação desfeita (dbtest)."""

import unittest
from datetime import date

import dbtest

from alertas import Alerta, gravar

SET = date(2026, 9, 1)


class Gravar(dbtest.CasoComBanco):
    def setUp(self):
        super().setUp()
        self.orgao = self.conn.execute("select orgao_id from conselho limit 1").fetchone()[0]

    def test_segunda_vez_nao_muda_nada(self):
        a = [Alerta(self.orgao, "em_silencio", SET, "x")]
        self.assertEqual(gravar(self.conn, a), (1, 0, 0))
        self.assertEqual(gravar(self.conn, a), (0, 0, 1))

    def test_detalhe_novo_atualiza_o_aberto(self):
        gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "x")])
        self.assertEqual(gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "y")]), (0, 1, 0))

    def test_tratado_nao_e_reescrito(self):
        gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "x")])
        self.conn.execute("update alerta set tratado_em = now(), tratado_por = (select min(id) from revisor), nota = 'ok' "
                          "where orgao_id = %s", (self.orgao,))
        self.assertEqual(gravar(self.conn, [Alerta(self.orgao, "em_silencio", SET, "y")]), (0, 0, 1))
        self.assertEqual(self.conn.execute("select detalhe from alerta where orgao_id = %s", (self.orgao,)).fetchone()[0], "x")


if __name__ == "__main__":
    unittest.main()
```

O `dou-db-test` instala só `src/dou/requirements.txt`, que já tem o `psycopg`. O `alertas/__init__.py` não importa o `duckdb`: só o `__main__` importa.

Rode: `make test-db-py`. Esperado: os testes do `dou_db` e os 3 novos com `OK`.

- [ ] **Passo 5: o alvo e a primeira carga.** Acrescente ao `Makefile`:

```make
alertas: .env ## E4: ETL reverso, grava no Postgres os alertas da mart_vitalidade (rode make gold antes)
	@test -f data/gold/conselhos.duckdb || { echo "falta a gold: rode make gold antes"; exit 1; }
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T orquestrador python -m alertas

test-alertas: ## testes da regra do ETL reverso, no serviço orquestrador, sem rede nem banco
	DOCKER_UID=$$(id -u) DOCKER_GID=$$(id -g) docker compose --progress quiet run --rm -T --no-deps orquestrador python -m unittest discover -s tests/alertas
```

Ponha `test-alertas` nos pré-requisitos do `test:`.

Rode `make alertas` duas vezes. Esperado no banco de trabalho, com julho a setembro: `novos=10 atualizados=0 inalterados=0` na primeira e `novos=0 atualizados=0 inalterados=10` na segunda. Guarde as duas saídas em `docs/adr/medicoes/0011-disponibilizacao/alertas-idempotencia.txt`.

**Atenção:** esses 10 alertas ficam no banco de trabalho, de propósito. São o dado da página Revisar e da defesa. Para tirá-los, como superusuário: `DELETE FROM alerta;`.

- [ ] **Passo 6: stage.**

```bash
git add src/alertas tests/alertas tests/dou_db/test_alertas.py Makefile docs/adr/medicoes/0011-disponibilizacao
git diff --cached --stat
```

---

### Tarefa 4: métricas e alertas no job mensal

**Arquivos:**
- Modificar: `src/orquestracao/__init__.py`

**Interfaces:**
- Consome: `python -m metricas` (Tarefa 1) e `python -m alertas` (Tarefa 3).
- Produz: os assets `metricas`, depois da gold, e `alertas`, depois das métricas, no job `mensal`.

- [ ] **Passo 1: os dois assets.** Em `src/orquestracao/__init__.py`, depois do `gold` e antes do `mensal = ...`, acrescente:

```python
# E4 (ADR 0011): as consultas salvas da camada semântica viram CSV depois da gold. O mf abre o DuckDB para
# escrita, por isso roda aqui, no mesmo job e em sequência, e não no painel.
@dg.asset(deps=[gold], partitions_def=MENSAL, retry_policy=RETRY, group_name="consumo")
def metricas(context: dg.AssetExecutionContext) -> None:
    """Exporta as consultas salvas do MetricFlow para /data/gold/metricas/."""
    roda(context, "sh", "-c", "cd /app/dbt && dbt parse -q && python -m metricas /data/gold/metricas")


# E4: o ETL reverso. A situação tratada na gold volta ao Postgres como alerta para a curadoria.
# Depois das métricas, e não ao lado: o mf segura o DuckDB para escrita, e o alertas não abriria nem para ler.
@dg.asset(deps=[metricas], partitions_def=MENSAL, retry_policy=RETRY, group_name="consumo")
def alertas(context: dg.AssetExecutionContext) -> None:
    """Grava no Postgres, como etl_reverso, os alertas da mart_vitalidade."""
    roda(context, "python", "-m", "alertas")
```

No `defs`, troque `assets=[atos_do_mes, silver_atos, silver_mencoes, gold]` por `assets=[atos_do_mes, silver_atos, silver_mencoes, gold, metricas, alertas]`.

- [ ] **Passo 2: o grafo valida.** Rode:

```bash
docker compose --progress quiet run --rm -T orquestrador sh -c 'dbt parse -q --project-dir /app/dbt && dagster definitions validate -m orquestracao'
```

Esperado: `Validation successful`.

- [ ] **Passo 3: um mês de ponta a ponta.** Rode: `make demo-backfill DE=2026-09 ATE=2026-09`

Esperado: `STEP_SUCCESS` em `atos_do_mes`, `silver__atos`, `silver__mencoes`, `gold`, `metricas` e `alertas`, e `RUN_SUCCESS`. O backfill grava a prova em `docs/adr/medicoes/0009-gold/`. Mova esse arquivo para `docs/adr/medicoes/0011-disponibilizacao/`, porque ele é a prova do job da E4.

- [ ] **Passo 4: o print do grafo.** Suba com `make orquestrador`, abra http://localhost:3000, vá ao job `mensal` e salve o print do grafo em `docs/adr/medicoes/0011-disponibilizacao/grafo-dagster.jpg`.

- [ ] **Passo 5: stage.**

```bash
git add src/orquestracao/__init__.py docs/adr/medicoes/0011-disponibilizacao
git diff --cached --stat
```

---

### Tarefa 5: o painel lê a camada semântica, e a página Revisar

**Arquivos:**
- Modificar: `src/painel/app.py`, `src/painel/requirements.txt`, `docker-compose.yml`, `tests/painel/test_app.py`
- Criar: `src/painel/pages/1_Revisar.py`, `tests/painel/test_revisar.py`

**Interfaces:**
- Consome:
  - `data/gold/metricas/atividade_por_mes.csv` e `atividade_por_conselho.csv` (Tarefa 1);
  - a tabela `alerta` e o papel `app_curadoria` (Tarefa 2).
- Produz:
  - a variável `PAINEL_METRICAS`, com padrão `/data/gold/metricas`;
  - a página Revisar, que o Streamlit lista sozinho por estar em `pages/`.

- [ ] **Passo 1: os testes do painel, que falham.** Em `tests/painel/test_app.py`:
  - No `setUp`, depois de `self.orig_gold = ...`, acrescente `self.orig_metricas = os.environ.get("PAINEL_METRICAS")` e `os.environ["PAINEL_METRICAS"] = os.path.join(self.tmpdir, "metricas")`. Sem isso, o teste leria o CSV de verdade em `data/gold/`, que o serviço monta.
  - No `tearDown`, restaure `PAINEL_METRICAS` como o `PAINEL_GOLD` é restaurado.
  - Acrescente os dois testes:

```python
    def _grava_metricas(self):
        pasta = os.environ["PAINEL_METRICAS"]
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "atividade_por_mes.csv"), "w") as f:
            # outubro só tem menção, depois do último mês coberto (setembro): o painel não pode mostrá-lo
            f.write("metric_time__month,atos_publicados,mencoes_recebidas\n2026-07-01,4,1\n2026-08-01,3,0\n2026-10-01,,5\n")
        with open(os.path.join(pasta, "atividade_por_conselho.csv"), "w") as f:
            f.write("conselho,atos_publicados,mencoes_recebidas,proporcao_autorregulacao\n1,4,1,0.25\n2,0,2,\n")

    def test_atividade_vem_da_camada_semantica(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        self._grava_metricas()
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(any("make metricas" in i.value for i in at.info))
        autorregulacao = at.dataframe[2].value
        self.assertEqual(list(autorregulacao["Conselho"]), ["Conselho Um"])
        self.assertEqual(list(autorregulacao["Autorregulação"]), [0.25])

    def test_sem_metricas_pede_make_metricas(self):
        with duckdb.connect(self.gold_path) as con:
            self._cria_tabelas_base(con)
            self._cria_freshness(con)
        os.environ["PAINEL_GOLD"] = self.gold_path
        at = AppTest.from_file(APP).run(timeout=60)
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("make metricas" in i.value for i in at.info))
```

Rode: `make test-painel`. Esperado: os dois testes novos falham, e os outros passam.

- [ ] **Passo 2: o painel lê as métricas.** Em `src/painel/app.py`:
  - Depois de `GOLD = os.environ.get(...)`, acrescente:

```python
# As métricas da camada semântica (ADR 0011), exportadas pelo make metricas ou pelo job mensal: o painel não
# recalcula o que o MetricFlow define.
METRICAS = os.environ.get("PAINEL_METRICAS", "/data/gold/metricas")
```

  - No bloco `with duckdb.connect(...)`, apague a linha `mensal = con.sql("select mes, sum(atos) as atos from fct_conselho_mes group by mes order by mes").df()`.
  - Troque o trecho inteiro, de `st.subheader("Atos de conselho por mês")` até o `st.bar_chart(...)`, por:

```python
st.subheader("Atos de conselho por mês")
por_mes = os.path.join(METRICAS, "atividade_por_mes.csv")
if os.path.exists(por_mes):
    mensal = pd.read_csv(por_mes, parse_dates=["metric_time__month"])
    # A silver das menções lê todo ZIP do bronze e pode ter mês depois do último coberto pelo DOU: sem o corte,
    # esse mês apareceria com zero ato, um silêncio falso. A mart_vitalidade faz o mesmo corte.
    mensal = mensal[mensal["metric_time__month"] <= pd.Timestamp(periodo["ultimo"])]
    mensal["mes"] = mensal["metric_time__month"].map(mes)
    st.bar_chart(mensal, x="mes", y=["atos_publicados", "mencoes_recebidas"], sort=False)
    st.caption("Métricas atos_publicados (atos do próprio conselho no DOU) e mencoes_recebidas (matérias de outros órgãos), da camada semântica.")
else:
    st.info("As métricas da camada semântica ainda não foram exportadas: rode make metricas.")
```

  - No fim do arquivo, depois do `st.dataframe(tipologia...)`, acrescente:

```python
por_conselho = os.path.join(METRICAS, "atividade_por_conselho.csv")
if os.path.exists(por_conselho):
    p = v[["orgao_id", "nome"]].merge(pd.read_csv(por_conselho).rename(columns={"conselho": "orgao_id"}), on="orgao_id")
    p = p.dropna(subset=["proporcao_autorregulacao"])
    st.caption("Autorregulação: atos AUTO sobre os atos já classificados (métrica proporcao_autorregulacao). Perto de 1, o conselho cuida mais de si que da política pública.")
    st.dataframe(p[["nome", "proporcao_autorregulacao"]].rename(columns={"nome": "Conselho", "proporcao_autorregulacao": "Autorregulação"}), hide_index=True)
```

Rode: `make test-painel`. Esperado: todos os testes passam.

- [ ] **Passo 3: o teste da página Revisar, que falha.** Crie `tests/painel/test_revisar.py`:

```python
"""A página Revisar (E4) sem banco: ela avisa, não quebra. O caminho com banco é provado à mão, com print
(Passo 6), e as permissões do papel app_curadoria, pelo tests/db/test_acesso.sh."""

import os
import unittest

from streamlit.testing.v1 import AppTest

PAGINA = "/app/pages/1_Revisar.py"


class Revisar(unittest.TestCase):
    def test_sem_banco_avisa(self):
        os.environ["PGHOST"] = "127.0.0.1"   # no container de teste, sem banco nesta porta
        os.environ["PGPORT"] = "1"
        at = AppTest.from_file(PAGINA).run(timeout=30)
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("make up" in e.value for e in at.error), [e.value for e in at.error])


if __name__ == "__main__":
    unittest.main()
```

Rode: `make test-painel`. Esperado: falha, porque a página não existe.

- [ ] **Passo 4: a página Revisar.** Em `src/painel/requirements.txt`, acrescente `psycopg[binary]==3.2.5`.

Crie `src/painel/pages/1_Revisar.py`:

```python
"""Revisar (E4, ADR 0011): os alertas que o ETL reverso gravou no Postgres, para a curadoria tratar. A página entra
como app_curadoria: lê o alerta e o nome do revisor, nunca o e-mail, e só marca o alerta como tratado."""

import os

import psycopg
import streamlit as st

st.title("Alertas para revisar")

TIPOS = {"em_silencio": "em silêncio", "citado_sem_ato_proprio": "citado, sem ato próprio"}


def conecta():
    return psycopg.connect(host=os.environ.get("PGHOST", "db"), port=int(os.environ.get("PGPORT", 5432)),
                           dbname=os.environ.get("PGDATABASE"), user=os.environ.get("PAINEL_PGUSER"),
                           password=os.environ.get("PAINEL_PGPASSWORD"), connect_timeout=3)


try:
    with conecta() as conn:
        abertos = conn.execute("""
            select a.id, coalesce(n.nome, '(sem nome vigente)'), a.tipo, a.mes_referencia, a.detalhe
            from alerta a left join orgao_nome n on n.orgao_id = a.orgao_id and n.data_fim is null
            where a.tratado_em is null
            order by a.mes_referencia desc, 2, a.tipo""").fetchall()
        revisores = conn.execute("select id, nome from revisor where tipo = 'HUMANO' order by nome").fetchall()
except psycopg.OperationalError:
    st.error("Sem conexão com o banco da curadoria: suba o Postgres com make up.")
    st.stop()

st.caption("Cada alerta vem da situação do conselho na gold, gravada pelo ETL reverso a cada mês. Tratar é registrar o que foi conferido; o alerta sai da lista e fica no banco.")
if not abertos:
    st.success("Nenhum alerta aberto.")
    st.stop()
if not revisores:
    st.error("Nenhum revisor humano cadastrado: rode make carga.")
    st.stop()

quem = st.selectbox("Quem está revisando", revisores, format_func=lambda r: r[1])
for id_, conselho, tipo, mes_ref, detalhe in abertos:
    with st.container(border=True):
        st.markdown(f"**{conselho}** · {TIPOS[tipo]} · {mes_ref:%m/%Y}")
        st.write(detalhe)
        nota = st.text_input("O que foi conferido", key=f"nota{id_}")
        if st.button("Marcar como tratado", key=f"ok{id_}"):
            with conecta() as conn:
                conn.execute("update alerta set tratado_em = now(), tratado_por = %s, nota = %s "
                             "where id = %s and tratado_em is null", (quem[0], nota or None, id_))
            st.rerun()
```

No `docker-compose.yml`, no serviço `painel`:
- troque o comentário "o painel lê a gold só para leitura; não fala com o Postgres" por "o painel lê a gold só para leitura; a página Revisar fala com o Postgres como app_curadoria (ADR 0011)";
- acrescente ao `environment:`:

```yaml
      PGHOST: db
      PGDATABASE: ${POSTGRES_DB}
      PAINEL_PGUSER: app_curadoria
      PAINEL_PGPASSWORD: ${APP_CURADORIA_PASSWORD:-app_curadoria}
```

- e acrescente, no mesmo nível do `environment:`:

```yaml
    depends_on:
      db:
        condition: service_healthy
```

O `make test-painel` roda com `--no-deps`, então o teste segue sem banco.

- [ ] **Passo 5: os testes passam.** Rode: `make test-painel`. Esperado: todos `OK`, inclusive o `test_revisar`.

- [ ] **Passo 6: de ponta a ponta, com print.** Rode `make metricas && make alertas && make painel`.
  - Abra http://127.0.0.1:8501 e confira que o gráfico mensal mostra atos e menções, e que a tabela de autorregulação aparece.
  - Abra Revisar e confira os 10 alertas.
  - Marque **um** como tratado, com a nota "conferido para a demonstração da E4".
  - Salve os prints da página principal e da Revisar em `docs/adr/medicoes/0011-disponibilizacao/painel-metricas.png` e `revisar.png`.

Confira no banco: `SELECT tratado_em IS NOT NULL, nota FROM alerta WHERE nota IS NOT NULL;` deve devolver uma linha. Ela fica no banco de trabalho, como o resto da curadoria.

- [ ] **Passo 7: stage.**

```bash
git add src/painel tests/painel docker-compose.yml docs/adr/medicoes/0011-disponibilizacao
git diff --cached --stat
```

---

### Tarefa 6: a análise de LGPD

**Arquivos:**
- Criar: `docs/lgpd.md`, `docs/lgpd/medir.sql`, `docs/lgpd/medicoes.txt`
- Modificar: `site/.vitepress/config.mts`

**Interfaces:**
- Consome:
  - os papéis e o recorte de coluna (Tarefa 2);
  - o `scripts/anonimizar_revisor.sh` (Tarefa 2).

- [ ] **Passo 1: medir o dado pessoal no banco.** Crie `docs/lgpd/medir.sql`:

```sql
-- Medição do dado pessoal no OLTP (docs/lgpd.md).
-- Uso: docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < docs/lgpd/medir.sql
select 'revisores humanos' as o_que, count(*) from revisor where tipo = 'HUMANO'
union all select 'revisores com e-mail', count(*) from revisor where email is not null
union all select 'atos com CPF mascarado no texto', count(*) from ato where conteudo ~ '\*{3}\.[0-9]{3}\.[0-9]{3}-\*{2}'
-- só a ementa e o começo do texto: no texto inteiro, um regimento que manda "designar os relatores" contaria
union all select 'atos de nomeação, designação ou exoneração', count(*) from ato
  where ementa ~* '(nomea|designa|exonera)' or left(conteudo, 300) ~* '(nomear|designar|exonerar)'
union all select 'atos do DOU', count(*) from ato where origem = 'DOU';
```

Rode:

```bash
{ echo "# Medição do dado pessoal no OLTP, $(date +%F), banco de trabalho com o DOU de julho a setembro de 2026."
  docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < docs/lgpd/medir.sql; } | tee docs/lgpd/medicoes.txt
```

Esperado: uma tabela com as cinco contagens.

- [ ] **Passo 2: a análise.** Crie `docs/lgpd.md`. Cada número sai do `docs/lgpd/medicoes.txt`; troque cada `N` pelo valor medido.

````markdown
# Análise de LGPD

O que a plataforma guarda de dado pessoal, com que base legal, por quanto tempo e como descarta. A medição é de
DD/MM/AAAA, no banco de trabalho ([medicoes.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/lgpd/medicoes.txt)).
Esta análise é da squad, não um parecer jurídico.

## O dado pessoal que existe

| Onde | Dado | Titular | Quanto há |
|---|---|---|---|
| `revisor` | nome e e-mail de quem classifica os atos | a pesquisadora e bolsistas | N revisores humanos, N com e-mail |
| `ato.conteudo` e `ato.ementa` | nomes de pessoas nomeadas, designadas ou exoneradas em atos de conselho; CPF mascarado pela própria Imprensa Nacional | pessoas citadas no DOU | N atos com CPF mascarado; N de nomeação, designação ou exoneração, de N atos do DOU |
| `data/bronze/` e `data/silver/mencoes/` | os mesmos textos, como vieram do DOU | idem | os ZIPs inteiros da Seção 1 |
| `alerta.tratado_por` | quem tratou cada alerta | a curadoria | liga ao `revisor` |

O que **não** existe: dado sensível (art. 5º, II), dado de criança, login de usuário final ou rastreio de quem abre o painel. O painel e a página Revisar não têm conta: rodam só em `127.0.0.1`.

## Base legal e finalidade

- **Os textos do DOU** são dado tornado público pelo próprio poder público. O tratamento considera a finalidade, a boa-fé e o interesse público que justificaram a publicação (art. 7º, § 3º). A finalidade aqui é a mesma: acompanhar o funcionamento de instâncias de participação social. Nada do texto é usado para perfilar a pessoa citada.
- **O nome e o e-mail do revisor** servem para atribuir cada classificação a quem a fez, o que é a auditoria da curadoria (ADR 0001). A base é a realização de estudo por órgão de pesquisa (art. 7º, IV). O projeto é uma pesquisa acadêmica da UnB com a pesquisadora da UFPB.

## Retenção e descarte

| Dado | Retenção | Descarte |
|---|---|---|
| Textos do DOU (bronze, OLTP, silver) | enquanto durar a pesquisa: o histórico é o objeto do estudo (art. 16, II, conservação para estudo por órgão de pesquisa) | apagar `data/` e o volume do banco ao fim do projeto; o DOU continua público na fonte |
| Nome e e-mail do revisor | enquanto ele participar da curadoria | `make anonimizar-revisor ID=n`: o nome vira "Revisor removido", o e-mail some, e as classificações ficam, sem identificar a pessoa |
| Alertas | enquanto a curadoria precisar do histórico | ficam com o tratado por, que aponta um revisor já anonimizado depois do descarte |

## Segurança e acesso (art. 46)

- **Privilégio mínimo:** cada serviço entra no Postgres por um papel com o mínimo que precisa ([ADR 0011](/docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis)).
  - O app de curadoria **não lê o e-mail** do revisor: esse é o recorte de coluna.
  - O dbt só lê os órgãos.
  - O ETL reverso só escreve alertas.
- **Prova:** `bash tests/db/test_acesso.sh`, que roda no `make test`.
- **Portas:** banco, pgAdmin, painel e Dagster publicados só em `127.0.0.1`.
- **Senhas:** só no ambiente; o repositório tem o padrão de desenvolvimento.

## Quando revisar esta análise

- Antes de ligar a aba Perguntar: ela manda trechos do DOU e a pergunta da pesquisadora à API do Claude, o que é uma transferência internacional (art. 33).
- Se o painel ganhar login ou sair de `127.0.0.1`.
- Se entrar uma fonte com dado pessoal que não seja público, como lista de conselheiros com contato.
````

- [ ] **Passo 3: a página no menu.** Em `site/.vitepress/config.mts`, no grupo "Dados e qualidade" da barra lateral, acrescente `{ text: 'LGPD (E4)', link: '/docs/lgpd' },`.

Rode: `npm --prefix site run build 2>&1 | grep -E '^[A-Za-z]*Error:|dead link|build complete'`

Esperado: só `build complete`.

- [ ] **Passo 4: stage.**

```bash
git add docs/lgpd.md docs/lgpd/medir.sql docs/lgpd/medicoes.txt site/.vitepress/config.mts
git diff --cached --stat
```

---

### Tarefa 7: a linhagem até o consumo

**Arquivos:**
- Modificar: `src/linhagem/__init__.py`, `tests/linhagem/test_linhagem.py`, `site/.vitepress/theme/LinhagemInterativa.vue`, `site/linhagem.md`

**Interfaces:**
- Consome: o `manifest.json` do dbt, que agora traz `semantic_models`, `metrics` e `saved_queries`.
- Produz: o diagrama gerado com as camadas "semântica" (modelos semânticos e métricas) e "consultas salvas".

- [ ] **Passo 1: o teste, que falha.** Em `tests/linhagem/test_linhagem.py`, acrescente ao `MANIFEST`, no mesmo nível de `"nodes"`:

```python
    "semantic_models": {
        "semantic_model.p.atos": {"name": "atos", "depends_on": {"nodes": ["model.p.fct_ato"]}},
    },
    "metrics": {
        "metric.p.atos_publicados": {"name": "atos_publicados", "depends_on": {"nodes": ["semantic_model.p.atos"]}},
    },
    "saved_queries": {
        "saved_query.p.atividade_por_mes": {"name": "atividade_por_mes", "depends_on": {"nodes": ["metric.p.atos_publicados"]}},
    },
```

E o teste:

```python
    def test_camada_semantica_ate_a_consulta_salva(self):
        d = mermaid(MANIFEST)
        self.assertIn('subgraph c3["semântica"]', d)
        self.assertIn('subgraph c4["consultas salvas"]', d)
        self.assertIn('["métrica atos_publicados"]', d)
        self.assertEqual(d.count("-->"), 5, "fonte → stg → fct → modelo semântico → métrica → consulta")
```

Troque, no `test_camadas_e_setas`, `self.assertEqual(d.count("-->"), 2, ...)` por `self.assertEqual(d.count("-->"), 5, "a dependência repetida vira uma seta só")`.

Rode: `PYTHONPATH=src python3 -m unittest discover -s tests/linhagem`. Esperado: falha em `semântica`.

- [ ] **Passo 2: o gerador.** Em `src/linhagem/__init__.py`:
  - No fim de `nos()`, antes do `return out`, acrescente:

```python
    for uid, s in manifest.get("semantic_models", {}).items():
        out[uid] = ("semântica", f"modelo semântico {s['name']}")
    for uid, m in manifest.get("metrics", {}).items():
        out[uid] = ("semântica", f"métrica {m['name']}")
    for uid, q in manifest.get("saved_queries", {}).items():
        out[uid] = ("consultas salvas", q["name"])
```

  - Em `mermaid()`, troque `[c for c in ("seed", "staging", "marts") if c in camadas]` por `[c for c in ("seed", "staging", "marts", "semântica", "consultas salvas") if c in camadas]`.
  - Troque `n = manifest.get("nodes", {}).get(uid)` por:

```python
        n = next((manifest[k][uid] for k in ("nodes", "semantic_models", "metrics", "saved_queries")
                  if uid in manifest.get(k, {})), None)
```

Rode o teste do Passo 1. Esperado: `Ran 5 tests` e `OK`.

- [ ] **Passo 3: regerar o catálogo e o diagrama.** Rode: `make gold && make gold-docs`

Esperado: em `site/linhagem.md`, entre os marcadores, as camadas "semântica" e "consultas salvas". O `public/linhagem/catalogo-dbt.html` é regerado. Confira que não há senha nele: `grep -c "password=" public/linhagem/catalogo-dbt.html` deve dar `0`.

- [ ] **Passo 4: a linhagem interativa até o alerta.** Em `site/.vitepress/theme/LinhagemInterativa.vue`:
  - Troque `const COLUNAS = ['Fontes', 'Bronze e OLTP', 'Silver · Delta', 'Gold · dbt', 'Consumo', 'Resposta']` por `const COLUNAS = ['Fontes', 'Bronze e OLTP', 'Silver · Delta', 'Gold · dbt', 'Consumo', 'Resposta e ação']`.
  - No array `NOS`, depois do nó `freshness`, acrescente:

```ts
  { id: 'metricas', col: 4, y: 60, cor: 'teal', titulo: 'Métricas', sub: 'camada semântica', onde: 'MetricFlow · data/gold/metricas/',
    texto: 'Cada métrica definida uma vez, em YAML: atos publicados, menções recebidas e a proporção de autorregulação. As consultas salvas viram CSV depois da gold, lido pelo painel e por quem quiser os números.',
    gera: 'make metricas, ou o asset metricas', testes: 'mf validate-configs; tests/metricas',
    links: [['ADR 0011', '/docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis']] },
  { id: 'alerta', col: 5, y: 410, cor: 'purple', titulo: 'alerta', sub: 'ETL reverso', onde: 'Postgres · OLTP',
    texto: 'A situação tratada na gold volta ao Postgres: o conselho em silêncio, ou sem ato próprio mas citado. A pesquisadora trata o alerta na página Revisar.',
    gera: 'make alertas, ou o asset alertas', testes: 'tests/alertas, tests/dou_db/test_alertas.py, tests/db/test_acesso.sh',
    links: [['ADR 0011', '/docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis'], ['LGPD', '/docs/lgpd']] },
```

  - No array `LIGACOES`, acrescente:

```ts
  ['fct_ato', 'metricas'],
  ['fct_mencao', 'metricas'],
  ['metricas', 'painel', 'consultas salvas'],
  ['mart', 'alerta', 'ETL reverso'],
```

  - No nó `painel`, troque o `texto` por: `'Lê a gold em modo só leitura e as métricas da camada semântica. A página Revisar mostra os alertas e marca o que a pesquisadora conferiu, entrando no Postgres como app_curadoria.'`.
  - No array `PASSOS`, troque o passo 5 por:

```ts
  { titulo: '5. Resposta e ação', texto: 'A mart responde quais conselhos funcionam, a camada semântica define as métricas que o painel lê, e o ETL reverso leva o que pede ação ao Postgres, onde a pesquisadora trata o alerta.', ids: ['mart', 'freshness', 'metricas', 'painel', 'alerta'] },
```

Rode `npm --prefix site run build 2>&1 | grep -E '^[A-Za-z]*Error:|dead link|build complete'` e abra http://localhost:5173/conselhos-vivos/linhagem. Confira que a seta "ETL reverso" não cruza uma caixa. Se cruzar, ajuste o `y` do nó `alerta`.

- [ ] **Passo 5: stage.**

```bash
git add src/linhagem tests/linhagem site/.vitepress/theme/LinhagemInterativa.vue site/linhagem.md public/linhagem/catalogo-dbt.html
git diff --cached --stat
```

---

### Tarefa 8: ADR 0011 e o portfólio

**Arquivos:**
- Criar: `docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis.md`, `docs/adr/medicoes/0011-disponibilizacao/medir.py`, `docs/adr/medicoes/0011-disponibilizacao/medir.sh`
- Modificar: `docs/adr/README.md`, `site/.vitepress/config.mts`

**Interfaces:**
- Consome: as provas das Tarefas 1 a 5 em `docs/adr/medicoes/0011-disponibilizacao/`.

- [ ] **Passo 1: as medições.** Crie `docs/adr/medicoes/0011-disponibilizacao/medir.py`, que roda no projeto dbt do orquestrador:

```python
"""Medições do ADR 0011, rodadas em /app/dbt: o MetricFlow contra a opção nula (SQL direto na gold)."""

import csv
import subprocess
import time

import duckdb

print("## mf query de cada consulta salva")
for q in ("atividade_por_mes", "atividade_por_conselho"):
    s = time.time()
    subprocess.run(["mf", "query", "--saved-query", q, "--csv", f"/tmp/{q}.csv"], check=True, capture_output=True)
    with open(f"/tmp/{q}.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    print(f"{q}: {len(linhas)} linhas em {time.time() - s:.1f} s")
    if q == "atividade_por_mes":
        for l in linhas:
            print("  ", l["metric_time__month"][:7], l["atos_publicados"])

print("## o SQL que o MetricFlow gerou para atividade_por_mes")
print(subprocess.run(["mf", "query", "--saved-query", "atividade_por_mes", "--explain"],
                     check=True, capture_output=True, text=True).stdout)

print("## opção nula: atos por mês em SQL direto na gold")
with duckdb.connect("/data/gold/conselhos.duckdb", read_only=True) as c:
    s = time.time()
    r = c.sql("select date_trunc('month', data_publicacao) as mes, count(*) from fct_ato "
              "where origem = 'DOU' group by 1 order by 1").fetchall()
    print(f"{len(r)} linhas em {time.time() - s:.3f} s")
    for mes, atos in r:
        print("  ", f"{mes:%Y-%m}", atos)
```

E `docs/adr/medicoes/0011-disponibilizacao/medir.sh`:

```bash
#!/usr/bin/env bash
# Medições do ADR 0011. Uso:
#   bash docs/adr/medicoes/0011-disponibilizacao/medir.sh | tee docs/adr/medicoes/0011-disponibilizacao/medicoes.txt
set -euo pipefail
cd "$(dirname "$0")/../../../.."
echo "# Medições do ADR 0011, $(date -u '+%Y-%m-%d %H:%M') UTC"
docker compose --progress quiet run --rm -T orquestrador sh -c 'cd /app/dbt && dbt parse -q && python /app/docs/adr/medicoes/0011-disponibilizacao/medir.py'
echo "## tamanho do que o consumo lê"
du -h data/gold/conselhos.duckdb data/gold/metricas/*.csv
```

Rode a linha de uso do comentário. Esperado:
- as duas consultas, com linhas e segundos;
- o SQL gerado;
- os mesmos números de atos por mês em SQL direto, que precisam bater com o CSV;
- os tamanhos.

Se os números de atos por mês não baterem entre o MetricFlow e o SQL direto, **pare**: a métrica está errada.

- [ ] **Passo 2: o ADR.** Crie `docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis.md`. Preencha cada número com o `medicoes.txt` e com as provas das Tarefas 3 e 4:

````markdown
# 0011 — Disponibilizar as métricas por uma camada semântica no MetricFlow, levar os alertas ao Postgres por push e dar a cada serviço um papel com privilégio mínimo

- **Status:** proposto
- **Data:** AAAA-MM-DD
- **Decisores:** a squad — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf), Marcio (@DeM4rcio)

## Contexto

A E3 entregou a gold e um painel que responde à pergunta da E1 ([ADR 0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md)). A E4 pede quatro coisas:
- que o dado chegue a quem decide por dois caminhos, o painel e uma camada semântica com a definição de cada métrica;
- que uma métrica volte a um sistema operacional onde alguém age;
- que o acesso siga o privilégio mínimo;
- que o dado pessoal seja tratado com base legal.

Até a E3, o painel calculava "atos por mês" no próprio código, e esse número não existia fora dele.

## Decisão

1. **Camada semântica no MetricFlow do dbt.** As métricas `atos_publicados`, `atos_classificados`, `atos_de_autorregulacao`, `proporcao_autorregulacao` e `mencoes_recebidas` ficam definidas uma vez, no YAML dos modelos. As consultas salvas `atividade_por_mes` e `atividade_por_conselho` viram CSV em `data/gold/metricas/` depois da gold, no job mensal. O painel lê esses CSVs; quem quiser os números fora do painel abre o mesmo arquivo.
2. **Cópia por arquivo, não federação nem warehouse.** O consumo lê CSV e o DuckDB em modo só leitura. Não há servidor de consulta a manter.
3. **ETL reverso por push.** Depois da gold, o job grava na tabela `alerta` do Postgres a situação que pede ação. A gravação é idempotente e não reescreve alerta já tratado. A pesquisadora trata o alerta na página Revisar do painel.
4. **Papéis com privilégio mínimo:**
   - `etl_reverso` só escreve alerta;
   - `app_curadoria` lê o alerta e o nome do revisor, nunca o e-mail (o recorte de coluna), e só marca o alerta como tratado;
   - `leitor_analitico` é o dbt lendo os órgãos.

## Alternativas consideradas

- **Visões materializadas escritas à mão, a opção nula da camada semântica:** um modelo `metricas` no dbt, com a definição na descrição de cada coluna. Não pede dependência nova e lê igual. Perde a validação da definição (`mf validate-configs`), as métricas de razão sem SQL novo e a consulta por dimensão sob demanda. Medido: o mesmo "atos por mês" em SQL direto levou N s, contra N s do MetricFlow (`medicoes.txt`).
- **CSV agendado direto da gold, sem camada semântica:** é a opção nula do consumo. O arquivo seria o mesmo, mas a definição da métrica voltaria a morar no SQL de quem exporta.
- **Federação (o painel consultando o Postgres e o Delta ao vivo) ou um warehouse:** mais um serviço para a pesquisadora manter, para um volume de N MB de gold.
- **ETL reverso por pull (a curadoria consulta a gold quando quer):** o alerta não chegaria a quem age. O enunciado pede que a métrica volte ao sistema operacional.
- **Row-level security no lugar do recorte de coluna:** não há hoje um recorte de linha com sentido de negócio. O dado pessoal está numa coluna, o e-mail do revisor.

## Consequências

- **Um número, uma definição:** o painel não recalcula a métrica, e a camada semântica é validada a cada `make metricas`.
- **O job mensal ganha dois passos depois da gold, com o mesmo retry.** O MetricFlow abre o DuckDB para escrita, então a exportação só roda em sequência com o dbt.
- **A página Revisar fala com o Postgres.** Ela só roda em `127.0.0.1` e não tem login: quem marca o alerta escolhe o próprio nome na lista.
- **O superusuário ainda roda a carga, o lake e o CDC.** Os papéis novos cobrem o consumo, não a ingestão.

## Medições

| O que | Resultado | Prova |
|---|---|---|
| `mf query` das consultas salvas | N linhas em N s e N linhas em N s | `medicoes.txt` |
| SQL direto, opção nula | os mesmos números, em N s | `medicoes.txt` |
| ETL reverso, duas rodadas | `novos=10`, depois `inalterados=10` | `alertas-idempotencia.txt` |
| Job mensal com os dois passos novos | `RUN_SUCCESS` | `backfill-*.txt`, `grafo-dagster.jpg` |
| Controle de acesso | N casos em `ok` | `bash tests/db/test_acesso.sh` |

## Gatilho de revisão

- A pesquisadora pedir métrica por uma dimensão que o MetricFlow não junte sozinho: por exemplo, pelo nome vigente do conselho, que mora numa dimensão de variação lenta.
- O `dbt-metricflow` ficar sem versão compatível com o dbt-core que o projeto usar.
- O painel sair de `127.0.0.1` ou ganhar mais de um usuário: aí a página Revisar precisa de login, e o `tratado_por` deixa de ser escolhido numa lista.
- Aparecer um recorte por linha com sentido, como bolsistas que só tratam alertas de alguns conselhos: aí entra RLS em `alerta`.
````

- [ ] **Passo 3: o portfólio.** No `docs/adr/README.md`:
  - Acrescente ao índice a linha `| [0011](0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis.md) | Disponibilizar as métricas por camada semântica no MetricFlow, alertas ao Postgres por push e papéis com privilégio mínimo | proposto |`.
  - Depois do índice, acrescente:

```markdown
## Portfólio

O que cada ADR cobre no projeto da disciplina. Todo ADR tem a seção "Gatilho de revisão": o que, se acontecer, reabre a decisão.

| Item | ADRs |
|---|---|
| Modelagem do sistema de origem (E1) | [0001](0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md), [0002](0002-manter-postgresql-como-motor-do-oltp.md), [0003](0003-carregar-a-planilha-como-rotulo-da-curadoria.md), [0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md) |
| Mecanismo de ingestão, com a opção nula (E2) | [0005](0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc.md), [0006](0006-armazenar-a-camada-analitica-em-tabelas-delta.md), [0007](0007-propagar-mudancas-por-slot-de-replicacao-logica.md) |
| Modelagem analítica e ferramenta (E3) | [0008](0008-unificar-o-pipeline-em-python.md), [0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md), [0010](0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome.md) |
| Como o dado é disponibilizado (E4) | [0011](0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis.md) |
```

  - Em `site/.vitepress/config.mts`, no grupo "Decisões (ADRs)", acrescente `{ text: '0011 · Camada semântica, ETL reverso e papéis', link: '/docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis' },`.

- [ ] **Passo 4: stage.**

```bash
git add docs/adr/0011-*.md docs/adr/medicoes/0011-disponibilizacao docs/adr/README.md site/.vitepress/config.mts
git diff --cached --stat
```

---

### Tarefa 9: retrospectiva, defesa, página da entrega e tag

**Arquivos:**
- Criar: `site/entrega-e4.md`, `docs/diario/2026-11-24.md`, `docs/defesa.md`
- Modificar:
  - `site/.vitepress/config.mts`, `site/arquitetura.md`, `site/.vitepress/theme/ArquiteturaInterativa.vue`, `site/jornada-do-dado.md`;
  - `README.md`, `AI-USAGE.md`.

- [ ] **Passo 1: a página da entrega.** Crie `site/entrega-e4.md` no molde do `site/entrega-e3.md`:
  - **Abertura:** a frase de abertura e o bloco "Conferir em máquina limpa", com `make setup`, `make test`, `make demo-backfill DE=2026-07 ATE=2026-09`, `make gold`, `make metricas`, `make alertas` e `make painel`.
  - **Entregáveis:** uma tabela com o que, onde está e como conferir, com uma linha por peça das Tarefas 1 a 8.
  - **Checklist de aceite:** os oito itens do enunciado, cada um com o link da prova.
  - **Uma seção por item,** curta, com o que foi feito e o número medido.
  - **Limites conhecidos e pendências da squad.**

  No menu, ponha "Entrega E4" antes da E3, na `nav` e na barra lateral "Comece aqui". Siga o `'site/entrega-e3.md': 'entrega-e3.md'` dos `rewrites`.

- [ ] **Passo 2: a arquitetura com a E4 entregue.** Em `site/.vitepress/theme/ArquiteturaInterativa.vue`, troque `situacao: 'E4'` por `situacao: 'pronto'` nas partes `alertas` e `revisar`. No texto da `gold`, acrescente: "As métricas ficam na camada semântica do MetricFlow (ADR 0011)."

Em `site/arquitetura.md`:
- Na tabela de ferramentas:
  - as linhas "Camada semântica", "ETL reverso" e "Controle de acesso" passam a `✅ E4`;
  - a ferramenta da camada semântica fica "MetricFlow (`dbt-metricflow`), consultas salvas exportadas em CSV".
- Na seção "O que cada entrega cobre", a tabela da E4 ganha a coluna de entrega e o título `### E4 ✅ · Plataforma completa, governada e defendida`, com as provas.
- A "Decisões em aberto" perde a camada semântica, que foi decidida no ADR 0011.

Na `site/jornada-do-dado.md`, a linha "Disponibilização" do ciclo de vida passa a `E3 ✅ painel · E4 ✅ camada semântica e alertas`.

- [ ] **Passo 3: a retrospectiva.** Crie `docs/diario/2026-11-24.md`, no formato dos diários (período, quem trabalhou, pauta, o que foi feito, pendente), com a seção:

```markdown
## Retrospectiva do ciclo de vida

| Estágio | O que fizemos | O que mudou no caminho | O que faríamos diferente |
|---|---|---|---|
| Geração | ... | ... | ... |
| Armazenamento | ... | ... | ... |
| Ingestão | ... | ... | ... |
| Transformação | ... | ... | ... |
| Disponibilização | ... | ... | ... |
```

Cada célula é escrita pela squad. Os fatos para cada estágio estão:
- nos diários de 25/09 a 10/11;
- no "O que foi decidido" de cada diário;
- nos ADRs 0001 a 0011.

Pontos que não podem faltar:
- a planilha como rótulo (ADR 0003);
- a troca do INLABS pelos dados abertos (ADR 0008);
- o slot lógico no lugar do Kafka (ADR 0007);
- a ausência como o que se mede (ADR 0009);
- o escopo de 82 para 59 conselhos (ADR 0010);
- o DOU vazio que quase passou calado em três lugares (diário de 10/11);
- a camada semântica e os alertas (ADR 0011).

Nenhum número é escrito de memória: cada um sai de um arquivo de `docs/adr/medicoes/`.

- [ ] **Passo 4: o roteiro da defesa.** Crie `docs/defesa.md`, com 20 minutos divididos entre as duas metades da banca:

```markdown
# Defesa da E4: roteiro

| Min | Quem | Para quem | O quê |
|---|---|---|---|
| 0–3 | | gestão | A pergunta: quais conselhos de participação social ainda funcionam? Por que ninguém sabe hoje. |
| 3–7 | | gestão | A resposta no painel: ativos, sem ato, citados por outros órgãos, e os limites do que o DOU mostra. |
| 7–10 | | gestão e técnica | A página Revisar: um alerta, quem o trata, e por que ele não vira uma decisão automática. |
| 10–15 | | técnica | O caminho do dado na linhagem interativa, do ZIP ao alerta, com o ADR de cada trecho. |
| 15–18 | | técnica | Governança: a métrica com uma definição só, o papel que não vê o e-mail, a LGPD. |
| 18–20 | | as duas | O que faríamos diferente (retrospectiva) e o que vem depois (a aba Perguntar). |

## Demonstração, na ordem

1. `make painel` → http://127.0.0.1:8501: os três números, a tabela, o gráfico das métricas.
2. Revisar: marcar um alerta como tratado ao vivo.
3. http://localhost:5173/conselhos-vivos/linhagem: "Percorrer a linhagem".
4. `bash tests/db/test_acesso.sh`: o `permission denied` do e-mail.

## Plano B

Se a rede ou o Docker falharem: os prints em `docs/adr/medicoes/0011-disponibilizacao/` e o site publicado.
```

A coluna "Quem" a squad preenche no ensaio.

- [ ] **Passo 5: a conferência num clone limpo.** Como na E3:
  1. Pare o ambiente de trabalho com `docker compose stop`.
  2. Clone o `main` noutra pasta e copie para o bronze dela os ZIPs de julho a setembro.
  3. Rode `make setup`, `make test`, `make demo-backfill DE=2026-07 ATE=2026-09`, `make gold`, `make metricas`, `make alertas` e `make demo-retry`.

Esperado: todos verdes; `make alertas` com `novos=10`.

Guarde o resumo em `docs/adr/medicoes/0011-disponibilizacao/clone-limpo-AAAAMMDD.txt`. Use o mesmo filtro do `clone-limpo-20261109.txt` da E3 e confira que a senha não aparece em forma de credencial. Depois:
1. derrube o projeto do clone;
2. apague os volumes dele e a pasta;
3. suba o ambiente de trabalho com `docker compose start`.

- [ ] **Passo 6: fechar.**
  - Acrescente as entradas da E4 ao `AI-USAGE.md` e a seção da E4 ao `README.md`.
  - Rode `npm --prefix site run build 2>&1 | grep -E '^[A-Za-z]*Error:|dead link|build complete'`. Esperado: só `build complete`.
  - Stage, e commit com o ok da Luiza.
  - Com o CI verde no `main`, crie a tag anotada `e4`, com a mensagem "Entrega E4: plataforma completa, governada e defendida", e a release "Entrega 4", em pre-release, no molde da `e3`.

---

## Autoconferência do plano

- **Os oito itens do enunciado têm tarefa:** a tabela do começo aponta cada um.
- **Nenhuma senha no repositório:**
  - os papéis leem a senha do ambiente;
  - os testes de acesso entram pelo socket do container;
  - o catálogo é conferido com `grep`.
- **Nomes que atravessam tarefas:**
  - `metric_time__month` e `conselho` (Tarefa 1 → 5);
  - `ALERTAS_PGUSER` e `ALERTAS_PGPASSWORD` (Tarefa 2 → 3);
  - `PAINEL_PGUSER` e `PAINEL_PGPASSWORD` (Tarefa 2 → 5);
  - o slug do ADR 0011 (Tarefas 6, 7 e 8).
- **Riscos que o plano já trata:**
  - o MetricFlow não instalar (Tarefa 1, Passo 1, com a volta à squad);
  - a coluna de tempo do CSV ter outro nome (Tarefa 1, Passo 5);
  - o DuckDB travado entre o MetricFlow e o dbt (os dois passos em sequência no mesmo job);
  - o teste do painel ler o CSV de verdade (`PAINEL_METRICAS` apontado para o temporário).
