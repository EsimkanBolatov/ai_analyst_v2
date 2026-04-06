"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { LogoutButton } from "@/components/logout-button";
import { SessionGuard } from "@/components/session-guard";
import {
  ApiError,
  fetchAdminSummary,
  fetchCurrentUser,
  refreshSession,
} from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { AdminSummary } from "@/lib/types";

const roleLabels: Record<string, string> = {
  User: "Клиент",
  Moderator: "Модератор",
  RiskManager: "Риск-менеджер",
  Admin: "Администратор",
};

export default function DashboardPage() {
  const router = useRouter();
  const { accessToken, refreshToken, user, setSession, setUser, clearSession } = useAuthStore();
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
      let currentUser = user;

      try {
        currentUser = await fetchCurrentUser(currentAccessToken);
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
          currentUser = refreshed.user;
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

      if (!currentUser) {
        setError("Пользователь не найден.");
        setIsLoading(false);
        return;
      }

      setUser(currentUser);

      if (["Admin", "Moderator", "RiskManager"].includes(currentUser.role.name)) {
        try {
          const adminSummary = await fetchAdminSummary(currentAccessToken);
          setSummary(adminSummary);
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

  const capabilityCards = useMemo(
    () => [
      {
        title: "Auth Service",
        text: "Регистрация, логин, refresh-token и ролевая защита уже заведены в backend_v3.",
      },
      {
        title: "Assistant Service",
        text: "Следующий этап: привязка бюджетов, истории трат и строгого ИИ-финансиста.",
      },
      {
        title: "Fraud Moderation",
        text: "Модерация и очередь репортов уже подготовлены на уровне модели данных.",
      },
    ],
    [],
  );

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
                Кабинет пользователя и административный контур под новый стек.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-smoke sm:text-base">
                Эта зона уже работает поверх JWT-авторизации и ролей. Следующие спринты будут
                насаживаться на этот фундамент без возврата к Streamlit как основному клиенту.
              </p>
            </div>
            <LogoutButton />
          </div>

          {isLoading ? (
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-32 animate-pulse rounded-3xl border border-line bg-white/40" />
              ))}
            </div>
          ) : (
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              <div className="rounded-[24px] border border-line bg-white/70 p-5">
                <p className="text-xs uppercase tracking-[0.3em] text-smoke">Профиль</p>
                <p className="mt-4 text-2xl font-semibold text-ink">{user?.email ?? "Unknown user"}</p>
                <p className="mt-2 text-sm text-smoke">
                  Роль: {user ? roleLabels[user.role.name] ?? user.role.name : "Не определена"}
                </p>
              </div>
              <div className="rounded-[24px] border border-line bg-white/70 p-5">
                <p className="text-xs uppercase tracking-[0.3em] text-smoke">Состояние</p>
                <p className="mt-4 text-2xl font-semibold text-ink">Auth ready</p>
                <p className="mt-2 text-sm text-smoke">
                  Access и refresh токены, защита ролями и `me` endpoint уже активны.
                </p>
              </div>
              <div className="rounded-[24px] border border-line bg-white/70 p-5">
                <p className="text-xs uppercase tracking-[0.3em] text-smoke">Следующий спринт</p>
                <p className="mt-4 text-2xl font-semibold text-ink">Assistant Core</p>
                <p className="mt-2 text-sm text-smoke">
                  Бюджеты, транзакции, чат и голосовой интерфейс будут строиться поверх этой модели.
                </p>
              </div>
            </div>
          )}
        </section>

        {error ? (
          <div className="mt-6 rounded-3xl border border-black/10 bg-black px-6 py-4 text-sm text-paper">
            {error}
          </div>
        ) : null}

        <section className="mt-8 grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="panel p-6">
            <p className="text-xs uppercase tracking-[0.3em] text-smoke">Roadmap</p>
            <div className="mt-5 grid gap-4">
              {capabilityCards.map((card) => (
                <article key={card.title} className="rounded-[24px] border border-line bg-white/70 p-5">
                  <h2 className="text-xl font-semibold text-ink">{card.title}</h2>
                  <p className="mt-3 text-sm leading-7 text-smoke">{card.text}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="panel p-6">
            <p className="text-xs uppercase tracking-[0.3em] text-smoke">Protected Metrics</p>
            {summary ? (
              <div className="mt-5 grid gap-4">
                <div className="rounded-[24px] border border-line bg-white/70 p-5">
                  <p className="text-sm text-smoke">Users</p>
                  <p className="mt-2 text-4xl font-semibold text-ink">{summary.users}</p>
                </div>
                <div className="rounded-[24px] border border-line bg-white/70 p-5">
                  <p className="text-sm text-smoke">Transactions</p>
                  <p className="mt-2 text-4xl font-semibold text-ink">{summary.transactions}</p>
                </div>
                <div className="rounded-[24px] border border-line bg-white/70 p-5">
                  <p className="text-sm text-smoke">Moderation Queue</p>
                  <p className="mt-2 text-4xl font-semibold text-ink">{summary.moderation_items}</p>
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-[24px] border border-dashed border-line bg-white/50 p-5 text-sm leading-7 text-smoke">
                Для роли `User` административная статистика скрыта. После входа под `Moderator`,
                `RiskManager` или `Admin` здесь будет показан защищенный summary endpoint.
              </div>
            )}
          </div>
        </section>
      </div>
    </SessionGuard>
  );
}
