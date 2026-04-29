/**
 * Sonde l'endpoint /health du backend FastAPI.
 * Retourne le statut + une erreur éventuelle.
 */
export interface HealthResponse {
  status: "ok" | "degraded";
  db: "ok" | "unreachable";
}

export function useHealth() {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase as string;
  return useFetch<HealthResponse>(`${apiBase}/health`, {
    lazy: true,
    server: false,
    key: "health",
  });
}
