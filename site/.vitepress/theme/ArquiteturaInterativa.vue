<script setup lang="ts">
// A arquitetura final, interativa. Mesmo desenho de public/arquitetura-final.svg
// (gerado à parte, estático), com as mesmas coordenadas: mudou um, muda o outro.
import { computed, ref } from 'vue'
import { withBase } from 'vitepress'

type Cor = 'teal' | 'purple' | 'coral' | 'gray'
type Situacao = 'pronto' | 'E3' | 'E4' | 'produto'
interface Parte {
  id: string
  x: number; y: number; w: number; h: number
  cor?: Cor
  container?: boolean
  titulo: string
  sub?: string
  ferramenta?: string
  situacao: Situacao
  texto: string
  porque: string
  links?: [string, string][]
}

const PARTES: Parte[] = [
  // containers primeiro: ficam atrás das caixas
  { id: 'postgres', container: true, x: 20, y: 124, w: 390, h: 240, titulo: 'Postgres 16', ferramenta: 'papéis e GRANT', situacao: 'pronto',
    texto: 'O único banco que a pesquisadora toca, mesmo sem saber. Guarda os atos, a curadoria, a busca do RAG e os alertas. Na E4 ganha papéis por função: o app lê e escreve só o que precisa.',
    porque: 'PostgreSQL 16 desde a E1. A busca do RAG usa a busca textual que já vem nele, com os mesmos filtros por conselho e por data.',
    links: [['ADR 0002', '/docs/adr/0002-manter-postgresql-como-motor-do-oltp']] },
  { id: 'lakehouse', container: true, x: 430, y: 124, w: 350, h: 240, titulo: 'Lakehouse', ferramenta: 'em disco local', situacao: 'pronto',
    texto: 'A parte analítica: tabelas em formato aberto num diretório, lidas pelo DuckDB sem servidor. Fica fora do caminho das perguntas: se cair, o assistente continua respondendo.',
    porque: 'Disco local basta para este volume. Os caminhos são URIs, então trocar por object storage depois não muda o código.',
    links: [['ADR 0006', '/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta']] },
  { id: 'app', container: true, x: 20, y: 412, w: 760, h: 128, titulo: 'App da pesquisadora', ferramenta: 'Streamlit', situacao: 'E3',
    texto: 'A única coisa que a pesquisadora abre. Três abas, um endereço, nenhum comando.',
    porque: 'Streamlit é Python, a mesma linguagem do resto, e um app de três abas cabe num arquivo. O ponto a decidir no ADR: o briefing pede que o banco não fique exposto.' },

  { id: 'fonte', x: 34, y: 24, w: 202, h: 66, cor: 'gray', titulo: 'Dados abertos', sub: 'ZIP do mês, desde 2002', ferramenta: 'Python · src/dou', situacao: 'pronto',
    texto: 'A Imprensa Nacional publica um ZIP por mês e por seção, sem login. O ingestor baixa, guarda o ZIP como veio e grava no Postgres só os atos de conselho.',
    porque: 'O INLABS recusa login de script. Os dados abertos têm o mesmo XML e vão até 2002, o que alcança o período dos 215 atos da planilha. Falta conferir o formato dos meses antigos.',
    links: [['ADR 0005', '/docs/adr/0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc']] },
  { id: 'orquestrador', x: 434, y: 24, w: 332, h: 66, cor: 'gray', titulo: 'Orquestrador', sub: 'mensal, retry, backfill', ferramenta: 'Dagster  (opção nula: cron + make)', situacao: 'E3',
    texto: 'Dispara a ingestão do mês, a gold e o ETL reverso, nessa ordem. Tenta de novo quando a Imprensa Nacional falha e reprocessa um intervalo de meses sob demanda.',
    porque: 'Dagster tem partições mensais: o backfill dos meses de 2003 a 2020 vira uma seleção de intervalo. Com cron + make, retry e backfill são código nosso. Vira ADR na E3.' },
  { id: 'atos', x: 34, y: 160, w: 174, h: 86, cor: 'teal', titulo: 'Atos do DOU', sub: 'texto + link', ferramenta: 'tabela ato', situacao: 'pronto',
    texto: 'Cada ato de conselho com o texto publicado e o link. Republicação vira versão nova, nada é sobrescrito. Rodar o mesmo mês de novo deixa o banco idêntico.',
    porque: 'O texto integral é o que o RAG lê e o que a análise conta.',
    links: [['Gravar as matérias', '/visao-geral#gravar-as-materias-no-banco']] },
  { id: 'curadoria', x: 222, y: 160, w: 174, h: 86, cor: 'purple', titulo: 'Curadoria', sub: 'tipologia, órgãos', ferramenta: 'insert-only', situacao: 'pronto',
    texto: 'A classificação de cada ato na tipologia e a identidade dos conselhos. Reclassificar é inserir uma linha nova; a humana vence a do pipeline.',
    porque: 'Guardar o histórico das decisões é o que permite auditar a classificação e alimentar o CDC.',
    links: [['ADR 0001', '/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp'], ['ADR 0004', '/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada']] },
  { id: 'indice', x: 34, y: 262, w: 174, h: 86, cor: 'coral', titulo: 'Busca do RAG', sub: 'texto + filtros', ferramenta: 'tsvector · português', situacao: 'produto',
    texto: 'O texto de cada ato indexado pela busca textual do Postgres, em português: acha "licenciar" quando o ato diz "licenciamento". A busca combina as palavras da pergunta com filtros comuns de SQL, por conselho, data e tipologia.',
    porque: 'Já vem no Postgres: nenhuma extensão, nenhum modelo de embedding, nenhuma conta a mais. O limite é achar palavras, não sentido; o Claude pode reescrever a pergunta em termos de busca antes da consulta.' },
  { id: 'alertas', x: 222, y: 262, w: 174, h: 86, cor: 'purple', titulo: 'Alertas', sub: 'ETL reverso', ferramenta: 'script Python', situacao: 'E4',
    texto: 'As métricas da gold voltam ao Postgres como alertas: o conselho que parou de publicar, o que mudou de perfil de decisões. Quem age sobre eles é a pesquisadora, na aba Revisar.',
    porque: 'É o ETL reverso que a E4 pede: o dado analítico chega a um sistema operacional onde alguém decide.' },
  { id: 'silver', x: 444, y: 160, w: 322, h: 86, cor: 'teal', titulo: 'Silver, em Delta', sub: 'atos + curadoria', ferramenta: 'deltalake · CDC por slot lógico', situacao: 'pronto',
    texto: 'Uma tabela consolidada por ato, particionada por ano. As mudanças da curadoria chegam pelo slot de replicação lógica do Postgres, sem Kafka. Um ato atrasado cai no ano certo.',
    porque: 'Entregue na E2. Formato aberto, lido pelo DuckDB sem passar pelo motor que escreveu.',
    links: [['ADR 0006', '/docs/adr/0006-armazenar-a-camada-analitica-em-tabelas-delta'], ['ADR 0007', '/docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica']] },
  { id: 'gold', x: 444, y: 262, w: 322, h: 86, cor: 'teal', titulo: 'Gold', sub: 'fatos, SCD, métricas, testes', ferramenta: 'dbt-core + dbt-duckdb', situacao: 'E3',
    texto: 'O modelo dimensional: o fato do ato publicado, a dimensão do conselho com histórico de vinculação e as métricas de vitalidade, com testes de dados em cada camada.',
    porque: 'O dbt dá modelos em SQL versionados, testes e a documentação de linhagem de uma vez. Roda no DuckDB, sem servidor.' },
  { id: 'perguntar', x: 34, y: 444, w: 272, h: 84, cor: 'coral', titulo: 'Perguntar', sub: 'assistente, cita o ato', ferramenta: 'SDK anthropic', situacao: 'produto',
    texto: 'A pesquisadora pergunta em português. O app acha os atos na busca do Postgres, manda à API do Claude e mostra a resposta com o link de cada ato citado.',
    porque: 'Sem LangChain: é uma consulta SQL e uma chamada à API. Menos peças para a pesquisadora manter.' },
  { id: 'revisar', x: 318, y: 444, w: 218, h: 84, cor: 'purple', titulo: 'Revisar', sub: 'alertas, reclassificar', ferramenta: 'grava na curadoria', situacao: 'E4',
    texto: 'A lista de alertas. Ao reclassificar um ato, o app insere uma linha nova na curadoria, que o CDC leva à silver.',
    porque: 'Fecha o ciclo: a decisão dela volta para os dados sem ninguém editar planilha.' },
  { id: 'painel', x: 548, y: 444, w: 218, h: 84, cor: 'teal', titulo: 'Painel', sub: 'vitalidade', ferramenta: 'lê as métricas do dbt', situacao: 'E3',
    texto: 'O indicador de vitalidade por conselho: silêncio e tipologia ao longo do tempo.',
    porque: 'Lê as mesmas métricas que geram os alertas: uma definição só, a camada semântica da E4.' },
  { id: 'claude', x: 34, y: 584, w: 272, h: 62, cor: 'coral', titulo: 'API do Claude', sub: 'escreve a resposta', situacao: 'produto',
    texto: 'Recebe a pergunta e os atos achados e escreve a resposta citando os atos.',
    porque: 'Escolha da squad. O texto enviado é do DOU, público; a pergunta da pesquisadora entra na análise de LGPD da E4.' },
  { id: 'catalogo', x: 548, y: 584, w: 218, h: 62, cor: 'gray', titulo: 'Catálogo e linhagem', sub: 'dbt docs, no site', situacao: 'E4',
    texto: 'Cada tabela com descrição e o grafo de onde ela vem, da fonte até o painel e os alertas.',
    porque: 'Vem do próprio dbt: nenhuma ferramenta a mais para manter.' },
]

interface Seta { de: string; para: string; x1: number; y1: number; x2: number; y2: number; rotulo?: string; agenda?: boolean }
const SETAS: Seta[] = [
  { de: 'fonte', para: 'atos', x1: 135, y1: 90, x2: 135, y2: 158, rotulo: 'mensal' },
  { de: 'orquestrador', para: 'lakehouse', x1: 600, y1: 90, x2: 600, y2: 122, rotulo: 'dispara', agenda: true },
  { de: 'curadoria', para: 'silver', x1: 396, y1: 203, x2: 442, y2: 203, rotulo: 'CDC' },
  { de: 'silver', para: 'gold', x1: 605, y1: 246, x2: 605, y2: 260 },
  { de: 'gold', para: 'alertas', x1: 442, y1: 305, x2: 398, y2: 305 },
  { de: 'atos', para: 'indice', x1: 121, y1: 246, x2: 121, y2: 260 },
  { de: 'indice', para: 'perguntar', x1: 121, y1: 348, x2: 121, y2: 442 },
  { de: 'alertas', para: 'revisar', x1: 357, y1: 348, x2: 357, y2: 442 },
  { de: 'gold', para: 'painel', x1: 648, y1: 348, x2: 648, y2: 442 },
  { de: 'perguntar', para: 'claude', x1: 170, y1: 528, x2: 170, y2: 582 },
]

const PASSOS = [
  { titulo: '1. Entrada', texto: 'Uma vez por mês, o orquestrador dispara o ingestor: ele baixa o ZIP da Imprensa Nacional e grava cada ato de conselho no Postgres.', ids: ['orquestrador', 'fonte', 'atos'] },
  { titulo: '2. Curadoria', texto: 'A tipologia e a identidade dos conselhos ficam ao lado dos atos. Nada é sobrescrito: reclassificar é inserir.', ids: ['curadoria'] },
  { titulo: '3. Análise', texto: 'As mudanças vão por CDC para a silver em Delta. O dbt, no DuckDB, monta a gold: fatos, dimensões com histórico e métricas.', ids: ['silver', 'gold'] },
  { titulo: '4. Volta para quem decide', texto: 'As métricas viram alertas no Postgres e aparecem na aba Revisar; o painel lê as mesmas métricas.', ids: ['gold', 'alertas', 'revisar', 'painel'] },
  { titulo: '5. Perguntas', texto: 'O texto dos atos é indexado pela busca textual do próprio Postgres. A aba Perguntar acha os atos e pede a resposta à API do Claude, citando cada um.', ids: ['atos', 'indice', 'perguntar', 'claude'] },
]

const SITUACAO: Record<Situacao, string> = {
  pronto: 'Já existe', E3: 'Entra na E3', E4: 'Entra na E4', produto: 'Assistente (RAG)',
}

const selecionada = ref<string | null>(null)
const passo = ref<number | null>(null)
const sobre = ref<string | null>(null)

const porId = Object.fromEntries(PARTES.map((p) => [p.id, p]))
const parte = computed(() => (selecionada.value ? porId[selecionada.value] : null))
const destacadas = computed<Set<string>>(() => {
  if (passo.value !== null) return new Set(PASSOS[passo.value].ids)
  const id = selecionada.value ?? sobre.value
  if (!id) return new Set()
  const s = new Set([id])
  for (const e of SETAS) { if (e.de === id) s.add(e.para); if (e.para === id) s.add(e.de) }
  return s
})
const algoDestacado = computed(() => destacadas.value.size > 0)

function escolhe(id: string) {
  passo.value = null
  selecionada.value = selecionada.value === id ? null : id
}
function anda(delta: number) {
  selecionada.value = null
  const n = passo.value === null ? (delta > 0 ? 0 : PASSOS.length - 1) : passo.value + delta
  passo.value = n < 0 || n >= PASSOS.length ? null : n
}
function limpa() { passo.value = null; selecionada.value = null }

function linhas(p: Parte) {
  const l: { t: string; cls: string }[] = [{ t: p.titulo, cls: 'tit' }]
  if (p.sub) l.push({ t: p.sub, cls: 'sub' })
  if (p.ferramenta) l.push({ t: p.ferramenta, cls: 'fer' })
  const y0 = p.y + (p.h - l.length * 17) / 2 + 12
  return l.map((x, i) => ({ ...x, y: y0 + i * 17 }))
}
const setaAtiva = (e: Seta) => destacadas.value.has(e.de) && destacadas.value.has(e.para)
const link = (href: string) => (href.startsWith('http') ? href : withBase(href))
</script>

<template>
  <div class="cv-ai">
    <div class="cv-ai-barra">
      <button type="button" @click="anda(-1)" :disabled="passo === 0" aria-label="Passo anterior">‹</button>
      <button type="button" class="cv-ai-percorrer" @click="anda(1)">
        {{ passo === null ? 'Percorrer o caminho do dado' : passo === PASSOS.length - 1 ? 'Terminar' : 'Próximo passo' }}
      </button>
      <button type="button" @click="anda(1)" :disabled="passo === null" aria-label="Próximo passo">›</button>
      <span class="cv-ai-dica" v-if="passo === null && !selecionada">ou clique numa parte do desenho</span>
      <button type="button" class="cv-ai-limpar" v-else @click="limpa">Limpar</button>
    </div>

    <div class="cv-ai-svg">
      <svg viewBox="0 0 800 662" role="img" aria-label="Arquitetura final do Conselhos Vivos, interativa">
        <defs>
          <marker id="cv-ai-seta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
          </marker>
        </defs>
        <g v-for="p in PARTES" :key="p.id"
           :class="['parte', p.container ? 'container' : 'caixa', p.cor && 'cor-' + p.cor, {
             novo: p.situacao !== 'pronto', ativa: selecionada === p.id,
             apagada: algoDestacado && !destacadas.has(p.id) && !p.container,
             acesa: destacadas.has(p.id) }]"
           tabindex="0" role="button" :aria-label="p.titulo + (p.ferramenta ? ', ' + p.ferramenta : '')"
           :aria-pressed="selecionada === p.id"
           @click.stop="escolhe(p.id)" @keydown.enter.prevent="escolhe(p.id)" @keydown.space.prevent="escolhe(p.id)"
           @mouseenter="sobre = p.id" @mouseleave="sobre = null">
          <rect :x="p.x" :y="p.y" :width="p.w" :height="p.h" :rx="p.container ? 18 : 9" />
          <template v-if="p.container">
            <text class="ctit" :x="p.x + 16" :y="p.y + 22">{{ p.titulo }}</text>
            <text class="fer" :x="p.x + p.w - 16" :y="p.y + 22" text-anchor="end">{{ p.ferramenta }}</text>
          </template>
          <template v-else>
            <text v-for="l in linhas(p)" :key="l.cls" :class="l.cls" :x="p.x + p.w / 2" :y="l.y" text-anchor="middle">{{ l.t }}</text>
          </template>
        </g>
        <g v-for="(e, i) in SETAS" :key="i" :class="['seta', { agenda: e.agenda, acesa: setaAtiva(e), apagada: algoDestacado && !setaAtiva(e) }]">
          <line :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2" marker-end="url(#cv-ai-seta)" />
          <text v-if="e.rotulo" :x="e.x1 === e.x2 ? e.x1 + 6 : (e.x1 + e.x2) / 2" :y="e.x1 === e.x2 ? (e.y1 + e.y2) / 2 + 4 : e.y1 - 6"
                :text-anchor="e.x1 === e.x2 ? 'start' : 'middle'">{{ e.rotulo }}</text>
        </g>
      </svg>
    </div>

    <div class="cv-ai-painel" aria-live="polite">
      <template v-if="passo !== null">
        <span class="cv-ai-rotulo">Passo {{ passo + 1 }} de {{ PASSOS.length }}</span>
        <strong>{{ PASSOS[passo].titulo.replace(/^\d+\. /, '') }}</strong>
        <p>{{ PASSOS[passo].texto }}</p>
        <p class="cv-ai-pecas">
          <button v-for="id in PASSOS[passo].ids" :key="id" type="button" @click="escolhe(id)">{{ porId[id].titulo }}</button>
        </p>
      </template>
      <template v-else-if="parte">
        <span :class="['cv-ai-rotulo', 'sit-' + parte.situacao]">{{ SITUACAO[parte.situacao] }}</span>
        <strong>{{ parte.titulo }}</strong>
        <p>{{ parte.texto }}</p>
        <p v-if="parte.ferramenta"><span class="cv-ai-campo">Ferramenta</span> <code>{{ parte.ferramenta }}</code></p>
        <p><span class="cv-ai-campo">Por que</span> {{ parte.porque }}</p>
        <p v-if="parte.links" class="cv-ai-links">
          <a v-for="[t, h] in parte.links" :key="h" :href="link(h)">{{ t }}</a>
        </p>
      </template>
      <template v-else>
        <span class="cv-ai-rotulo">Como ler</span>
        <p>Contorno sólido: já existe. Tracejado: entra na E3 e na E4. Verde: dado do DOU. Roxo: o que a pesquisadora decide. Coral: o assistente. Passe o mouse para ver as ligações de cada parte.</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.cv-ai {
  --t-bg: #E1F5EE; --t-st: #0F6E56; --t-tx: #085041;
  --p-bg: #EEEDFE; --p-st: #534AB7; --p-tx: #3C3489;
  --c-bg: #FAECE7; --c-st: #993C1D; --c-tx: #712B13;
  --g-bg: #F1EFE8; --g-st: #5F5E5A; --g-tx: #2C2C2A;
  --ct-bg: #FAFAF7; --ct-st: #B4B2A9; --seta: #73726C; --rot: #5F5E5A;
  margin: 20px 0 8px;
}
.dark .cv-ai {
  --t-bg: #0B3B2E; --t-st: #4FC7A0; --t-tx: #C9F2E3;
  --p-bg: #26224F; --p-st: #9C95F0; --p-tx: #DEDBFF;
  --c-bg: #47200F; --c-st: #F0936B; --c-tx: #FBD9CA;
  --g-bg: #2C2C2A; --g-st: #A8A69E; --g-tx: #EDEBE4;
  --ct-bg: #1C1C1E; --ct-st: #48484A; --seta: #A1A1A6; --rot: #A1A1A6;
}

.cv-ai-barra { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.cv-ai-barra button {
  border: 1px solid var(--vp-c-brand-1); color: var(--vp-c-brand-1); background: transparent;
  border-radius: 980px; padding: 4px 14px; font-size: 14px; font-weight: 500; line-height: 1.6;
}
.cv-ai-barra button:hover:not(:disabled) { background: var(--vp-c-brand-soft); }
.cv-ai-barra button:disabled { opacity: .35; cursor: default; }
.cv-ai-barra .cv-ai-percorrer { background: var(--vp-c-brand-1); color: #fff; }
.cv-ai-barra .cv-ai-percorrer:hover { background: var(--vp-c-brand-2) !important; }
.cv-ai-dica { font-size: 13px; color: var(--vp-c-text-2); }
.cv-ai-barra .cv-ai-limpar { border-color: var(--vp-c-divider); color: var(--vp-c-text-2); }

.cv-ai-svg { overflow-x: auto; border-radius: 16px; }
.cv-ai-svg svg { display: block; width: 100%; min-width: 640px; height: auto; font-family: var(--vp-font-family-base); }

.parte { cursor: pointer; outline: none; transition: opacity .15s; }
.parte rect { stroke-width: 1.2; transition: stroke-width .15s; }
.parte.novo rect { stroke-dasharray: 5 3; }
.parte.container rect { fill: var(--ct-bg); stroke: var(--ct-st); stroke-width: 1; }
.parte.container.novo rect { stroke-dasharray: 6 4; }
.parte.caixa:hover rect, .parte.caixa:focus-visible rect, .parte.ativa rect, .parte.caixa.acesa rect { stroke-width: 2.6; }
.parte.container:hover rect, .parte.container:focus-visible rect, .parte.container.ativa rect { stroke: var(--vp-c-brand-1); stroke-width: 1.6; }
.parte.apagada { opacity: .3; }

.cor-teal rect { fill: var(--t-bg); stroke: var(--t-st); }
.cor-teal .tit, .cor-teal .sub { fill: var(--t-tx); } .cor-teal .fer { fill: var(--t-st); }
.cor-purple rect { fill: var(--p-bg); stroke: var(--p-st); }
.cor-purple .tit, .cor-purple .sub { fill: var(--p-tx); } .cor-purple .fer { fill: var(--p-st); }
.cor-coral rect { fill: var(--c-bg); stroke: var(--c-st); }
.cor-coral .tit, .cor-coral .sub { fill: var(--c-tx); } .cor-coral .fer { fill: var(--c-st); }
.cor-gray rect { fill: var(--g-bg); stroke: var(--g-st); }
.cor-gray .tit, .cor-gray .sub { fill: var(--g-tx); } .cor-gray .fer { fill: var(--g-st); }

text { pointer-events: none; }
.tit { font-size: 14px; font-weight: 600; }
.sub { font-size: 12px; }
.fer { font-size: 11.5px; font-weight: 500; font-family: var(--vp-font-family-mono); }
.container .ctit { font-size: 14px; font-weight: 700; fill: var(--vp-c-text-1); }
.container .fer { fill: var(--rot); }

.seta line { stroke: var(--seta); stroke-width: 1.5; transition: stroke .15s; }
.seta.agenda line { stroke-dasharray: 5 4; }
.seta text { font-size: 11px; font-style: italic; fill: var(--rot); }
.seta.acesa line { stroke: var(--vp-c-brand-1); stroke-width: 2.4; }
.seta.apagada { opacity: .3; }

.cv-ai-painel {
  margin-top: 12px; border-radius: 16px; padding: 16px 20px;
  background: var(--vp-c-bg-soft); min-height: 132px;
}
.cv-ai-painel strong { display: block; font-size: 18px; letter-spacing: -0.015em; margin: 2px 0 6px; }
.cv-ai-painel p { font-size: 14.5px !important; line-height: 1.55 !important; margin: 0 0 8px !important; }
.cv-ai-rotulo { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--vp-c-brand-1); }
.cv-ai-rotulo.sit-pronto { color: var(--t-st); }
.cv-ai-rotulo.sit-produto { color: var(--c-st); }
.cv-ai-campo { font-weight: 600; color: var(--vp-c-text-2); margin-right: 4px; }
.cv-ai-links a { margin-right: 14px; font-size: 14px; }
.cv-ai-pecas button {
  margin: 0 6px 6px 0; padding: 2px 10px; border-radius: 980px; font-size: 13px;
  border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg);
}
.cv-ai-pecas button:hover { border-color: var(--vp-c-brand-1); color: var(--vp-c-brand-1); }
</style>
