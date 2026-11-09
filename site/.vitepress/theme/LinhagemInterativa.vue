<script setup lang="ts">
// A linhagem dos dados, interativa, no mesmo desenho da ArquiteturaInterativa: do ZIP do DOU ao painel.
// As setas saem das caixas (borda direita para a esquerda, ou de cima para baixo na mesma coluna): mexeu numa
// caixa, a seta acompanha.
import { computed, ref } from 'vue'
import { withBase } from 'vitepress'

type Cor = 'teal' | 'purple' | 'coral' | 'gray'
interface No {
  id: string
  col: number; y: number
  cor: Cor
  titulo: string
  sub: string
  onde: string
  texto: string
  gera: string
  testes?: string
  links?: [string, string][]
}

const COLUNAS = ['Fontes', 'Bronze e OLTP', 'Silver · Delta', 'Gold · dbt', 'Consumo', 'Resposta']
const X0 = 20, PASSO_X = 250, W = 160, H = 70

const GH = 'https://github.com/Luidooo/conselhos-vivos/blob/main/'
const NOS: No[] = [
  { id: 'dou', col: 0, y: 60, cor: 'gray', titulo: 'DOU Seção 1', sub: 'dados abertos, um ZIP por mês', onde: 'in.gov.br',
    texto: 'O Diário Oficial da União, publicado pela Imprensa Nacional como um ZIP por mês, sem login, com o mesmo XML do INLABS. O mês sai cerca de duas semanas depois de acabar.',
    gera: 'make fetch-mensal MES=AAAA-MM, ou o asset atos_do_mes do Dagster',
    links: [['ADR 0005', '/docs/adr/0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc']] },
  { id: 'planilha', col: 0, y: 190, cor: 'purple', titulo: 'Planilha', sub: '215 atos, 2003 a 2020', onde: 'data/raw/',
    texto: 'Os atos que a pesquisadora classificou à mão, com a tipologia. É o rótulo da curadoria e o ground truth do projeto.',
    gera: 'make carga',
    links: [['ADR 0003', '/docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria']] },
  { id: 'siorg', col: 0, y: 320, cor: 'gray', titulo: 'SIORG', sub: 'cadastro de órgãos', onde: 'dados.gov.br',
    texto: 'O cadastro de órgãos do governo federal. Dá o código de 68 dos 82 órgãos e o nome vigente quando o nome casa com uma unidade só.',
    gera: 'make siorg (recorte versionado em data/referencia/)',
    links: [['ADR 0004', '/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada']] },

  { id: 'zip', col: 1, y: 60, cor: 'teal', titulo: 'Bronze', sub: 'o ZIP como veio', onde: 'data/bronze/dados-abertos/',
    texto: 'O arquivo só ganha o nome final depois de validado como ZIP. Um mês já em disco não é baixado de novo. É a fonte das duas leituras: os atos do próprio conselho e as menções de outros órgãos.',
    gera: 'python -m dou fetch-mensal' },
  { id: 'ato', col: 1, y: 170, cor: 'teal', titulo: 'ato', sub: 'texto + versões', onde: 'Postgres · OLTP',
    texto: 'Cada matéria publicada por um conselho, com o texto e a data. Republicação vira versão nova; nada é sobrescrito. Rodar o mesmo mês de novo deixa o banco idêntico.',
    gera: 'python -m dou persist ZIP', testes: 'tests/dou_db, no make test',
    links: [['ADR 0001', '/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp']] },
  { id: 'classificacao', col: 1, y: 270, cor: 'purple', titulo: 'classificacao', sub: 'tipologia, insert-only', onde: 'Postgres · OLTP',
    texto: 'A tipologia de cada ato. Reclassificar é inserir uma linha nova; a classificação humana vence a do pipeline. É o que o CDC acompanha.',
    gera: 'make carga, e a curadoria', links: [['ADR 0001', '/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp']] },
  { id: 'orgao_nome', col: 1, y: 370, cor: 'teal', titulo: 'orgao_nome', sub: 'nomes com vigência', onde: 'Postgres · OLTP',
    texto: 'Todos os nomes que cada órgão já teve, com início e fim de vigência. É a origem da variação lenta da dimensão.',
    gera: 'make carga', links: [['ADR 0004', '/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada']] },

  { id: 'silver_mencoes', col: 2, y: 60, cor: 'coral', titulo: 'silver/mencoes', sub: 'atos de outros órgãos', onde: 'data/silver/mencoes/',
    texto: 'As matérias publicadas por OUTRO órgão que têm o conselho como assunto: uma homologação, a composição, o regimento. O nome é procurado só no título, na ementa e no começo do texto.',
    gera: 'make mencoes, ou o asset silver/mencoes', testes: 'tests/mencoes: a extração e o MERGE idempotente',
    links: [['Plano', '/docs/planos/2026-11-09-mencoes-de-terceiros']] },
  { id: 'silver_atos', col: 2, y: 220, cor: 'teal', titulo: 'silver/atos', sub: 'um ato consolidado por linha', onde: 'data/silver/atos/',
    texto: 'Uma tabela por ato, particionada por ano e comprimida com zstd, com o nome do órgão na época e a classificação vigente. As reclassificações chegam pelo slot de replicação lógica do Postgres.',
    gera: 'make lake, e make cdc', testes: 'tests/lake: idempotência, dado atrasado, CDC',
    links: [['ADR 0006', '/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta'], ['ADR 0007', '/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica']] },

  { id: 'fct_mencao', col: 3, y: 60, cor: 'coral', titulo: 'fct_mencao', sub: 'matéria × conselho citado', onde: 'gold · dbt',
    texto: 'Fato. Uma linha por matéria de outro órgão × conselho citado, só dos conselhos no escopo do ADR 0010.',
    gera: 'make gold', testes: 'unique, not_null, relationships com a dim_conselho, accepted_values do assunto, um teste unitário' },
  { id: 'dim_conselho', col: 3, y: 170, cor: 'teal', titulo: 'dim_conselho', sub: 'SCD tipo 2', onde: 'gold · dbt',
    texto: 'Dimensão de variação lenta: uma linha por nome que o conselho teve, com a vigência. Renomear é inserir. O escopo é todo órgão com nome começando com "Conselho", menos as exclusões da seed.',
    gera: 'make gold', testes: 'vigências sem sobreposição, no máximo um nome atual, início aberto só no nome mais antigo',
    links: [['ADR 0010', '/docs/adr/0010-tratar-como-conselho-todo-orgao-com-conselho-no-nome']] },
  { id: 'fct_ato', col: 3, y: 280, cor: 'teal', titulo: 'fct_ato', sub: 'uma linha por matéria', onde: 'gold · dbt',
    texto: 'Fato. Cada matéria do próprio conselho, na versão mais recente, ligada ao nome que ele tinha na data (asof join).',
    gera: 'make gold', testes: 'unique, relationships, tipologias, volume igual ao staging, sem data no futuro, um teste unitário' },
  { id: 'fct_conselho_mes', col: 3, y: 390, cor: 'teal', titulo: 'fct_conselho_mes', sub: 'conselho × mês, com zeros', onde: 'gold · dbt',
    texto: 'Fato. Um conselho por mês coberto pelo DOU, com zero no mês sem ato: é o mês sem ato que responde à pergunta.',
    gera: 'make gold', testes: 'unique na dupla conselho × mês, relationships, nenhum mês coberto sem ato (distribuição)' },

  { id: 'mart', col: 4, y: 170, cor: 'teal', titulo: 'mart_vitalidade', sub: 'uma linha por conselho', onde: 'gold · dbt',
    texto: 'A resposta à pergunta da E1: ativo, em silêncio ou sem ato no período coberto, com as menções de outros órgãos ao lado, que não mudam a situação.',
    gera: 'make gold', testes: 'uma linha por conselho, accepted_values da situação, seis testes unitários da regra' },
  { id: 'freshness', col: 4, y: 330, cor: 'gray', titulo: 'freshness_vitalidade', sub: 'SLA: dia 20 do mês seguinte', onde: 'gold · dbt (view)',
    texto: 'O último mês coberto, o mês que o SLA espera hoje e o atraso. É uma view, para o "hoje" valer na leitura. O teste sla_vitalidade avisa sem travar o build.',
    gera: 'make gold', testes: 'sla_vitalidade (warn), três testes unitários da fronteira do dia 20' },

  { id: 'painel', col: 5, y: 250, cor: 'purple', titulo: 'Painel', sub: 'a pergunta da E1', onde: 'make painel · 127.0.0.1:8501',
    texto: 'Lê só a gold, em modo só leitura, e fecha a conexão a cada carga: o make gold passa com ele aberto. Mostra a situação, as menções, a marca da pesquisadora, os atos por mês e as tipologias.',
    gera: 'make painel', testes: 'tests/painel, no make test' },
]

const LIGACOES: [string, string, string?][] = [
  ['dou', 'zip', 'fetch-mensal'],
  ['zip', 'ato', 'persist'],
  ['zip', 'silver_mencoes', 'mencoes'],
  ['planilha', 'ato', 'carga'],
  ['planilha', 'classificacao'],
  ['siorg', 'orgao_nome'],
  ['ato', 'silver_atos', 'lake'],
  ['classificacao', 'silver_atos', 'CDC'],
  ['silver_mencoes', 'fct_mencao'],
  ['silver_atos', 'fct_ato'],
  ['orgao_nome', 'dim_conselho'],
  ['dim_conselho', 'fct_mencao'],
  ['dim_conselho', 'fct_ato'],
  ['fct_ato', 'fct_conselho_mes'],
  ['dim_conselho', 'mart'],
  ['fct_mencao', 'mart'],
  ['fct_conselho_mes', 'mart'],
  ['fct_conselho_mes', 'freshness'],
  ['mart', 'painel'],
  ['freshness', 'painel'],
  ['fct_ato', 'painel', 'tipologias'],
]

const PASSOS = [
  { titulo: '1. Entrada', texto: 'Uma vez por mês, o Dagster baixa o ZIP da Seção 1 do DOU e o guarda no bronze como veio.', ids: ['dou', 'zip'] },
  { titulo: '2. OLTP', texto: 'O persist grava no Postgres as matérias dos conselhos; a planilha e o SIORG trazem a tipologia e os nomes com vigência.', ids: ['zip', 'ato', 'planilha', 'classificacao', 'siorg', 'orgao_nome'] },
  { titulo: '3. Silver', texto: 'O lake consolida os atos em Delta, e o CDC leva as reclassificações. Do mesmo ZIP, as menções de outros órgãos vão para a sua própria tabela.', ids: ['ato', 'classificacao', 'silver_atos', 'zip', 'silver_mencoes'] },
  { titulo: '4. Gold', texto: 'O dbt monta a estrela: a dimensão com os nomes na época e os três fatos, cada um com seus testes.', ids: ['silver_atos', 'silver_mencoes', 'orgao_nome', 'dim_conselho', 'fct_ato', 'fct_conselho_mes', 'fct_mencao'] },
  { titulo: '5. Resposta', texto: 'A mart responde quais conselhos funcionam, o freshness vigia o SLA, e o painel mostra os dois.', ids: ['fct_conselho_mes', 'fct_mencao', 'dim_conselho', 'mart', 'freshness', 'painel'] },
]

const porId = Object.fromEntries(NOS.map((n) => [n.id, n]))
const x = (n: No) => X0 + n.col * PASSO_X
const Y = (n: No) => 50 + (n.y - 60) * 1.35 // afasta as linhas, para o rótulo da seta caber entre as caixas
const LARG = X0 * 2 + (COLUNAS.length - 1) * PASSO_X + W
const ALT = Math.max(...NOS.map(Y)) + H + 30

const SETAS = LIGACOES.map(([de, para, rotulo]) => {
  const a = porId[de], b = porId[para]
  if (b.col > a.col) return { de, para, rotulo, x1: x(a) + W, y1: Y(a) + H / 2, x2: x(b) - 2, y2: Y(b) + H / 2 }
  const desce = Y(b) > Y(a)
  return { de, para, rotulo, x1: x(a) + W / 2, y1: desce ? Y(a) + H : Y(a), x2: x(b) + W / 2, y2: desce ? Y(b) - 2 : Y(b) + H + 2 }
})

const selecionada = ref<string | null>(null)
const passo = ref<number | null>(null)
const sobre = ref<string | null>(null)
const no = computed(() => (selecionada.value ? porId[selecionada.value] : null))
const destacadas = computed<Set<string>>(() => {
  if (passo.value !== null) return new Set(PASSOS[passo.value].ids)
  const id = selecionada.value ?? sobre.value
  if (!id) return new Set()
  const s = new Set([id])
  for (const e of SETAS) { if (e.de === id) s.add(e.para); if (e.para === id) s.add(e.de) }
  return s
})
const algo = computed(() => destacadas.value.size > 0)
const acesa = (e: { de: string; para: string }) => destacadas.value.has(e.de) && destacadas.value.has(e.para)

function escolhe(id: string) { passo.value = null; selecionada.value = selecionada.value === id ? null : id }
function anda(d: number) {
  selecionada.value = null
  const n = passo.value === null ? (d > 0 ? 0 : PASSOS.length - 1) : passo.value + d
  passo.value = n < 0 || n >= PASSOS.length ? null : n
}
function limpa() { passo.value = null; selecionada.value = null }
const link = (h: string) => (h.startsWith('http') ? h : withBase(h))
</script>

<template>
  <div class="cv-li">
    <div class="cv-li-barra">
      <button type="button" @click="anda(-1)" :disabled="passo === 0" aria-label="Passo anterior">‹</button>
      <button type="button" class="cv-li-percorrer" @click="anda(1)">
        {{ passo === null ? 'Percorrer a linhagem' : passo === PASSOS.length - 1 ? 'Terminar' : 'Próximo passo' }}
      </button>
      <button type="button" @click="anda(1)" :disabled="passo === null" aria-label="Próximo passo">›</button>
      <span class="cv-li-dica" v-if="passo === null && !selecionada">ou clique numa tabela</span>
      <button type="button" class="cv-li-limpar" v-else @click="limpa">Limpar</button>
    </div>

    <div class="cv-li-svg">
      <svg :viewBox="`0 0 ${LARG} ${ALT}`" role="img" aria-label="Linhagem dos dados do Conselhos Vivos, interativa">
        <defs>
          <marker id="cv-li-seta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
          </marker>
        </defs>
        <text v-for="(c, i) in COLUNAS" :key="c" class="col" :x="X0 + i * PASSO_X + W / 2" y="30" text-anchor="middle">{{ c }}</text>
        <g v-for="(e, i) in SETAS" :key="'s' + i" :class="['seta', { acesa: acesa(e), apagada: algo && !acesa(e) }]">
          <line :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2" marker-end="url(#cv-li-seta)" />
          <text v-if="e.rotulo" :x="(e.x1 + e.x2) / 2" :y="(e.y1 + e.y2) / 2 - 5" text-anchor="middle">{{ e.rotulo }}</text>
        </g>
        <g v-for="n in NOS" :key="n.id"
           :class="['no', 'cor-' + n.cor, { ativa: selecionada === n.id, acesa: destacadas.has(n.id), apagada: algo && !destacadas.has(n.id) }]"
           tabindex="0" role="button" :aria-label="n.titulo + ', ' + n.sub" :aria-pressed="selecionada === n.id"
           @click.stop="escolhe(n.id)" @keydown.enter.prevent="escolhe(n.id)" @keydown.space.prevent="escolhe(n.id)"
           @mouseenter="sobre = n.id" @mouseleave="sobre = null">
          <rect :x="x(n)" :y="Y(n)" :width="W" :height="H" rx="9" />
          <text class="tit" :x="x(n) + W / 2" :y="Y(n) + 26" text-anchor="middle">{{ n.titulo }}</text>
          <text class="sub" :x="x(n) + W / 2" :y="Y(n) + 44" text-anchor="middle">{{ n.sub }}</text>
          <text class="fer" :x="x(n) + W / 2" :y="Y(n) + 60" text-anchor="middle">{{ n.onde }}</text>
        </g>
      </svg>
    </div>

    <div class="cv-li-painel" aria-live="polite">
      <template v-if="passo !== null">
        <span class="cv-li-rotulo">Passo {{ passo + 1 }} de {{ PASSOS.length }}</span>
        <strong>{{ PASSOS[passo].titulo.replace(/^\d+\. /, '') }}</strong>
        <p>{{ PASSOS[passo].texto }}</p>
        <p class="cv-li-pecas">
          <button v-for="id in PASSOS[passo].ids" :key="id" type="button" @click="escolhe(id)">{{ porId[id].titulo }}</button>
        </p>
      </template>
      <template v-else-if="no">
        <span class="cv-li-rotulo">{{ no.onde }}</span>
        <strong>{{ no.titulo }}</strong>
        <p>{{ no.texto }}</p>
        <p><span class="cv-li-campo">Gerado por</span> <code>{{ no.gera }}</code></p>
        <p v-if="no.testes"><span class="cv-li-campo">Testes</span> {{ no.testes }}</p>
        <p v-if="no.links" class="cv-li-links">
          <a v-for="[t, h] in no.links" :key="h" :href="link(h)">{{ t }}</a>
        </p>
      </template>
      <template v-else>
        <span class="cv-li-rotulo">Como ler</span>
        <p>Cada caixa é uma tabela ou uma fonte, e cada seta, de onde ela lê. Verde: o caminho do DOU. Roxo: o que vem da pesquisadora. Coral: as menções de outros órgãos, o enriquecimento da E3. Passe o mouse para ver as ligações, ou clique para ver como a tabela é gerada e testada.</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.cv-li {
  --t-bg: #E1F5EE; --t-st: #0F6E56; --t-tx: #085041;
  --p-bg: #EEEDFE; --p-st: #534AB7; --p-tx: #3C3489;
  --c-bg: #FAECE7; --c-st: #993C1D; --c-tx: #712B13;
  --g-bg: #F1EFE8; --g-st: #5F5E5A; --g-tx: #2C2C2A;
  --seta: #73726C; --rot: #5F5E5A;
  margin: 20px 0 8px;
}
.dark .cv-li {
  --t-bg: #0B3B2E; --t-st: #4FC7A0; --t-tx: #C9F2E3;
  --p-bg: #26224F; --p-st: #9C95F0; --p-tx: #DEDBFF;
  --c-bg: #47200F; --c-st: #F0936B; --c-tx: #FBD9CA;
  --g-bg: #2C2C2A; --g-st: #A8A69E; --g-tx: #EDEBE4;
  --seta: #A1A1A6; --rot: #A1A1A6;
}
.cv-li-barra { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.cv-li-barra button {
  border: 1px solid var(--vp-c-brand-1); color: var(--vp-c-brand-1); background: transparent;
  border-radius: 980px; padding: 4px 14px; font-size: 14px; font-weight: 500; line-height: 1.6;
}
.cv-li-barra button:hover:not(:disabled) { background: var(--vp-c-brand-soft); }
.cv-li-barra button:disabled { opacity: .35; cursor: default; }
.cv-li-barra .cv-li-percorrer { background: var(--vp-c-brand-1); color: #fff; }
.cv-li-barra .cv-li-percorrer:hover { background: var(--vp-c-brand-2) !important; }
.cv-li-dica { font-size: 13px; color: var(--vp-c-text-2); }
.cv-li-barra .cv-li-limpar { border-color: var(--vp-c-divider); color: var(--vp-c-text-2); }

.cv-li-svg { overflow-x: auto; border-radius: 16px; background: var(--vp-c-bg-soft); }
.cv-li-svg svg { display: block; width: 100%; min-width: 1150px; height: auto; font-family: var(--vp-font-family-base); }

.col { font-size: 13px; font-weight: 700; fill: var(--vp-c-text-2); text-transform: uppercase; letter-spacing: .04em; }
.no { cursor: pointer; outline: none; transition: opacity .15s; }
.no rect { stroke-width: 1.2; transition: stroke-width .15s; }
.no:hover rect, .no:focus-visible rect, .no.ativa rect, .no.acesa rect { stroke-width: 2.6; }
.no.apagada { opacity: .28; }
.cor-teal rect { fill: var(--t-bg); stroke: var(--t-st); } .cor-teal .tit, .cor-teal .sub { fill: var(--t-tx); } .cor-teal .fer { fill: var(--t-st); }
.cor-purple rect { fill: var(--p-bg); stroke: var(--p-st); } .cor-purple .tit, .cor-purple .sub { fill: var(--p-tx); } .cor-purple .fer { fill: var(--p-st); }
.cor-coral rect { fill: var(--c-bg); stroke: var(--c-st); } .cor-coral .tit, .cor-coral .sub { fill: var(--c-tx); } .cor-coral .fer { fill: var(--c-st); }
.cor-gray rect { fill: var(--g-bg); stroke: var(--g-st); } .cor-gray .tit, .cor-gray .sub { fill: var(--g-tx); } .cor-gray .fer { fill: var(--g-st); }

text { pointer-events: none; }
.tit { font-size: 14px; font-weight: 600; }
.sub { font-size: 11.5px; }
.fer { font-size: 10.5px; font-weight: 500; font-family: var(--vp-font-family-mono); }

.seta line { stroke: var(--seta); stroke-width: 1.4; transition: stroke .15s; }
.seta text { font-size: 12.5px; font-weight: 700; fill: var(--rot); paint-order: stroke; stroke: var(--vp-c-bg-soft); stroke-width: 5px; stroke-linejoin: round; }
.seta.acesa text { fill: var(--vp-c-brand-1); }
.seta.acesa line { stroke: var(--vp-c-brand-1); stroke-width: 2.4; }
.seta.apagada { opacity: .25; }

.cv-li-painel { margin-top: 12px; border-radius: 16px; padding: 16px 20px; background: var(--vp-c-bg-soft); min-height: 132px; }
.cv-li-painel strong { display: block; font-size: 18px; letter-spacing: -0.015em; margin: 2px 0 6px; }
.cv-li-painel p { font-size: 14.5px !important; line-height: 1.55 !important; margin: 0 0 8px !important; }
.cv-li-rotulo { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--vp-c-brand-1); }
.cv-li-campo { font-weight: 600; color: var(--vp-c-text-2); margin-right: 4px; }
.cv-li-links a { margin-right: 14px; font-size: 14px; }
.cv-li-pecas button { margin: 0 6px 6px 0; padding: 2px 10px; border-radius: 980px; font-size: 13px; border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg); }
.cv-li-pecas button:hover { border-color: var(--vp-c-brand-1); color: var(--vp-c-brand-1); }
</style>
