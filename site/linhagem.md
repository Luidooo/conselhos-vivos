---
title: Linhagem dos dados
outline: [2, 3]
---

# Linhagem dos dados

De onde vem cada número do painel: do ZIP do Diário Oficial até a tabela que responde à pergunta da E1, e daí até as métricas e o alerta que volta ao Postgres. A linhagem está em três níveis, do mais geral ao mais detalhado.

## Do dado bruto ao painel

<LinhagemInterativa />

<p class="cv-legenda">Clique numa tabela para ver o que ela guarda, o comando que a gera e os testes que a protegem, ou percorra a linhagem passo a passo.</p>

O Dagster roda os passos do ZIP até o alerta num job mensal: `atos_do_mes` → `silver/atos` e `silver/mencoes` → modelos do dbt → `metricas` → `alertas`, com retry e backfill. O grafo dele, como aparece na interface, está em [grafo-dagster.jpg](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0011-disponibilizacao/grafo-dagster.jpg).

## Dentro do dbt

Gerado do `manifest.json` do dbt pelo `make gold-docs`: é sempre o projeto como está, modelo a modelo, das fontes às consultas salvas da camada semântica.

<!-- linhagem-dbt:inicio -->
```mermaid
flowchart LR
  subgraph c0["fonte oltp"]
    n22["oltp.conselho"]
    n23["oltp.orgao"]
    n24["oltp.orgao_nome"]
  end
  subgraph c1["fonte silver"]
    n25["silver.atos"]
    n26["silver.mencoes"]
  end
  subgraph c2["seed"]
    n19["conselhos_excluidos"]
  end
  subgraph c3["staging"]
    n12["stg_atos"]
    n13["stg_conselho"]
    n14["stg_mencoes"]
    n15["stg_orgao"]
    n16["stg_orgao_nome"]
  end
  subgraph c4["marts"]
    n5["dim_conselho"]
    n6["fct_ato"]
    n7["fct_conselho_mes"]
    n8["fct_mencao"]
    n9["freshness_vitalidade"]
    n10["mart_vitalidade"]
    n11["metricflow_time_spine"]
  end
  subgraph c5["semântica"]
    n20["modelo semântico atos"]
    n21["modelo semântico mencoes"]
    n0["métrica atos_classificados"]
    n1["métrica atos_de_autorregulacao"]
    n2["métrica atos_publicados"]
    n3["métrica mencoes_recebidas"]
    n4["métrica proporcao_autorregulacao"]
  end
  subgraph c6["consultas salvas"]
    n17["atividade_por_conselho"]
    n18["atividade_por_mes"]
  end
  n20 --> n0
  n20 --> n1
  n20 --> n2
  n21 --> n3
  n0 --> n4
  n1 --> n4
  n13 --> n5
  n15 --> n5
  n16 --> n5
  n19 --> n5
  n5 --> n6
  n12 --> n6
  n5 --> n7
  n6 --> n7
  n5 --> n8
  n14 --> n8
  n7 --> n9
  n5 --> n10
  n7 --> n10
  n8 --> n10
  n25 --> n12
  n22 --> n13
  n26 --> n14
  n23 --> n15
  n24 --> n16
  n2 --> n17
  n3 --> n17
  n4 --> n17
  n2 --> n18
  n3 --> n18
  n6 --> n20
  n8 --> n21
```
<!-- linhagem-dbt:fim -->

## O catálogo completo

O [catálogo do dbt](/linhagem/catalogo-dbt.html){target="_blank"} tem a linhagem interativa de cada modelo, com as colunas, as descrições, os testes e o SQL compilado. Ele é gerado pelo `make gold-docs` (`dbt docs generate --static`) e publicado junto com este site.

Para regerar depois de mudar um modelo:

```bash
make gold && make gold-docs
```
