---
title: Entrega E2
outline: [2, 3]
aside: false
---

<script setup>
import { onMounted } from 'vue'

const PAINEIS = {
  fonte: {
    rotulo: 'Fonte pública', titulo: 'Dados abertos da Imprensa Nacional',
    texto: 'Um ZIP por mês e por seção, público (CC0), sem login, com o mesmo XML do INLABS e as edições extras dentro. Substituiu o INLABS como fonte automática porque o login dele é recusado a scripts (502). Histórico desde 2002.',
    numeros: ['Agosto/2026: 8.590 matérias, 120 imagens, 0 falhas de leitura', 'O mês sai ~2 semanas depois de acabar (setembro apareceu em 13/10)'],
    comando: 'make fetch-mensal MES=2026-08',
    links: [['ADR 0005', '/docs/adr/0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc'], ['Como o link é encontrado', '/visao-geral#ingerir-um-mes-pelos-dados-abertos']],
  },
  bronze: {
    rotulo: 'Camada bronze', titulo: 'O ZIP guardado como veio',
    texto: 'O arquivo só ganha o nome final depois de validado como ZIP: temporário, cópia, fsync, validação, rename. Mês já em disco não é baixado de novo. Marcadores .sem-edicao e .falhou registram o que foi pedido e não veio.',
    numeros: ['S01082026.zip: 52.565.336 bytes, idêntico (cmp) entre o cliente antigo em Go e o atual em Python', 'Segunda execução: nenhuma requisição'],
    comando: 'ls data/bronze/dados-abertos/',
    links: [['PR #60', 'https://github.com/Luidooo/conselhos-vivos/pull/60'], ['src/dou/bronze.py', 'https://github.com/Luidooo/conselhos-vivos/blob/main/src/dou/bronze.py']],
  },
  oltp: {
    rotulo: 'OLTP de curadoria', titulo: 'Postgres 16: ato e classificacao',
    texto: 'O persist lê cada matéria do ZIP, acha o conselho pela chave normalizada (ADR 0004) e grava em ato só o que é de conselho; o resto vai para a fila orgao_alias. Cada matéria é comparada com todas as versões já gravadas: igual, nada; diferente, versão nova. A classificação é insert-only.',
    numeros: ['96 atos de conselho em agosto; 8.494 de órgão desconhecido fora de ato', 'Rodar de novo: gravadas=0, inalteradas=96, banco idêntico linha a linha'],
    comando: 'make persist-mensal MES=2026-08',
    links: [['ADR 0001', '/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp'], ['Gravar as matérias', '/visao-geral#gravar-as-materias-no-banco']],
  },
  delta: {
    rotulo: 'Camada analítica', titulo: 'Tabela Delta sobre Parquet',
    texto: 'Uma tabela consolidada (ato, órgão vigente na data, tipologia vigente) em data/silver/atos/, particionada por ano de publicação e comprimida com zstd, gravada por MERGE em ato_id. Sem JVM: biblioteca deltalake (Rust/Python). Um ato que chega atrasado cai na partição do ano certo.',
    numeros: ['311 linhas; make lake 2×: inseridas=311, depois inalteradas=311', 'zstd: mesmo tempo de consulta e 20–29% menos disco que snappy; partição anual 12 arquivos contra 112 da diária'],
    comando: 'make lake',
    links: [['ADR 0006', '/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta'], ['test_atrasado.sh', 'https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_atrasado.sh']],
  },
  duckdb: {
    rotulo: 'Consumo', titulo: 'DuckDB lendo o Delta',
    texto: 'O formato é aberto de verdade: o DuckDB lê a tabela com delta_scan sem passar pelo motor que a escreveu. É daqui que sai a distribuição da tipologia por conselho, o insumo do indicador de vitalidade da E3.',
    numeros: ['Agregação tipologia × conselho × ano: ~0,85 ms', 'Contagem do DuckDB bate com o count(*) do banco (teste automatizado)'],
    comando: "SELECT orgao_sigla, tipologia_sigla, count(*) FROM delta_scan('data/silver/atos') GROUP BY 1, 2",
    links: [['test_lake.sh', 'https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_lake.sh']],
  },
  curadoria: {
    rotulo: 'Origem das mudanças', titulo: 'A curadoria reclassifica',
    texto: 'Reclassificar um ato é inserir uma linha nova em classificacao; nada é sobrescrito, e a view classificacao_vigente devolve a última de cada revisor, com a humana vencendo a do pipeline. É a única fonte de mudança que o CDC precisa levar ao Delta.',
    numeros: ['215 classificações da pesquisadora como gabarito', 'make cdc-demo reclassifica, mostra no Delta e restaura'],
    comando: 'make cdc-demo',
    links: [['ADR 0001', '/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp']],
  },
  slot: {
    rotulo: 'Captura', titulo: 'Slot de replicação lógica do Postgres',
    texto: 'O banco sobe com wal_level=logical; um slot (conselhos_lake) com o plugin test_decoding, que vem na imagem oficial, guarda as mudanças de classificacao até alguém consumir. Sem Kafka, sem Debezium, sem JVM: zero containers a mais.',
    numeros: ['Slot em dia: 56 bytes de WAL retido; uma reclassificação pendente: 512 bytes', 'Slot parado retém WAL: make cdc-drop libera'],
    comando: 'make cdc',
    links: [['ADR 0007', '/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica'], ['Fluxo de mudanças', '/visao-geral#fluxo-de-mudancas-do-oltp-ao-delta-cdc']],
  },
  cdc: {
    rotulo: 'Consumidor', titulo: 'make cdc: espia, grava, confirma',
    texto: 'O consumidor espia o slot, relê do OLTP só os atos alterados com a mesma consulta do make lake, grava no Delta por MERGE e só então avança o cursor. Se cair no meio, o evento volta e o MERGE idempotente absorve: pelo menos uma vez na leitura, efetivamente uma vez no destino.',
    numeros: ['Queda forçada entre gravar e confirmar (código 42): reexecução com inalteradas=1, 311 atos antes e depois, 0 duplicatas', 'Incremental de 1 ato: ~58 ms contra ~68 ms da recarga completa'],
    comando: 'make cdc-chaos',
    links: [['ADR 0007', '/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica'], ['test_cdc.sh', 'https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_cdc.sh']],
  },
}

onMounted(() => {
  const host = document.getElementById('cv-arq-svg')
  const painel = document.getElementById('cv-arq-painel')
  if (!host || !painel) return
  const inicial = painel.innerHTML
  let fixo = null
  const mostra = (id) => {
    const p = PAINEIS[id]
    if (!p) return
    painel.innerHTML = `
      <span class="cv-rotulo">${p.rotulo}</span>
      <strong>${p.titulo}</strong>
      <p>${p.texto}</p>
      <ul>${p.numeros.map(n => `<li>${n}</li>`).join('')}</ul>
      <code class="cv-arq-cmd">${p.comando}</code>
      <p class="cv-arq-links">${p.links.map(([t, h]) => `<a href="${h}"${h.startsWith('http') ? ' target="_blank"' : ''}>${t}</a>`).join(' · ')}</p>`
  }
  host.querySelectorAll('.caixa').forEach(c => {
    const id = c.dataset.id
    c.addEventListener('mouseenter', () => { if (!fixo) mostra(id) })
    c.addEventListener('mouseleave', () => { if (!fixo) painel.innerHTML = inicial })
    c.addEventListener('click', () => {
      host.querySelectorAll('.caixa').forEach(o => o.classList.remove('ativa'))
      if (fixo === id) { fixo = null; painel.innerHTML = inicial; return }
      fixo = id; c.classList.add('ativa'); mostra(id)
    })
  })
})
</script>


# Entrega E2 · Ingestão em lote e captura de mudanças

Entregue na tag [`e2`](https://github.com/Luidooo/conselhos-vivos/releases/tag/e2) (commit `95a82b4`, 16/10/2026). Esta página tem três partes: **a arquitetura**, num diagrama interativo; **os entregáveis**, o que foi construído e onde está; e **o checklist de aceite** da disciplina, item a item, com o lugar exato onde conferir.

## Arquitetura

O dado sai da Imprensa Nacional e chega ao DuckDB por dois caminhos de natureza diferente, como a E2 pede: um **lote** mensal, idempotente, e um **fluxo de mudanças** que leva ao Delta o que a curadoria altera no OLTP. Clique numa caixa.

<div class="cv-arq">
  <div class="cv-arq-svg" id="cv-arq-svg">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 440" font-family="-apple-system, BlinkMacSystemFont, 'SF Pro Text', Inter, 'Helvetica Neue', Arial, sans-serif">
  <defs>
    <marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#8e8e93"/></marker>
    <marker id="seta-azul" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0071e3"/></marker>
    <filter id="sombra" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity="0.07"/></filter>
  </defs>
  <g class="caixa conteiner" data-id="oltp">
    <rect x="498" y="44" width="250" height="332"/>
    <text class="titulo" x="623" y="72" text-anchor="middle">Postgres 16 · OLTP</text>
  </g>
  <path class="fluxo" d="M178,128 H260"/>
  <path class="fluxo" d="M414,128 H516"/>
  <path class="fluxo" d="M750,168 H832"/>
  <path class="fluxo" d="M1006,128 H1054"/>
  <g>
    <text class="cmd" x="219" y="118" text-anchor="middle">fetch-mensal</text>
    <text class="cmd-sub" x="219" y="148" text-anchor="middle">ZIP do mês</text>
  </g>
  <g>
    <text class="cmd" x="465" y="118" text-anchor="middle">persist</text>
    <text class="cmd-sub" x="465" y="148" text-anchor="middle">só conselhos</text>
  </g>
  <g>
    <text class="cmd" x="791" y="158" text-anchor="middle">make lake</text>
    <text class="cmd-sub" x="791" y="188" text-anchor="middle">relê tudo</text>
  </g>
  <g>
    <text class="cmd" x="1030" y="118" text-anchor="middle">delta_scan</text>
    <text class="cmd-sub" x="1030" y="148" text-anchor="middle">lê o Delta</text>
  </g>
  <g class="caixa" data-id="fonte" filter="url(#sombra)">
    <rect x="16" y="92" width="160" height="116"/>
    <text class="titulo" x="96" y="124" text-anchor="middle">Dados abertos</text>
    <text class="sub" x="96" y="146" text-anchor="middle">Imprensa Nacional</text>
    <text class="sub" x="96" y="164" text-anchor="middle">1 ZIP/mês, sem login</text>
    <text class="num" x="96" y="194" text-anchor="middle">8.590 matérias · ago/26</text>
  </g>
  <g class="caixa" data-id="bronze" filter="url(#sombra)">
    <rect x="262" y="92" width="150" height="116"/>
    <text class="titulo" x="337" y="124" text-anchor="middle">Bronze</text>
    <text class="sub" x="337" y="146" text-anchor="middle">data/bronze/</text>
    <text class="sub" x="337" y="164" text-anchor="middle">ZIP como veio</text>
    <text class="num" x="337" y="194" text-anchor="middle">52,6 MB, byte a byte</text>
  </g>
  <g class="caixa destaque" data-id="delta" filter="url(#sombra)">
    <rect x="834" y="92" width="170" height="188"/>
    <text class="titulo" x="919" y="124" text-anchor="middle">Delta Lake</text>
    <text class="sub" x="919" y="146" text-anchor="middle">data/silver/atos/</text>
    <text class="sub" x="919" y="164" text-anchor="middle">Parquet · ano= · zstd</text>
    <text class="sub" x="919" y="182" text-anchor="middle">MERGE por ato_id</text>
    <text class="num" x="919" y="266" text-anchor="middle">311 linhas · −29% disco</text>
  </g>
  <g class="caixa" data-id="duckdb" filter="url(#sombra)">
    <rect x="1056" y="92" width="112" height="116"/>
    <text class="titulo" x="1112" y="124" text-anchor="middle">DuckDB</text>
    <text class="sub" x="1112" y="146" text-anchor="middle">consulta</text>
    <text class="sub" x="1112" y="164" text-anchor="middle">analítica</text>
    <text class="num" x="1112" y="194" text-anchor="middle">~0,85 ms</text>
  </g>
  <g class="caixa interna" data-id="oltp">
    <rect x="518" y="96" width="210" height="56"/>
    <text class="tab" x="623" y="120" text-anchor="middle">ato</text>
    <text class="num" x="623" y="140" text-anchor="middle">96 atos de conselho · versões</text>
  </g>
  <g class="caixa interna" data-id="curadoria">
    <rect x="518" y="168" width="210" height="56"/>
    <text class="tab" x="623" y="192" text-anchor="middle">classificacao</text>
    <text class="num" x="623" y="212" text-anchor="middle">insert-only · humano vence</text>
  </g>
  <g class="caixa interna slot" data-id="slot">
    <rect x="518" y="290" width="210" height="66"/>
    <text class="tab" x="623" y="314" text-anchor="middle">slot lógico</text>
    <text class="num" x="623" y="334" text-anchor="middle">test_decoding · 512 B por mudança</text>
  </g>
  <path class="fluxo cdc" d="M623,226 V288"/>
  <text class="cmd-sub cdc" x="633" y="262">WAL (wal_level=logical)</text>
  <g class="caixa" data-id="curadoria" filter="url(#sombra)">
    <rect x="262" y="250" width="150" height="96"/>
    <text class="titulo" x="337" y="282" text-anchor="middle">Curadoria</text>
    <text class="sub" x="337" y="304" text-anchor="middle">reclassifica um ato</text>
    <text class="num" x="337" y="332" text-anchor="middle">INSERT, nunca UPDATE</text>
  </g>
  <path class="fluxo cdc" d="M414,290 H465 V196 H516"/>
  <path class="fluxo cdc" d="M750,323 H919 V282"/>
  <g class="caixa rotulo" data-id="cdc"><rect class="alvo" x="774" y="291" width="130" height="58"/>
    <text class="cmd cdc" x="839" y="313" text-anchor="middle">make cdc</text>
    <text class="cmd-sub" x="839" y="343" text-anchor="middle">só o que mudou</text>
  </g>
  <path class="fluxo" d="M24,414 h36" marker-end="none"/><text class="legenda" x="68" y="418">lote: a fonte pública chega ao OLTP e ao Delta</text>
  <path class="fluxo cdc" d="M420,414 h36" marker-end="none"/><text class="legenda" x="464" y="418">mudanças: o que a curadoria altera chega ao Delta (CDC)</text>
  <text class="legenda" x="1164" y="418" text-anchor="end">clique numa caixa para os detalhes</text>
</svg>

  </div>
  <aside class="cv-arq-painel" id="cv-arq-painel">
    <span class="cv-rotulo">Arquitetura da E2</span>
    <strong>Dois caminhos, um destino</strong>
    <p>Em cima, o lote: um ZIP por mês entra no bronze como veio, o <code>persist</code> grava só as matérias de conselho no Postgres, e o <code>make lake</code> leva tudo a uma tabela Delta particionada por ano. Embaixo, as mudanças: cada reclassificação da curadoria é um <code>INSERT</code> que o slot lógico do Postgres captura e o <code>make cdc</code> aplica no Delta por <code>MERGE</code>.</p>
    <p class="cv-arq-dica">Passe o mouse ou clique numa caixa para ver o comando, os números medidos e onde conferir.</p>
  </aside>
</div>

<p class="cv-legenda">A mesma figura, estática, para imprimir ou colar numa apresentação: <a href="/conselhos-vivos/arquitetura-e2.svg" target="_blank">arquitetura-e2.svg</a>.</p>

## Entregáveis

| O que | Onde está | Como conferir |
|---|---|---|
| **Ingestão mensal da fonte pública**, idempotente | `make ingest-mensal MES=AAAA-MM` · `src/dou/` (Python) | 2ª execução: `gravadas=0 inalteradas=96`; banco idêntico linha a linha |
| **OLTP de curadoria** com versões e fila de órgãos | Postgres 16 · `sql/` · `ato`, `classificacao`, `orgao_alias` | `make test` (23 testes de banco em transação desfeita) |
| **Tabela Delta em formato aberto** (Parquet, `ano=`, zstd) | `make lake` · `data/silver/atos/` · `src/lake/` | 2ª execução: `inseridas=0`; DuckDB lê com `delta_scan` |
| **CDC por slot lógico**, sem Kafka | `make cdc` · `src/lake/cdc.py` · `wal_level=logical` | `make cdc-demo`: reclassifica, chega ao Delta, restaura |
| **Semântica de entrega demonstrada** | `make cdc-chaos` · `scripts/cdc_chaos_demo.sh` | queda forçada (código 42) → reexecução sem duplicar |
| **Dado atrasado e janela** | `make ingest` (janela de 7 dias) · `tests/lake/test_atrasado.sh` | ato de 2024 chegado hoje cai em `ano=2024` |
| **ADRs da E2** | [0005](/docs/adr/0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc) ingestão · [0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta) Delta/zstd · [0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica) CDC | medições em `docs/adr/medicoes/` |
| **Diários** das semanas 7 a 10 | `docs/diario/` | [Processo](/docs/diario/2026-10-13) |
| **Migração do ingestor Go → Python** (#51–#55) | `src/dou/`, provada byte a byte e linha a linha contra o Go | [plano](/docs/planos/2026-10-13-migracao-ingestor-go-para-python) · PRs #58, #60, #62, #63 |

## Checklist de aceite

Cada item do [checklist da E2](https://unb-bd2.github.io/PlanoEnsino/projeto/e2/), na ordem da página da disciplina, com o lugar exato onde conferir.

::: tip Conferir em máquina limpa
```bash
git clone https://github.com/Luidooo/conselhos-vivos.git && cd conselhos-vivos
make setup                        # cria o .env, sobe o Postgres, aplica as migrações e carrega a planilha
make test                         # inclui a idempotência da gravação e a janela de reprocessamento
make ingest-mensal MES=2026-08    # baixa agosto de 2026 dos dados abertos e grava as matérias de conselho
make ingest-mensal MES=2026-08    # de novo: 0 gravadas, nada muda no banco
make lake                         # OLTP → tabela Delta em data/silver/atos/; de novo: 0 inseridas
make cdc-demo                     # reclassifica um ato e mostra a mudança atravessando o slot até o Delta
make cdc-chaos                    # derruba o consumidor pós-gravação e reprocessa provando que nada duplica
```
Pré-requisitos: Docker com Compose v2 e `make`. A ingestão mensal não precisa de credencial. Detalhes em [Como rodar](/visao-geral#como-rodar).
:::

## 1. Ingestão em lote da fonte pública, idempotente e reexecutável

**Fonte:** o Diário Oficial da União em XML, pelos [dados abertos da Imprensa Nacional](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados): um ZIP por mês, público e sem login, com o histórico desde 2002. O INLABS, que publica o dia, continua disponível pelo `make ingest`, mas recusa login automático; por isso a fonte automática é a mensal ([#42](https://github.com/Luidooo/conselhos-vivos/issues/42)).

- **Um comando:** `make ingest-mensal MES=AAAA-MM` baixa a Seção 1 do mês para `data/bronze/dados-abertos/` e grava as matérias de conselho em `ato`. Mês já em disco não é baixado de novo. Conferir: [Ingerir um mês pelos dados abertos](/visao-geral#ingerir-um-mes-pelos-dados-abertos).
- **Idempotente:** cada matéria é comparada com todas as versões dela no banco; igual, nada é gravado; diferente, entra como versão nova, e as anteriores ficam. Conferir: [Gravar as matérias no banco](/visao-geral#gravar-as-materias-no-banco).
- **Medido com dado real**, num banco limpo, com agosto de 2026 (8.590 matérias, 52,6 MB):

  | Execução | gravadas | inalteradas | órgão desconhecido | falhou |
  |---|---|---|---|---|
  | 1ª | 96 | 0 | 8.494 | 0 |
  | 2ª | 0 | 96 | 8.494 | 0 |

  Depois da 2ª execução, `ato`, `orgao_alias` e `classificacao` saíram idênticos linha a linha. Conferir: [diário da semana 10](/docs/diario/2026-10-13) e [PR #43](https://github.com/Luidooo/conselhos-vivos/pull/43).
- **Testado:** `TestPersistTwiceLeavesTheDatabaseIdentical` grava a mesma edição duas vezes e compara o banco linha a linha, com `id` e `criado_em`; roda no `make test` e no CI.

## 2. Fluxo de mudanças a partir do OLTP (CDC)

- **Decodificação lógica do próprio Postgres**, sem Kafka nem Debezium: o banco sobe com `wal_level=logical`, um slot (`conselhos_lake`, plugin `test_decoding`) guarda as mudanças de `classificacao`, e `make cdc` as aplica na tabela Delta. O slot só diz *quais* atos mudaram; o consumidor relê esses atos do OLTP com a mesma consulta do `make lake` e grava por `MERGE` em `ato_id`. Conferir: [Fluxo de mudanças do OLTP ao Delta](/visao-geral#fluxo-de-mudancas-do-oltp-ao-delta-cdc) e [ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica).
- **O CDC viu uma mudança de verdade:** `make cdc-demo` reclassifica um ato (um `INSERT` novo, porque `classificacao` é insert-only), consome o slot, mostra a linha nova no Delta e depois restaura a tipologia original pelo mesmo caminho. Testado por [`tests/lake/test_cdc.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_cdc.sh), que roda no `make test`.
- **Cobertura declarada:** o fluxo cobre `INSERT` em `classificacao`; ato novo do DOU, versão nova e troca de nome de órgão continuam entrando pelo `make lake`.
- **Medido** (ADR 0007, script em `docs/adr/medicoes/0007-cdc/`): recarga completa dos 215 atos ~68 ms contra ~58 ms do incremental de um ato; o slot consumido retém 56 bytes de WAL, e uma reclassificação pendente, 512 bytes.

## 3. Camada de armazenamento analítico em formato aberto

- **Tabela Delta sobre Parquet** em `data/silver/atos/`, uma tabela consolidada (ato, órgão vigente na data, tipologia vigente), particionada por ano e gravada por `MERGE` em `ato_id` a partir do OLTP com a biblioteca `deltalake` (Rust/Python, sem JVM). Lida pelo DuckDB com `delta_scan`. Conferir: [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta).
- **Idempotente:** `make lake` duas vezes com os 311 atos (215 da planilha + 96 do DOU de agosto): 1ª `inseridas=311`, 2ª `inseridas=0 atualizadas=0 inalteradas=311`. Testado por [`tests/lake/test_lake.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_lake.sh), que compara a contagem do DuckDB com o `count(*)` do banco.
- **Delta × Iceberg** com critério explícito (catálogo, `MERGE` em Python puro, leitura no DuckDB) no ADR 0006.

## 4. Semântica de entrega declarada e demonstrada

- **Declarada:** pelo menos uma vez na leitura, efetivamente uma vez no destino. O consumidor espia o slot (`pg_logical_slot_peek_changes`), grava o Delta por `MERGE` atômico na chave primária (`ato_id`) e checksum de integridade, e só então consome até o último LSN (`pg_logical_slot_get_changes`). Se o processo cair antes de avançar o slot, o evento permanece no WAL e é entregue de novo na próxima execução (*at-least-once*); o `MERGE` idempotente detecta que a versão no Delta já coincide e absorve a repetição (`inalteradas=N`, `inseridas=0`, `atualizadas=0`), assegurando semântica *effectively-once*. Conferir: [ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica), decisão 3.
- **Demonstrada por teste automatizado:** [`tests/lake/test_cdc.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_cdc.sh) (integrado ao `make test` e CI) simula a interrupção forçada (`--falhar-apos-gravar`, exit code 42), confirma que o slot permaneceu sem avançar (`pendentes > 0`), reexecuta o consumidor normal e afere via DuckDB que a contagem total de registros no Delta Lake permaneceu estritamente inalterada e com 0 duplicações.
- **Demonstrada por comando interativo:** `make cdc-chaos` roda o roteiro reproduzível [`scripts/cdc_chaos_demo.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/scripts/cdc_chaos_demo.sh): reclassifica um ato no OLTP, derruba o consumidor intencionalmente após o MERGE no Delta, inspeciona o slot e o Delta Lake durante a falha, reexecuta o consumidor e valida via DuckDB que a contagem de atos (215) se mantém idêntica, sem linhas duplicadas.

## 5. Dado atrasado e reprocessamento de janela

- **Janela de dias:** `make ingest` busca e grava de novo os últimos `JANELA` dias (padrão 7, provisório), do mais antigo para o mais novo; `make janela` lista os dias sem baixar nada. Conferir: [Gravar as matérias no banco](/visao-geral#gravar-as-materias-no-banco), no parágrafo "Dado atrasado".
- **O ato atrasado fica na data em que foi publicado**, não na data em que chegou. Testado por `TestPersistTakesAMateriaThatArrivedLate`; a conta da janela, por [`tests/ingest/test_janela.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/ingest/test_janela.sh).
- **O que chega depois da janela** não entra sozinho; está escrito o que fazer.
- **Na fonte mensal não há janela:** o ZIP de um mês fechado já traz a edição extra (`DO1E`) de todos os dias, e uma retificação sai como matéria nova, na data em que foi publicada.

- **No Delta, demonstrado de ponta a ponta:** [`tests/lake/test_atrasado.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/lake/test_atrasado.sh) grava pelo `persist` um ato publicado em 15/03/2024 que chega hoje, roda o `make lake` e confere no DuckDB que ele entrou em `ano=2024` (`inseridas=1`), que nenhuma outra partição mudou e que a reexecução não duplica (`inseridas=0 atualizadas=0`). Roda no `make test`.

## 6. Serialização e compressão justificadas pelo padrão de acesso

- **Parquet particionado por ano**, não por dia: com os 215 atos da planilha, a partição diária dá 112 arquivos de poucos KB e a anual, 12; a agregação por conselho e tipologia no DuckDB cai de 16,7 ms para 4,9 ms. Partição por órgão foi descartada porque o indicador compara os 82 conselhos de uma vez.
- **`zstd`, medido contra `snappy`** com os dados reais: mesmo tempo de consulta (agregação e busca no texto) e 20% a 29% menos disco. A escolha não é o padrão da ferramenta: o `deltalake` grava `snappy` se nada for dito, e o código fixa `WriterProperties(compression="ZSTD")`. Script e resultados em [`docs/adr/medicoes/0006-camada-analitica/`](https://github.com/Luidooo/conselhos-vivos/tree/main/docs/adr/medicoes/0006-camada-analitica); justificativa no [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta).

## 7. ADR sobre o mecanismo de ingestão, com a opção nula considerada

- **Método de Decisão com 3 alternativas:** [ADR 0005](/docs/adr/0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc) compara formalmente a **Opção Nula** (A, recarga periódica completa agendada), o **CDC lógico nativo** (B, adotada) e **Debezium com Kafka** (C).
- **Medição reproduzível no repositório:** comando `docker compose run --rm lake python docs/adr/medicoes/0005-ingestao/bench.py` (não altera o banco) afere os tempos de extração e MERGE no Python para as opções A e B com os dados reais do domínio (base de referência com 311 atos: 215 históricos + 96 de agosto/2026), comparando-os com as estimativas arquiteturais da opção C (Debezium + Kafka).
  - *Containers e RAM permanente:* Opção B adiciona **0 containers e 0 MB de RAM permanente** (o slot é nativo no PostgreSQL), contra a estimativa de 4 containers e ~2 GB de RAM JVM permanente que uma stack Debezium + Kafka demandaria em regime ocioso.
  - *Tempo de processamento e parede:* em CPU no Python praticamente empatam (92,5 ms vs 65,4 ms; a extração pontual é mais rápida, 1,7 ms vs 25,8 ms, mas o MERGE no Delta Lake domina o tempo), e em tempo de parede no Compose efêmero ambos levam ~7 s de container. O CDC foi escolhido porque o checklist da E2 exige fluxo de mudanças com semântica demonstrada, porque custa zero container a mais, e porque escala em O(Δ) contra O(N) da opção nula (onde hoje N = 311 atos, acumulando ~1.150/ano com HTMLs de até 42 KB).
  - *Reprocessamento e tolerância a falhas:* entrega *effectively-once* comprovada sem duplicação no Delta Lake ([ADR 0007](/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica)).
- **Por que o DOU agora entra no OLTP:** o ADR 0001 previa o DOU apenas como bronze/OLAP. O ADR 0005 documenta a evolução e o que **não** mudou: o OLTP continua sendo a curadoria humana em 3NF (exigindo que `classificacao` aponte para uma chave estrangeira real em `ato(id)` com `origem = DOU|PLANILHA`), o espelho integral bruto segue no bronze (`data/bronze/`), a fila de resolução de aliases de órgãos ([ADR 0004](/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada)) é transacional viva, e o OLTP não espelha indiscriminadamente o DOU (em agosto/2026, 8.494 matérias alheias a conselho geraram **626 nomes novos** na fila `orgao_alias` e apenas as 96 matérias pertinentes foram gravadas em `ato`).
- **Dados Abertos vs INLABS:** a ingestão automática oficial adotou os Dados Abertos mensais públicos (sem login, com histórico desde 2002 e DO1E), contornando a recusa de login de script (502 Bad Gateway) imposta pelo INLABS em 12/10 (para publicações do dia corrente, a operação é baixar o ZIP pelo navegador na interface web e rodar `make persist`).
- **Delta × Iceberg e compressão zstd:** critérios explícitos consolidados no [ADR 0006](/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta).


## 8. Diário de bordo das semanas 7 a 10

| Semana | Diário |
|---|---|
| 7 | [25/09](/docs/diario/2026-09-25) e [26/09](/docs/diario/2026-09-26) |
| 8 | [29/09](/docs/diario/2026-09-29) |
| 9 | [06/10](/docs/diario/2026-10-06) |
| 10 | [13/10](/docs/diario/2026-10-13) |

## Processo da squad

- Registro de uso de IA, uma entrada por uso: [AI-USAGE](/AI-USAGE).
- Histórico e revisões entre pares: [pull requests](https://github.com/Luidooo/conselhos-vivos/pulls?q=is%3Apr).
- O que a E2 deixa para a E3: [Jornada do dado](/jornada-do-dado).
