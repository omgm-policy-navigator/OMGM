import type { HealthResponse } from "../../entities/health/model";
import { appConfig } from "../config/appConfig";
import { getJson } from "./client";

const mockHealthResponse: HealthResponse = {
  status: "ok",
  service: "omgm-frontend-mock-api",
  environment: "mock",
};

type FetchHealthOptions = {
  signal?: AbortSignal;
};

export async function fetchHealth(options: FetchHealthOptions = {}): Promise<HealthResponse> {
  if (appConfig.apiMode === "mock") {
    return mockHealthResponse;
  }

  return getJson<HealthResponse>("/health", options);
}
