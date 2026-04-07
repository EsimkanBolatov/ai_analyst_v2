import {
  API_BASE_URL,
  ApiError,
  refreshSession,
  type SessionRequestContext,
} from "@/lib/api";
import type {
  LegacyAiAnalysis,
  LegacyChatMessage,
  LegacyFraudCheckResponse,
  LegacyFraudDataType,
  LegacyModelConfig,
  LegacyModelListResponse,
  LegacyPredictionResponse,
  LegacyProfileResponse,
  LegacyScoreFileResponse,
  LegacyTrainPayload,
  LegacyUploadResponse,
} from "@/lib/legacy-types";

async function parseApiError(response: Response): Promise<ApiError> {
  const fallbackMessage = `Legacy API request failed with status ${response.status}`;
  try {
    const payload = (await response.json()) as { detail?: string };
    return new ApiError(payload.detail ?? fallbackMessage, response.status);
  } catch {
    return new ApiError(fallbackMessage, response.status);
  }
}

async function legacyRequest<T>(
  path: string,
  session: SessionRequestContext,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Authorization", `Bearer ${session.accessToken}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (response.status === 401) {
    const refreshed = await refreshSession(session.refreshToken);
    session.onSession(refreshed);
    const retryHeaders = new Headers(headers);
    retryHeaders.set("Authorization", `Bearer ${refreshed.access_token}`);
    const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: retryHeaders,
      cache: "no-store",
    });
    if (!retryResponse.ok) {
      throw await parseApiError(retryResponse);
    }
    return (await retryResponse.json()) as T;
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}

async function legacyTextRequest(
  path: string,
  session: SessionRequestContext,
): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  });

  if (response.status === 401) {
    const refreshed = await refreshSession(session.refreshToken);
    session.onSession(refreshed);
    const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Authorization: `Bearer ${refreshed.access_token}`,
      },
      cache: "no-store",
    });
    if (!retryResponse.ok) {
      throw await parseApiError(retryResponse);
    }
    return retryResponse.text();
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return response.text();
}

export function fetchLegacyFiles(session: SessionRequestContext): Promise<string[]> {
  return legacyRequest<string[]>("/legacy/files", session);
}

export function uploadLegacyFile(
  session: SessionRequestContext,
  file: File,
): Promise<LegacyUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return legacyRequest<LegacyUploadResponse>("/legacy/upload", session, {
    method: "POST",
    body: formData,
  });
}

export function fetchLegacyColumns(
  session: SessionRequestContext,
  filename: string,
): Promise<string[]> {
  return legacyRequest<string[]>(`/legacy/columns/${encodeURIComponent(filename)}`, session);
}

export function createLegacyProfile(
  session: SessionRequestContext,
  filename: string,
): Promise<LegacyProfileResponse> {
  return legacyRequest<LegacyProfileResponse>("/legacy/profile", session, {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
}

export function fetchLegacyProfileReport(
  session: SessionRequestContext,
  reportFilename: string,
): Promise<string> {
  return legacyTextRequest(
    `/legacy/profile-report/${encodeURIComponent(reportFilename)}`,
    session,
  );
}

export function analyzeLegacyFile(
  session: SessionRequestContext,
  filename: string,
): Promise<LegacyAiAnalysis> {
  return legacyRequest<LegacyAiAnalysis>("/legacy/ai/analyze", session, {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
}

export function sendLegacyAiChat(
  session: SessionRequestContext,
  payload: { filename: string; chat_history: LegacyChatMessage[] },
): Promise<LegacyChatMessage> {
  return legacyRequest<LegacyChatMessage>("/legacy/ai/chat", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchLegacyModels(
  session: SessionRequestContext,
): Promise<LegacyModelListResponse> {
  return legacyRequest<LegacyModelListResponse>("/legacy/models", session);
}

export function fetchLegacyModelConfig(
  session: SessionRequestContext,
  modelName: string,
): Promise<LegacyModelConfig> {
  return legacyRequest<LegacyModelConfig>(
    `/legacy/models/${encodeURIComponent(modelName)}/config`,
    session,
  );
}

export function trainLegacyAnomalyDetector(
  session: SessionRequestContext,
  payload: LegacyTrainPayload,
): Promise<{ message: string }> {
  return legacyRequest<{ message: string }>("/legacy/train-anomaly-detector", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function scoreLegacyFile(
  session: SessionRequestContext,
  payload: { model_name: string; filename: string },
): Promise<LegacyScoreFileResponse> {
  return legacyRequest<LegacyScoreFileResponse>("/legacy/score-file", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function predictLegacyRow(
  session: SessionRequestContext,
  payload: { model_name: string; features: Record<string, unknown> },
): Promise<LegacyPredictionResponse> {
  return legacyRequest<LegacyPredictionResponse>("/legacy/predict-or-score", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function checkLegacyFraud(
  session: SessionRequestContext,
  payload: { data_type: LegacyFraudDataType; value: string },
): Promise<LegacyFraudCheckResponse> {
  return legacyRequest<LegacyFraudCheckResponse>("/legacy/fraud-check", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function addLegacyBlacklist(
  session: SessionRequestContext,
  payload: { data_type: "phone" | "email" | "domain"; value: string },
): Promise<{ message: string }> {
  return legacyRequest<{ message: string }>("/legacy/fraud-blacklist", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
