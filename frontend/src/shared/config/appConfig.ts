type ApiMode = "mock" | "live";
type RequiredEnvName = "VITE_API_BASE_URL" | "VITE_SSE_BASE_URL" | "VITE_API_MODE";

function readRequiredEnv(name: RequiredEnvName) {
  const env = import.meta.env;
  let value: string;

  switch (name) {
    case "VITE_API_BASE_URL":
      value = env.VITE_API_BASE_URL;
      break;
    case "VITE_SSE_BASE_URL":
      value = env.VITE_SSE_BASE_URL;
      break;
    case "VITE_API_MODE":
      value = env.VITE_API_MODE;
      break;
  }

  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Missing required frontend environment variable: ${name}`);
  }

  return value;
}

function readApiMode() {
  const value = readRequiredEnv("VITE_API_MODE");

  if (value !== "mock" && value !== "live") {
    throw new Error("VITE_API_MODE must be either 'mock' or 'live'.");
  }

  return value;
}

function readUrlEnv(name: RequiredEnvName) {
  const value = readRequiredEnv(name);

  try {
    return new URL(value).toString().replace(/\/$/, "");
  } catch {
    throw new Error(`${name} must be a valid absolute URL.`);
  }
}

export const appConfig = {
  apiBaseUrl: readUrlEnv("VITE_API_BASE_URL"),
  sseBaseUrl: readUrlEnv("VITE_SSE_BASE_URL"),
  apiMode: readApiMode(),
} as const satisfies {
  apiBaseUrl: string;
  sseBaseUrl: string;
  apiMode: ApiMode;
};
