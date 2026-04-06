"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

import { useAuthStore } from "@/lib/auth-store";

export function Header() {
  const pathname = usePathname();
  const { hydrated, user } = useAuthStore();
  const links = [
    { href: "/", label: "Главная" },
    { href: "/dashboard", label: "Dashboard" },
    ...(user && ["Moderator", "Admin", "RiskManager"].includes(user.role.name)
      ? [{ href: "/moderation", label: "Moderation" }]
      : []),
  ];

  return (
    <header className="shell pt-4">
      <div className="panel flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-[family-name:var(--font-mono)] text-sm uppercase tracking-[0.35em] text-ink">
            AI-Analyst
          </Link>
          <nav className="flex items-center gap-2">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  "rounded-full px-3 py-2 text-sm transition",
                  pathname === link.href
                    ? "bg-ink text-paper"
                    : "text-smoke hover:bg-black/5 hover:text-ink",
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3 text-sm">
          {hydrated && user ? (
            <>
              <span className="rounded-full border border-line px-3 py-2 text-smoke">{user.email}</span>
              <Link href="/dashboard" className="button-primary">
                Кабинет
              </Link>
            </>
          ) : (
            <>
              <Link href="/login" className="button-secondary">
                Войти
              </Link>
              <Link href="/register" className="button-primary">
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
