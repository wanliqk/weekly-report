import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'

// electron-vite's default main/preload build externalizes every real
// `dependencies` entry (leaves it as a runtime `require(...)` instead of
// bundling it), betting that electron-builder's packaging step will locate
// and include it from `node_modules`. That bet doesn't reliably pay off in
// this npm-workspace layout: `@electron-toolkit/utils` lives hoisted at the
// *repo-root* `node_modules/`, not `electron/node_modules/`, and
// electron-builder's dependency walker intermittently failed to find and
// bundle it from there — confirmed live (PKG-02/REL-01) as
// `Error: Cannot find module '@electron-toolkit/utils'` thrown from the
// packaged `out/main/index.js` on some launches of the installed app, not
// others. Excluding it from externalization bundles it directly into
// `out/main/index.js` instead, so the packaged app never needs to resolve
// it from `node_modules` at runtime at all.
const BUNDLE_INTO_MAIN = ['@electron-toolkit/utils']

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin({ exclude: BUNDLE_INTO_MAIN })]
  },
  preload: {},
  renderer: {
    resolve: {
      alias: {
        '@renderer': resolve('src/renderer/src')
      }
    },
    plugins: [vue()]
  }
})
