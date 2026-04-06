"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuthStore } from "@/lib/auth-store";

export function SessionGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { accessToken, hydrated } = useAuthStore();

  useEffect(() => {
    if (hydrated && !accessToken) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [accessToken, hydrated, pathname, router]);

  if (!hydrated || !accessToken) {
    return (
      <div className="shell pt-10">
        <div className="panel flex min-h-[320px] items-center justify-center p-8 text-sm text-smoke">
          Проверяем сессию...
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
