"use client";

import { useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";

import type { SessionRequestContext } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { TokenPair } from "@/lib/types";

export function useSessionContext(): {
  session: SessionRequestContext | null;
  onAuthFailure: () => void;
} {
  const router = useRouter();
  const { accessToken, refreshToken, setSession, clearSession } = useAuthStore();

  const handleSession = useCallback(
    (session: TokenPair) => {
      setSession(session);
    },
    [setSession],
  );

  const onAuthFailure = useCallback(() => {
    clearSession();
    router.replace("/login");
  }, [clearSession, router]);

  const session = useMemo<SessionRequestContext | null>(() => {
    if (!accessToken || !refreshToken) {
      return null;
    }
    return {
      accessToken,
      refreshToken,
      onSession: handleSession,
    };
  }, [accessToken, handleSession, refreshToken]);

  return { session, onAuthFailure };
}
