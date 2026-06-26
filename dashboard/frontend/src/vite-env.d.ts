/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for the backend API. Defaults to the local backend in dev. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
