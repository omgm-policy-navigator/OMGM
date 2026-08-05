type ApiMode = "mock" | "live";

const apiMode = import.meta.env.VITE_API_MODE === "live" ? "live" : "mock";

export const appConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  sseBaseUrl: import.meta.env.VITE_SSE_BASE_URL ?? "http://localhost:8000",
  apiMode,
} as const satisfies {
  apiBaseUrl: string;
  sseBaseUrl: string;
  apiMode: ApiMode;
};
