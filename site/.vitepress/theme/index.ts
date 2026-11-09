import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import ArquiteturaInterativa from './ArquiteturaInterativa.vue'
import LinhagemInterativa from './LinhagemInterativa.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('ArquiteturaInterativa', ArquiteturaInterativa)
    app.component('LinhagemInterativa', LinhagemInterativa)
  },
} satisfies Theme
