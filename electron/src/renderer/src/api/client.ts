import axios, { type AxiosInstance } from 'axios'

let cachedClient: Promise<AxiosInstance> | null = null

/** Lazily builds a single axios instance once the sidecar's runtime config (base URL + secret header) is available. Not yet consumed by any business endpoint — this is scaffolding for later FE tasks. */
export function getApiClient(): Promise<AxiosInstance> {
  cachedClient ??= createClient()
  return cachedClient
}

async function createClient(): Promise<AxiosInstance> {
  const config = await window.runtimeBridge.api.getConfig()
  if (!config) {
    throw new Error('runtime API config is not ready yet')
  }
  return axios.create({
    baseURL: config.baseUrl,
    headers: {
      [config.runtimeSecretHeader]: config.runtimeSecret
    }
  })
}
