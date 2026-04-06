"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { LogoutButton } from "@/components/logout-button";
import { ModerationBoard } from "@/components/moderation-board";
import { SessionGuard } from "@/components/session-guard";
import { ApiError, fetchCurrentUser, refreshSession } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { User } from "@/lib/types";

const allowedRoles = new Set(["Moderator", "Admin", "RiskManager"]);

export default function ModerationPage() {
  const router = useRouter();
  const { accessToken, refreshToken, user, setSession, setUser, clearSession } = useAuthStore();
  const [currentUser, setCurrentUser] = useState<User | null>(user);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
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
      } catch (loadError) {
        if (!(loadError instanceof ApiError) || loadError.status !== 401) {
          setError(loadError instanceof Error ? loadError.message : "Не удалось проверить пользователя.");
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
          setError(refreshError instanceof Error ? refreshError.message : "Сессия истекла.");
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

      if (!allowedRoles.has(nextUser.role.name)) {
        router.replace("/dashboard");
        setError("Недостаточно прав для доступа к moderation board.");
        setIsLoading(false);
        return;
      }

      setIsLoading(false);
    };

    void loadUser();
  }, [accessToken, clearSession, refreshToken, router, setSession, setUser, user]);

  return (
    <SessionGuard>
      <div className="shell pt-8 sm:pt-10">
        <section className="panel overflow-hidden p-8 sm:p-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.4em] text-smoke">
                Moderator Workspace
              </p>
              <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-tight text-ink sm:text-5xl">
                Release moderation board для двухэтапной проверки пользовательских жалоб.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-smoke sm:text-base">
                Здесь модератор получает вывод AI, принимает решение и переводит кейс в финальный
                blacklist или отклоняет его.
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
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-56 animate-pulse rounded-3xl border border-line bg-white/40" />
              ))}
            </div>
          ) : (
            <ModerationBoard
              session={{
                accessToken,
                refreshToken,
                onSession: (session) => {
                  setSession(session);
                  setUser(session.user);
                  setCurrentUser(session.user);
                },
              }}
              onAuthFailure={() => {
                clearSession();
                router.replace("/login");
              }}
            />
          )}
        </div>
      </div>
    </SessionGuard>
  );
}
