import { appConfig } from "../config/appConfig";

type RequestOptions = {
  signal?: AbortSignal;
};

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export async function getJson<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    method: "GET",
    credentials: "include",
    signal: options.signal,
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new ApiClientError(`Request failed with status ${response.status}`, response.status);
  }

  return response.json() as Promise<TResponse>;
}

export async function postJson<TResponse, TBody extends object | undefined = object>(
  path: string,
  body?: TBody,
  options: RequestOptions = {},
): Promise<TResponse> {
  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    method: "POST",
    credentials: "include",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body ?? {}),
  });

  if (!response.ok) {
    throw new ApiClientError(`Request failed with status ${response.status}`, response.status);
  }

  return response.json() as Promise<TResponse>;
}
