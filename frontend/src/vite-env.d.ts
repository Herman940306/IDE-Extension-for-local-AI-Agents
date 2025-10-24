/// <reference types="vite/client" />

declare interface ImportMetaEnv {
  readonly VITE_BACKEND_WS_URL?: string;
  readonly VITE_BACKEND_WS_URLS?: string;
}

declare interface ImportMeta {
  readonly env: ImportMetaEnv;
}
