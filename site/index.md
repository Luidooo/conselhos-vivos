---
layout: home
title: Conselhos Vivos

hero:
  name: Conselhos Vivos
  text: Quais conselhos nacionais de participação social ainda estão funcionando?
  tagline: "Os conselhos nacionais não são extintos quando param de funcionar: eles simplesmente deixam de publicar. Esta plataforma lê o Diário Oficial da União, classifica cada ato e mostra quais conselhos seguem decidindo sobre política pública."
  actions:
    - theme: brand
      text: Conferir a Entrega E1
      link: /entrega-e1
    - theme: alt
      text: Jornada do dado
      link: /jornada-do-dado
    - theme: alt
      text: Como rodar
      link: /visao-geral#como-rodar
    - theme: alt
      text: Decisões
      link: /docs/adr/

features:
  - title: "215"
    details: atos classificados à mão pela pesquisadora, de 5 conselhos (2003–2020), carregados no OLTP com a classificação dela.
    link: /docs/carga/relatorio-planilha
    linkText: Relatório da carga
  - title: "82"
    details: conselhos distintos por trás de 125 nomes, com cada fusão registrada e justificada — nunca por similaridade de texto.
    link: /docs/carga/relatorio-conselhos
    linkText: Identidade dos conselhos
  - title: "4"
    details: ADRs com alternativas, opção nula e medição reproduzível — do OLTP de curadoria ao benchmark de cinco motores.
    link: /docs/adr/
    linkText: Ver as decisões
  - title: "1 comando"
    details: "make setup sobe o banco, aplica as migrações em ordem e carrega a planilha, numa máquina limpa."
    link: /visao-geral#como-rodar
    linkText: Como rodar
---

<div class="cv-home">

## O problema

<p class="cv-lead">A professora Lizandra Serafim (UFPB) pesquisa a produção decisória desses conselhos desde 2003, lendo o DOU ato por ato. Em vinte anos de trabalho manual, cobriu cinco conselhos. Existem entre oitenta e cem.</p>

## A tipologia

<p class="cv-lead">Cada ato é classificado numa de cinco categorias. A distribuição delas ao longo do tempo já é, sozinha, uma medida de saúde: um conselho que só produz <code>AUTO</code> está se auto-administrando, não incidindo em política pública.</p>

| Sigla | Significado |
|---|---|
| `DEF` | Define a política — diretrizes, regulação, orçamento. Ato vinculante, antes da execução. |
| `FISC` | Fiscaliza — aprova ou reprova contas, responsabiliza, aplica sanção. |
| `GEST` | Gestão administrativa da política já definida. |
| `AUTO` | Autorregulação — o conselho falando de si mesmo: regimento, eleições internas, grupos de trabalho. |
| `IP` | Gere outras instâncias participativas — conferências, eleições, comissões setoriais. |

## A arquitetura, em uma frase

<p class="cv-lead">O DOU nasce na Imprensa Nacional, então copiá-lo é ingestão. O dado que nasce aqui é o <strong>julgamento humano</strong> sobre cada ato — por isso o OLTP é o <a href="./docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp">sistema de curadoria, com classificação insert-only</a>, em <a href="./docs/adr/0002-manter-postgresql-como-motor-do-oltp">PostgreSQL 16</a>.</p>

</div>
