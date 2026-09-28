import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

// As páginas são os .md do próprio repositório (fonte única): o site só as organiza.
const REPO = 'https://github.com/Luidooo/conselhos-vivos'
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

/**
 * Link relativo para algo que não é página (.csv, .py, .sql, .json, pasta sem README)
 * vira link para o arquivo no GitHub. Link entre .md continua interno ao site.
 */
function linkParaGithub(href: string, arquivoFonte: string): string | null {
  if (/^([a-z]+:|#|\/)/i.test(href)) return null
  const [caminho, ancora = ''] = href.split('#')
  if (!caminho) return null
  const alvo = path.resolve(path.dirname(arquivoFonte), decodeURIComponent(caminho))
  const relativo = path.relative(RAIZ, alvo).split(path.sep).join('/')
  if (relativo.startsWith('..')) return null
  const ext = path.extname(alvo)
  if (ext === '.md') return null
  if (!ext) {
    const temPagina = ['README.md', 'index.md'].some((f) => existsSync(path.join(alvo, f)))
    if (temPagina) return null
    return `${REPO}/tree/main/${relativo}`
  }
  return `${REPO}/blob/main/${relativo}${ancora ? '#' + ancora : ''}`
}

export default withMermaid(defineConfig({
  lang: 'pt-BR',
  title: 'Conselhos Vivos',
  description: 'Plataforma de dados que mede a vitalidade dos conselhos nacionais de participação social.',
  base: '/conselhos-vivos/',
  cleanUrls: true,

  srcDir: '..',
  srcExclude: [
    '**/node_modules/**',
    'site/.vitepress/**',
    'sql/**', 'src/**', 'tests/**', 'data/**', 'scripts/**',
  ],
  rewrites: {
    'site/index.md': 'index.md',
    'site/entrega-e1.md': 'entrega-e1.md',
    'site/jornada-do-dado.md': 'jornada-do-dado.md',
    'README.md': 'visao-geral.md',
    'docs/adr/README.md': 'docs/adr/index.md',
  },
  // o README aponta para o pgAdmin local; não é link do site
  ignoreDeadLinks: 'localhostLinks',

  markdown: {
    config(md) {
      md.core.ruler.after('inline', 'link-para-github', (state) => {
        const fonte: string | undefined = state.env?.path
        if (!fonte) return
        for (const bloco of state.tokens) {
          for (const t of bloco.children ?? []) {
            if (t.type !== 'link_open') continue
            const href = t.attrGet('href')
            const novo = href && linkParaGithub(href, fonte)
            if (novo) {
              t.attrSet('href', novo)
              t.attrSet('target', '_blank')
              t.attrSet('rel', 'noreferrer')
            }
          }
        }
      })
    },
  },

  // Os .md ficam fora de site/: o Vite procuraria o vue a partir da raiz do repositório,
  // onde não há node_modules. Aponta para o de site/.
  vite: {
    // o plugin do Mermaid não declara estas dependências CommonJS; sem pré-processar,
    // o modo dev quebra com "does not provide an export named 'default'"
    optimizeDeps: { include: ['mermaid', 'fastdom'] },
    resolve: {
      alias: [{ find: /^vue(\/.*)?$/, replacement: path.join(RAIZ, 'site/node_modules/vue$1') }],
    },
  },

  head: [['meta', { name: 'theme-color', content: '#ffffff' }]],

  themeConfig: {
    siteTitle: 'Conselhos Vivos',
    nav: [
      { text: 'Entrega E1', link: '/entrega-e1' },
      { text: 'Jornada do dado', link: '/jornada-do-dado' },
      { text: 'Visão geral', link: '/visao-geral' },
      { text: 'Decisões', link: '/docs/adr/' },
      { text: 'Dados', link: '/docs/carga/relatorio-planilha' },
      { text: 'Processo', link: '/docs/diario/2026-09-26' },
    ],
    sidebar: [
      {
        text: 'Comece aqui',
        items: [
          { text: 'Entrega E1', link: '/entrega-e1' },
          { text: 'Jornada do dado', link: '/jornada-do-dado' },
          { text: 'Visão geral e como rodar', link: '/visao-geral' },
        ],
      },
      {
        text: 'Decisões (ADRs)',
        items: [
          { text: 'Índice', link: '/docs/adr/' },
          { text: '0001 · OLTP de curadoria, insert-only', link: '/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp' },
          { text: '0002 · PostgreSQL 16', link: '/docs/adr/0002-manter-postgresql-como-motor-do-oltp' },
          { text: '0003 · Planilha como rótulo', link: '/docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria' },
          { text: '0004 · Identidade dos conselhos', link: '/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada' },
        ],
      },
      {
        text: 'Dados e qualidade',
        items: [
          { text: 'Carga da planilha', link: '/docs/carga/relatorio-planilha' },
          { text: 'Identidade dos conselhos', link: '/docs/carga/relatorio-conselhos' },
        ],
      },
      {
        text: 'Processo',
        items: [
          { text: 'Diário · 25/09', link: '/docs/diario/2026-09-25' },
          { text: 'Diário · 26/09', link: '/docs/diario/2026-09-26' },
          { text: 'Uso de IA', link: '/AI-USAGE' },
        ],
      },
    ],
    socialLinks: [{ icon: 'github', link: REPO }],
    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: 'Buscar', buttonAriaLabel: 'Buscar' },
          modal: {
            noResultsText: 'Nada encontrado para',
            resetButtonTitle: 'Limpar',
            footer: { selectText: 'abrir', navigateText: 'navegar', closeText: 'fechar' },
          },
        },
      },
    },
    outline: { level: [2, 3], label: 'Nesta página' },
    docFooter: { prev: 'Anterior', next: 'Próxima' },
    darkModeSwitchLabel: 'Aparência',
    lightModeSwitchTitle: 'Tema claro',
    darkModeSwitchTitle: 'Tema escuro',
    sidebarMenuLabel: 'Menu',
    returnToTopLabel: 'Voltar ao topo',
    footer: {
      message: 'Projeto Integrado de Banco de Dados 2 — FCTE/UnB, 2026/2.',
      copyright: 'Dados da pesquisa: SERAFIM, Lizandra e colaboradores (UFPB/Cebrap).',
    },
  },

  // diagramas Mermaid no tom do site (o plugin troca para o tema escuro sozinho)
  mermaid: {
    theme: 'base',
    themeVariables: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", Helvetica, Arial, sans-serif',
      fontSize: '17px',
    },
    flowchart: { nodeSpacing: 36, rankSpacing: 46, padding: 14, wrappingWidth: 320 },
  },
}))
