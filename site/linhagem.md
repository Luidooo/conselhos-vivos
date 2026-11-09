---
title: Linhagem dos dados
outline: [2, 3]
---

# Linhagem dos dados

De onde vem cada número do painel: do ZIP do Diário Oficial até a tabela que responde à pergunta da E1. A linhagem está em três níveis, do mais geral ao mais detalhado.

## Do dado bruto ao painel

<LinhagemInterativa />

<p class="cv-legenda">Clique numa tabela para ver o que ela guarda, o comando que a gera e os testes que a protegem, ou percorra a linhagem passo a passo.</p>

O Dagster roda os passos do ZIP até a gold num job mensal: `atos_do_mes` → `silver/atos` e `silver/mencoes` → modelos do dbt, com retry e backfill. O grafo dele, como aparece na interface, está em [grafo-dagster.jpg](https://github.com/Luidooo/conselhos-vivos/blob/main/docs/adr/medicoes/0009-gold/grafo-dagster.jpg).

## Dentro do dbt

Gerado do `manifest.json` do dbt pelo `make gold-docs`: é sempre o projeto como está, modelo a modelo, das fontes aos marts.

<!-- linhagem-dbt:inicio -->
```mermaid
flowchart LR
  subgraph c0["fonte oltp"]
    n12["oltp.conselho"]
    n13["oltp.orgao"]
    n14["oltp.orgao_nome"]
  end
  subgraph c1["fonte silver"]
    n15["silver.atos"]
    n16["silver.mencoes"]
  end
  subgraph c2["seed"]
    n11["conselhos_excluidos"]
  end
  subgraph c3["staging"]
    n6["stg_atos"]
    n7["stg_conselho"]
    n8["stg_mencoes"]
    n9["stg_orgao"]
    n10["stg_orgao_nome"]
  end
  subgraph c4["marts"]
    n0["dim_conselho"]
    n1["fct_ato"]
    n2["fct_conselho_mes"]
    n3["fct_mencao"]
    n4["freshness_vitalidade"]
    n5["mart_vitalidade"]
  end
  n7 --> n0
  n9 --> n0
  n10 --> n0
  n11 --> n0
  n0 --> n1
  n6 --> n1
  n0 --> n2
  n1 --> n2
  n0 --> n3
  n8 --> n3
  n2 --> n4
  n0 --> n5
  n2 --> n5
  n3 --> n5
  n15 --> n6
  n12 --> n7
  n16 --> n8
  n13 --> n9
  n14 --> n10
```
<!-- linhagem-dbt:fim -->

## O catálogo completo

O [catálogo do dbt](/linhagem/catalogo-dbt.html){target="_blank"} tem a linhagem interativa de cada modelo, com as colunas, as descrições, os testes e o SQL compilado. Ele é gerado pelo `make gold-docs` (`dbt docs generate --static`) e publicado junto com este site.

Para regerar depois de mudar um modelo:

```bash
make gold && make gold-docs
```
