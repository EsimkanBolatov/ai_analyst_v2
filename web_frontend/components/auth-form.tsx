"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { motion } from "framer-motion";

import { ApiError, loginUser, registerUser } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

type AuthFormMode = "login" | "register";

const modeCopy: Record<
  AuthFormMode,
  {
    eyebrow: string;
    title: string;
    subtitle: string;
    submit: string;
    alternateHref: string;
    alternateLabel: string;
  }
> = {
  login: {
    eyebrow: "Secure Access",
    title: "Вход в AI-Analyst Platform",
    subtitle: "Используйте аккаунт для доступа к защищенному контуру и ролям.",
    submit: "Войти",
    alternateHref: "/register",
    alternateLabel: "Создать аккаунт",
  },
  register: {
    eyebrow: "New Account",
    title: "Создание клиентского аккаунта",
    subtitle: "Регистрация сразу выдает JWT-сессию и роль `User`.",
    submit: "Зарегистрироваться",
    alternateHref: "/login",
    alternateLabel: "У меня уже есть аккаунт",
  },
};

export function AuthForm({ mode }: { mode: AuthFormMode }) {
  const router = useRouter();
  const { setSession } = useAuthStore();
  const copy = modeCopy[mode];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const session =
        mode === "login"
          ? await loginUser({ email, password })
          : await registerUser({ email, password });
      setSession(session);
      router.push("/dashboard");
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.message);
      } else if (submitError instanceof Error) {
        setError(submitError.message);
      } else {
        setError("Произошла непредвиденная ошибка.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="panel w-full max-w-xl p-8 sm:p-10"
    >
      <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.4em] text-smoke">
        {copy.eyebrow}
      </p>
      <h1 className="mt-4 text-3xl font-semibold text-ink sm:text-4xl">{copy.title}</h1>
      <p className="mt-3 text-sm leading-7 text-smoke">{copy.subtitle}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-medium text-ink">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="input-field"
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </div>
        <div>
          <label htmlFor="password" className="mb-2 block text-sm font-medium text-ink">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="input-field"
            placeholder="Минимум 8 символов"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            required
          />
        </div>

        {error ? (
          <div className="rounded-2xl border border-black/10 bg-black px-4 py-3 text-sm text-paper">
            {error}
          </div>
        ) : null}

        <button type="submit" className="button-primary w-full" disabled={isSubmitting}>
          {isSubmitting ? "Обработка..." : copy.submit}
        </button>
      </form>

      <div className="mt-6 flex items-center justify-between gap-3 border-t border-line pt-5 text-sm text-smoke">
        <span>Нужен другой сценарий?</span>
        <Link href={copy.alternateHref} className="font-semibold text-ink">
          {copy.alternateLabel}
        </Link>
      </div>
    </motion.section>
  );
}
