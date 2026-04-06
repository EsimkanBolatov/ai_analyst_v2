"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export function LandingHero() {
  return (
    <section className="panel overflow-hidden px-6 py-8 sm:px-10 sm:py-12">
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
        className="grid gap-8 lg:grid-cols-[1.25fr_0.75fr] lg:items-end"
      >
        <div>
          <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.4em] text-smoke">
            Premium fraud defense
          </p>
          <h1 className="mt-5 max-w-4xl text-4xl font-semibold leading-tight text-ink sm:text-5xl lg:text-6xl">
            AI-Analyst Platform вышел в release-контур для контроля бюджета и борьбы с финансовым мошенничеством.
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-smoke sm:text-base">
            В продукт уже входят FastAPI backend, Next.js App Router, AI-бухгалтер, moderation workflow
            и Chromium extension для браузерной защиты.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/register" className="button-primary">
              Открыть новый контур
            </Link>
            <Link href="/login" className="button-secondary">
              Войти в систему
            </Link>
          </div>
        </div>

        <div className="grid gap-4">
          {[
            "JWT access + refresh",
            "Role-based endpoints",
            "AI accountant + moderation",
            "Browser guard + deploy ready",
          ].map((item) => (
            <div key={item} className="rounded-[24px] border border-line bg-white/70 px-5 py-4 text-sm text-ink">
              {item}
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}
