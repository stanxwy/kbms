/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** admin 后端 /api 入口；缺省 '/api'（走 vite 代理，生产/开发最佳实践）。 */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}