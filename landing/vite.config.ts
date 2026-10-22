import { defineConfig, loadEnv } from 'vite'
import { resolveSiteUrl, BASE_PATH } from './site.config.ts'
import { prerender } from './build/vite-plugin-prerender.ts'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const siteUrl = resolveSiteUrl(loadEnv(mode, process.cwd(), 'VITE_'))
  return {
    base: BASE_PATH,
    plugins: [prerender({ siteUrl })],
  }
})
