import type {
  AdminSummary,
  AssistantChatResponse,
  AssistantOverview,
  Budget,
  FraudDataType,
  FraudReportResponse,
  ModerationFilterStatus,
  ModerationQueueResponse,
  ModerationResolveResponse,
  TokenPair,
  TransactionImportResponse,
  User,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export type SessionRequestContext = {
  accessToken: string;
  refreshToken: string;
  onSession: (session: TokenPair) => void;
};

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const fallbackMessage = `API request failed with status ${response.status}`;
    let detail = fallbackMessage;

    try {
      const errorPayload = (await response.json()) as { detail?: string };
      detail = errorPayload.detail ?? fallbackMessage;
    } catch {
      detail = fallbackMessage;
    }

    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

async function apiRequestWithSession<T>(
  path: string,
  session: SessionRequestContext,
  options: RequestInit = {},
): Promise<T> {
  try {
    return await apiRequest<T>(path, options, session.accessToken);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) {
      throw error;
    }

    const refreshed = await refreshSession(session.refreshToken);
    session.onSession(refreshed);
    return apiRequest<T>(path, options, refreshed.access_token);
  }
}

export async function registerUser(payload: {
  email: string;
  password: string;
}): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginUser(payload: {
  email: string;
  password: string;
}): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function refreshSession(refreshToken: string): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<User> {
  return apiRequest<User>("/auth/me", {}, accessToken);
}

export async function fetchAdminSummary(accessToken: string): Promise<AdminSummary> {
  return apiRequest<AdminSummary>("/admin/summary", {}, accessToken);
}

export async function fetchAssistantOverview(
  session: SessionRequestContext,
): Promise<AssistantOverview> {
  return apiRequestWithSession<AssistantOverview>("/assistant/overview", session);
}

export async function saveBudget(
  session: SessionRequestContext,
  payload: { monthly_limit: number; month?: string },
): Promise<Budget> {
  return apiRequestWithSession<Budget>("/assistant/budget", session, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function sendAssistantMessage(
  session: SessionRequestContext,
  payload: { message: string },
): Promise<AssistantChatResponse> {
  return apiRequestWithSession<AssistantChatResponse>("/assistant/chat", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function importTransactions(
  session: SessionRequestContext,
  file: File,
): Promise<TransactionImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequestWithSession<TransactionImportResponse>("/assistant/import-transactions", session, {
    method: "POST",
    body: formData,
  });
}

export async function submitFraudReport(
  session: SessionRequestContext,
  payload: { data_type: FraudDataType; value: string; user_comment?: string },
): Promise<FraudReportResponse> {
  return apiRequestWithSession<FraudReportResponse>("/fraud/report", session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchMyFraudReports(
  session: SessionRequestContext,
): Promise<FraudReportResponse["item"][]> {
  return apiRequestWithSession<FraudReportResponse["item"][]>("/fraud/reports/mine", session);
}

export async function fetchModerationQueue(
  session: SessionRequestContext,
  params: { status?: ModerationFilterStatus; dataType?: string } = {},
): Promise<ModerationQueueResponse> {
  const searchParams = new URLSearchParams();
  if (params.status) {
    searchParams.set("status", params.status);
  }
  if (params.dataType) {
    searchParams.set("data_type", params.dataType);
  }
  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return apiRequestWithSession<ModerationQueueResponse>(`/fraud/moderation/queue${suffix}`, session);
}

export async function resolveModerationItem(
  session: SessionRequestContext,
  reportId: number,
  payload: { action: "approved" | "rejected"; moderator_comment?: string },
): Promise<ModerationResolveResponse> {
  return apiRequestWithSession<ModerationResolveResponse>(
    `/fraud/moderation/resolve/${reportId}`,
    session,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
