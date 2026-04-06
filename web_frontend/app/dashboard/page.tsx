"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AssistantWorkspace } from "@/components/assistant-workspace";
import { FraudReportCenter } from "@/components/fraud-report-center";
import { LogoutButton } from "@/components/logout-button";
import { SessionGuard } from "@/components/session-guard";
import {
  ApiError,
  fetchAdminSummary,
  fetchCurrentUser,
  refreshSession,
} from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { AdminSummary, User } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const { accessToken, refreshToken, user, setSession, setUser, clearSession } = useAuthStore();
  const [currentUser, setCurrentUser] = useState<User | null>(user);
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboard = async () => {
      if (!accessToken || !refreshToken) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      let currentAccessToken = accessToken;
      let nextUser = user;

      try {
        nextUser = await fetchCurrentUser(currentAccessToken);
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 401) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить профиль.");
          setIsLoading(false);
          return;
        }

        try {
          const refreshed = await refreshSession(refreshToken);
          setSession(refreshed);
          currentAccessToken = refreshed.access_token;
          nextUser = refreshed.user;
        } catch (refreshError) {
          clearSession();
          router.replace("/login");
          setError(
            refreshError instanceof Error
              ? refreshError.message
              : "Сессия истекла. Войдите повторно.",
          );
          setIsLoading(false);
          return;
        }
      }

      if (!nextUser) {
        setError("Пользователь не найден.");
        setIsLoading(false);
        return;
      }

      setUser(nextUser);
      setCurrentUser(nextUser);

      if (["Admin", "Moderator", "RiskManager"].includes(nextUser.role.name)) {
        try {
          setSummary(await fetchAdminSummary(currentAccessToken));
        } catch (summaryError) {
          setError(
            summaryError instanceof Error
              ? summaryError.message
              : "Не удалось загрузить admin summary.",
          );
        }
      } else {
        setSummary(null);
      }

      setIsLoading(false);
    };

    void loadDashboard();
  }, [accessToken, clearSession, refreshToken, router, setSession, setUser, user]);

  return (
    <SessionGuard>
      <div className="shell pt-8 sm:pt-10">
        <section className="panel overflow-hidden p-8 sm:p-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.4em] text-smoke">
                Protected Workspace
              </p>
              <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight text-ink sm:text-5xl">
                Release contour: бюджет, AI-бухгалтер, fraud reports и moderator-ready workflow.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-smoke sm:text-base">
                Кабинет работает поверх JWT и ролей, управляет бюджетом, импортирует выписки,
                принимает fraud reports и связывается с moderator pipeline без legacy-зависимости от Streamlit.
              </p>
            </div>
            <LogoutButton />
          </div>
        </section>

        {error ? (
          <div className="mt-6 rounded-3xl border border-black/10 bg-black px-6 py-4 text-sm text-paper">
            {error}
          </div>
        ) : null}

        <div className="mt-8">
          {isLoading || !currentUser || !accessToken || !refreshToken ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="h-40 animate-pulse rounded-3xl border border-line bg-white/40" />
                ))}
              </div>
              <div className="h-64 animate-pulse rounded-3xl border border-line bg-white/40" />
            </div>
          ) : (
            <div className="space-y-8">
              <AssistantWorkspace
                user={currentUser}
                adminSummary={summary}
                accessToken={accessToken}
                refreshToken={refreshToken}
                onSession={(session) => {
                  setSession(session);
                  setUser(session.user);
                  setCurrentUser(session.user);
                }}
                onAuthFailure={() => {
                  clearSession();
                  router.replace("/login");
                }}
              />
              <FraudReportCenter
                user={currentUser}
                accessToken={accessToken}
                refreshToken={refreshToken}
                onSession={(session) => {
                  setSession(session);
                  setUser(session.user);
                  setCurrentUser(session.user);
                }}
                onAuthFailure={() => {
                  clearSession();
                  router.replace("/login");
                }}
              />
            </div>
          )}
        </div>
      </div>
    </SessionGuard>
  );
}
