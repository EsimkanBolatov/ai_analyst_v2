"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const links = [
  { href: "/ml-lab", label: "Данные" },
  { href: "/ml-lab/profile", label: "Data Profile" },
  { href: "/ml-lab/ai-report", label: "AI Report" },
  { href: "/ml-lab/train", label: "Train Model" },
  { href: "/ml-lab/prediction", label: "Prediction" },
  { href: "/ml-lab/fraud-check", label: "Fraud Check" },
];

export function LegacyShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell pt-8 sm:pt-10">
      <section className="panel overflow-hidden p-8 sm:p-10">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.4em] text-smoke">
          Streamlit logic migration
        </p>
        <div className="mt-4 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-ink sm:text-5xl">
              ML Lab: старые аналитические сценарии в новом интерфейсе.
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-smoke sm:text-base">
              Раздел повторяет ключевую логику Streamlit-страниц: загрузка датасетов,
              profiling, AI-отчет, обучение моделей, скоринг и ручная fraud-проверка.
              Старый Streamlit-контур остается в репозитории и может запускаться отдельно.
            </p>
          </div>
          <Link href="/dashboard" className="button-secondary">
            Вернуться в Dashboard
          </Link>
        </div>

        <nav className="mt-8 flex flex-wrap gap-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "rounded-full px-4 py-2 text-sm transition",
                pathname === link.href
                  ? "bg-ink text-paper"
                  : "border border-line bg-white/60 text-smoke hover:border-ink hover:text-ink",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </section>

      <div className="mt-8">{children}</div>
    </div>
  );
}
