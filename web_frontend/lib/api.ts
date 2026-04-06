import type { AdminSummary, TokenPair, User } from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

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
