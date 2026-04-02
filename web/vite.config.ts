import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Workaround: @vitejs/plugin-react@6 + vite@8 not injecting the refresh preamble
function reactRefreshPreamble(): Plugin {
  return {
    name: 'react-refresh-preamble',
    apply: 'serve',
    transformIndexHtml(html) {
      return html.replace(
        /(<script type="module" src="\/src\/main\.tsx[^"]*"><\/script>)/,
        `<script type="module">
import RefreshRuntime from '/@react-refresh'
RefreshRuntime.injectIntoGlobalHook(window)
window.$RefreshReg$ = () => {}
window.$RefreshSig$ = () => (type) => type
window.__vite_plugin_react_preamble_installed__ = true
</script>
$1`
      );
    },
  };
}

export default defineConfig({
  plugins: [reactRefreshPreamble(), react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
