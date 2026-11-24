---
title: Entrega E4
outline: [2, 3]
---

# Entrega E4 — plataforma completa, governada e defendida

A E3 respondeu à pergunta da E1 num painel. A E4 faz a resposta chegar a quem decide por dois caminhos, o painel e uma camada semântica, leva de volta ao Postgres o que pede ação, e fecha a governança: linhagem até o consumo, LGPD, controle de acesso e o portfólio das decisões. A decisão está no [ADR 0011](/docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis).

As provas estão em [`docs/adr/medicoes/0011-disponibilizacao/`](https://github.com/Luidooo/conselhos-vivos/tree/main/docs/adr/medicoes/0011-disponibilizacao), com o DOU de julho a setembro de 2026 e os 215 atos da planilha.

::: tip Conferir em máquina limpa
```bash
git clone https://github.com/Luidooo/conselhos-vivos.git && cd conselhos-vivos
make setup                                  # .env, Postgres, migrações (com os papéis) e a planilha
make test                                   # inclui o teste de acesso de cada papel
make demo-backfill DE=2026-07 ATE=2026-09   # três meses pelo Dagster, até as métricas e os alertas
make gold                                   # a gold, com os testes do dbt
make metricas                               # valida a camada semântica e exporta as consultas salvas
make alertas                                # o ETL reverso: novos=10 na primeira rodada
make painel                                 # http://127.0.0.1:8501, com a página Revisar
```
Pré-requisitos: Docker com Compose v2, `make` e `sqlite3`. O backfill baixa os ZIPs dos dados abertos.

**A conferência num clone limpo do `main` ainda não foi feita para a E4.** Ela é o último passo antes da tag `e4`.
:::

## Entregáveis

| O que | Onde está | Como conferir |
|---|---|---|
| **Camada semântica** | `dbt/models/marts/marts.yml` · `dbt/models/metricas/` · `src/metricas/` | `make metricas`: cinco métricas e duas consultas salvas, em CSV |
| **Painel lendo a camada semântica** | `src/painel/app.py` | `make painel`: os atos por mês e a autorregulação vêm dos CSV |
| **ETL reverso** | `src/alertas/` · tabela `alerta` (`sql/007`) | `make alertas`: `novos=10`, depois `inalterados=10` |
| **Página Revisar** | `src/painel/pages/1_Revisar.py` | a pesquisadora marca o alerta como tratado |
| **Métricas e alertas no job mensal** | `src/orquestracao/` · assets `metricas` e `alertas` | `make demo-backfill`: seis passos em `STEP_SUCCESS` |
| **Papéis com privilégio mínimo** | `sql/007_alertas_e_papeis.sql` | `bash tests/db/test_acesso.sh`: 14 casos |
| **Análise de LGPD** | [LGPD](/docs/lgpd) · `docs/lgpd/` | a medição do dado pessoal no banco |
| **Linhagem até o consumo** | [Linhagem dos dados](/linhagem) · `make gold-docs` | do ZIP do DOU ao alerta |
| **ADR 0011 e portfólio** | [ADR 0011](/docs/adr/0011-disponibilizar-por-camada-semantica-etl-reverso-e-papeis) · [índice dos ADRs](/docs/adr/) | onze ADRs, todos com gatilho de revisão |
| **Retrospectiva e roteiro da defesa** | [diário de 24/11](/docs/diario/2026-11-24) · [defesa](/docs/defesa) | |

## Checklist de aceite

Cada item do [checklist da E4](https://unb-bd2.github.io/PlanoEnsino/projeto/e4/), na ordem da página da disciplina.

| # | Item | Prova |
|---|---|---|
| 1 | Consumo duplo: painel e camada semântica, com a definição versionada de cada métrica | [medicoes.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/medicoes.txt) · [painel-metricas.png](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/painel-metricas.png) |
| 2 | ETL reverso: uma métrica tratada volta a um sistema operacional onde alguém age | [alertas-idempotencia.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/alertas-idempotencia.txt) · [revisar.png](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/revisar.png) |
| 3 | Catálogo e linhagem publicados, da fonte ao consumo | [Linhagem dos dados](/linhagem) · [grafo-dagster.jpg](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/grafo-dagster.jpg) |
| 4 | Análise de LGPD: dado pessoal, base legal, retenção e descarte | [LGPD](/docs/lgpd) |
| 5 | Controle de acesso num recorte de coluna, com privilégio mínimo | [acesso.txt](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/acesso.txt) |
| 6 | Portfólio dos ADRs, com os gatilhos de revisão | [índice dos ADRs](/docs/adr/) |
| 7 | Retrospectiva do ciclo de vida no diário | [diário de 24/11](/docs/diario/2026-11-24) |
| 8 | Defesa de 20 minutos, para público técnico e de gestão | [roteiro](/docs/defesa) |

## 1. Consumo duplo: o painel e a camada semântica

As métricas `atos_publicados`, `atos_classificados`, `atos_de_autorregulacao`, `proporcao_autorregulacao` e `mencoes_recebidas` ficam definidas uma vez, no YAML do dbt, e o MetricFlow as valida. As consultas salvas `atividade_por_mes` e `atividade_por_conselho` viram CSV em `data/gold/metricas/` depois da gold. O painel lê esses arquivos, e quem quiser os números fora dele abre os mesmos.

**Medido:** o MetricFlow e o SQL direto na gold dão os mesmos atos por mês, 94 em julho, 56 em agosto e 93 em setembro. O `mf query` leva 8,2 s, contra 0,005 s do SQL direto; esse tempo é pago uma vez por mês, no job.

## 2. ETL reverso: o alerta volta ao Postgres

Depois da gold, o job grava na tabela `alerta` a situação que pede ação: o conselho em silêncio, ou sem ato próprio mas citado por outros órgãos. A gravação é idempotente e não reescreve alerta já tratado. A pesquisadora trata o alerta na página Revisar do painel, que entra no Postgres como `app_curadoria`.

**Medido:** com julho a setembro, a primeira rodada dá `novos=10` e a segunda, `inalterados=10`. Os dez são do tipo "citado, sem ato próprio".

## 3. Catálogo e linhagem até o consumo

A [linhagem interativa](/linhagem) vai do ZIP do DOU até as métricas e o alerta. O diagrama do dbt, gerado do `manifest.json`, ganhou as camadas "semântica" e "consultas salvas", e o catálogo do dbt publicado no site traz as métricas. No Dagster, o job mensal termina nos assets `metricas` e `alertas`.

## 4. Análise de LGPD

A [análise](/docs/lgpd) mede o dado pessoal que está no banco, em vez de descrevê-lo de forma genérica: os revisores com nome e e-mail, e os atos de pessoal entre os 604 atos. Ela dá a base legal de cada dado, a retenção e o descarte. O descarte do revisor é um comando, `make anonimizar-revisor ID=n`, coberto por teste.

## 5. Controle de acesso com privilégio mínimo

Cada serviço entra no Postgres por um papel:
- `etl_reverso` só escreve alerta;
- `app_curadoria` lê o alerta e o nome do revisor, **nunca o e-mail**, e só marca o alerta como tratado. Esse é o recorte de coluna;
- `leitor_analitico` é o dbt lendo os órgãos.

**Medido:** o `tests/db/test_acesso.sh` tem 14 casos, do que cada papel pode e do que não pode, e roda no `make test`.

## 6. Portfólio dos ADRs

O [índice dos ADRs](/docs/adr/) mostra o que cada um dos onze cobre nas quatro entregas. Todos têm a seção "Gatilho de revisão": o que, se acontecer, reabre a decisão.

## 7. Retrospectiva do ciclo de vida

O [diário de 24/11](/docs/diario/2026-11-24) percorre os cinco estágios, da geração à disponibilização: o que foi feito, o que mudou no caminho e o que a squad faria diferente.

## 8. Defesa

O [roteiro](/docs/defesa) divide os 20 minutos entre a gestão e a banca técnica, com a ordem da demonstração e o plano B.

## Limites conhecidos e pendências da squad

- **ADR 0011:** está como "proposto", à espera do aceite da squad.
- **Clone limpo e tag `e4`:** ainda não feitos.
- **Alerta que deixou de valer não fecha sozinho.** Se a gold muda e a regra para de apontar um conselho, o alerta aberto fica até a curadoria fechá-lo.
- **A página Revisar não tem login.** Ela só roda em `127.0.0.1`, e quem marca o alerta escolhe o próprio nome numa lista.
- **O superusuário ainda roda a carga, o lake e o CDC.** Os papéis novos cobrem o consumo, não a ingestão.
- **Além do checklist:** as perguntas P1 e P2 da E1, o assistente de perguntas (RAG) e o dicionário de dados estão nas issues #105 a #112, ainda abertas.
- **O limite de 3 meses da vitalidade** continua provisório, à espera da pesquisadora.
