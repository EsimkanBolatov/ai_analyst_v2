"use client";

import { useRouter } from "next/navigation";

import { useAuthStore } from "@/lib/auth-store";

export function LogoutButton() {
  const router = useRouter();
  const clearSession = useAuthStore((state) => state.clearSession);

  return (
    <button
      type="button"
      className="button-secondary"
      onClick={() => {
        clearSession();
        router.push("/login");
      }}
    >
      Выйти
    </button>
  );
}
