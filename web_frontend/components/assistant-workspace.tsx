"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import {
  ApiError,
  fetchAssistantOverview,
  importTransactions,
  saveBudget,
  sendAssistantMessage,
} from "@/lib/api";
import type {
  AdminSummary,
  AssistantMessage,
  AssistantOverview,
  TokenPair,
  Transaction,
  User,
} from "@/lib/types";

type AssistantWorkspaceProps = {
  user: User;
  adminSummary: AdminSummary | null;
  accessToken: string;
  refreshToken: string;
  onSession: (session: TokenPair) => void;
  onAuthFailure: () => void;
};

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const roleLabels: Record<string, string> = {
  User: "Клиент",
  Moderator: "Модератор",
  RiskManager: "Риск-менеджер",
  Admin: "Администратор",
};

function currentMonthValue() {
  return new Date().toISOString().slice(0, 7);
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "KZT",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AssistantWorkspace({
  user,
  adminSummary,
  accessToken,
  refreshToken,
  onSession,
  onAuthFailure,
}: AssistantWorkspaceProps) {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const [overview, setOverview] = useState<AssistantOverview | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [budgetLimit, setBudgetLimit] = useState("");
  const [budgetMonth, setBudgetMonth] = useState(currentMonthValue());
  const [composer, setComposer] = useState("");
  const [importFeedback, setImportFeedback] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingBudget, setIsSavingBudget] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);

  useEffect(() => {
    const loadOverview = async () => {
      setIsLoading(true);
      setWorkspaceError(null);
      try {
        const nextOverview = await fetchAssistantOverview({
          accessToken,
          refreshToken,
          onSession,
        });
        setOverview(nextOverview);
        if (nextOverview.budget) {
          setBudgetLimit(String(nextOverview.budget.monthly_limit));
          setBudgetMonth(nextOverview.budget.month.slice(0, 7));
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          onAuthFailure();
          return;
        }
        setWorkspaceError(
          error instanceof Error ? error.message : "Не удалось загрузить assistant workspace.",
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadOverview();
  }, [accessToken, onAuthFailure, onSession, refreshToken]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [overview?.messages]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const speechWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
    const RecognitionCtor =
      speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    setSpeechSupported(Boolean(RecognitionCtor));

    if (!RecognitionCtor) {
      recognitionRef.current = null;
      return;
    }

    const recognition = new RecognitionCtor();
    recognition.lang = "ru-RU";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? "";
      if (transcript) {
        setComposer((current) => [current, transcript].filter(Boolean).join(" ").trim());
      }
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
    };
  }, []);

  const speak = (text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window) || !text) {
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ru-RU";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const currentBudget = overview?.budget;
  const progressPercent =
    currentBudget && currentBudget.monthly_limit > 0
      ? Math.max(0, Math.min(100, (currentBudget.current_balance / currentBudget.monthly_limit) * 100))
      : 0;

  const saveCurrentBudget = async () => {
    const numericLimit = Number(budgetLimit);
    if (!Number.isFinite(numericLimit) || numericLimit < 0) {
      setWorkspaceError("Введите корректный месячный лимит.");
      return;
    }

    setIsSavingBudget(true);
    setWorkspaceError(null);
    try {
      const budget = await saveBudget(
        { accessToken, refreshToken, onSession },
        { monthly_limit: numericLimit, month: `${budgetMonth}-01` },
      );
      if (budget.month.slice(0, 7) === currentMonthValue()) {
        setOverview((current) =>
          current
            ? { ...current, budget, current_month_spent: budget.spent_amount }
            : current,
        );
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onAuthFailure();
        return;
      }
      setWorkspaceError(error instanceof Error ? error.message : "Не удалось сохранить бюджет.");
    } finally {
      setIsSavingBudget(false);
    }
  };

  const sendMessage = async () => {
    const trimmed = composer.trim();
    if (!trimmed || !overview) {
      return;
    }

    const optimisticUserMessage: AssistantMessage = {
      id: -Date.now(),
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    setComposer("");
    setIsSending(true);
    setOverview((current) =>
      current ? { ...current, messages: [...current.messages, optimisticUserMessage] } : current,
    );

    try {
      const response = await sendAssistantMessage(
        { accessToken, refreshToken, onSession },
        { message: trimmed },
      );
      setOverview((current) =>
        current
          ? {
              ...current,
              budget: response.budget,
              current_month_spent: response.current_month_spent,
              recent_transactions: response.recent_transactions,
              messages: [...current.messages, response.assistant_message],
            }
          : current,
      );
      if (autoSpeak) {
        speak(response.assistant_message.content);
      }
    } catch (error) {
      setOverview((current) =>
        current
          ? {
              ...current,
              messages: current.messages.filter((item) => item.id !== optimisticUserMessage.id),
            }
          : current,
      );
      if (error instanceof ApiError && error.status === 401) {
        onAuthFailure();
        return;
      }
      setWorkspaceError(error instanceof Error ? error.message : "Не удалось отправить сообщение.");
    } finally {
      setIsSending(false);
    }
  };

  const uploadStatement = async (file: File) => {
    setIsUploading(true);
    setImportFeedback(null);
    setWorkspaceError(null);
    try {
      const response = await importTransactions({ accessToken, refreshToken, onSession }, file);
      setOverview((current) =>
        current
          ? {
              ...current,
              budget: response.budget,
              current_month_spent: response.current_month_spent,
              recent_transactions: response.recent_transactions,
            }
          : current,
      );
      setImportFeedback(`Импортировано ${response.imported_count}, пропущено ${response.skipped_count}.`);
      if (response.warnings.length > 0) {
        setWorkspaceError(response.warnings.join(" | "));
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onAuthFailure();
        return;
      }
      setWorkspaceError(error instanceof Error ? error.message : "Не удалось импортировать выписку.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }
    setIsListening(true);
    recognitionRef.current.start();
  };

  const lastAssistantMessage = [...(overview?.messages ?? [])]
    .reverse()
    .find((message) => message.role === "assistant");

  return (
    <div className="space-y-8">
      <section className="grid gap-4 xl:grid-cols-[0.8fr_0.8fr_0.6fr]">
        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-smoke">Текущий бюджет</p>
          <div className="mt-5 rounded-[24px] border border-line bg-white/70 p-5">
            <p className="text-sm text-smoke">Профиль</p>
            <p className="mt-3 text-2xl font-semibold text-ink">{user.email}</p>
            <p className="mt-2 text-sm text-smoke">Роль: {roleLabels[user.role.name] ?? user.role.name}</p>
            <p className="mt-6 text-sm text-smoke">Остаток</p>
            <p className="mt-2 text-4xl font-semibold text-ink">
              {currentBudget ? formatCurrency(currentBudget.current_balance) : "Лимит не задан"}
            </p>
            <p className="mt-3 text-sm text-smoke">
              Потрачено: {formatCurrency(overview?.current_month_spent ?? 0)}
            </p>
            {currentBudget ? (
              <>
                <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/10">
                  <div className="h-full rounded-full bg-ink" style={{ width: `${progressPercent}%` }} />
                </div>
                <p className="mt-3 text-sm text-smoke">
                  Лимит: {formatCurrency(currentBudget.monthly_limit)}
                </p>
              </>
            ) : null}
          </div>
          <div className="mt-5 grid gap-3">
            <input type="month" value={budgetMonth} onChange={(event) => setBudgetMonth(event.target.value)} className="input-field" />
            <input type="number" min="0" step="100" value={budgetLimit} onChange={(event) => setBudgetLimit(event.target.value)} className="input-field" placeholder="Месячный лимит" />
            <button type="button" className="button-primary w-full" onClick={saveCurrentBudget} disabled={isSavingBudget}>
              {isSavingBudget ? "Сохраняю лимит..." : "Сохранить лимит"}
            </button>
          </div>
        </div>

        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-smoke">Импорт выписки</p>
          <div className="mt-5 rounded-[24px] border border-dashed border-line bg-white/60 p-5">
            <p className="text-lg font-semibold text-ink">CSV / Excel в assistant flow</p>
            <p className="mt-3 text-sm leading-7 text-smoke">
              Выписка сохраняется через `file_service`, затем преобразуется в пользовательские транзакции.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void uploadStatement(file);
                }
              }}
            />
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" className="button-primary" onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
                {isUploading ? "Импорт..." : "Прикрепить выписку"}
              </button>
              <button type="button" className={autoSpeak ? "button-primary" : "button-secondary"} onClick={() => setAutoSpeak((current) => !current)}>
                {autoSpeak ? "Автоозвучка включена" : "Включить автоозвучку"}
              </button>
            </div>
            {importFeedback ? (
              <div className="mt-4 rounded-2xl border border-line bg-paper px-4 py-3 text-sm text-ink">
                {importFeedback}
              </div>
            ) : null}
            <p className="mt-4 text-sm text-smoke">
              {speechSupported
                ? "Диктовка доступна через Web Speech API."
                : "SpeechRecognition недоступен в этом браузере."}
            </p>
          </div>
          <div className="mt-5 rounded-[24px] border border-line bg-white/70 p-5">
            <p className="text-sm text-smoke">Последний ответ ассистента</p>
            <p className="mt-3 text-sm leading-7 text-ink">
              {lastAssistantMessage?.content ?? "Еще нет ответа. Напишите первое сообщение."}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" className="button-secondary" onClick={toggleListening} disabled={!speechSupported}>
                {isListening ? "Слушаю..." : "Диктовка"}
              </button>
              <button type="button" className="button-secondary" onClick={() => lastAssistantMessage && speak(lastAssistantMessage.content)}>
                Озвучить ответ
              </button>
            </div>
          </div>
        </div>

        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-smoke">Protected Summary</p>
          {adminSummary ? (
            <div className="mt-5 grid gap-4">
              <div className="rounded-[24px] border border-line bg-white/70 p-5"><p className="text-sm text-smoke">Users</p><p className="mt-2 text-4xl font-semibold text-ink">{adminSummary.users}</p></div>
              <div className="rounded-[24px] border border-line bg-white/70 p-5"><p className="text-sm text-smoke">Transactions</p><p className="mt-2 text-4xl font-semibold text-ink">{adminSummary.transactions}</p></div>
              <div className="rounded-[24px] border border-line bg-white/70 p-5"><p className="text-sm text-smoke">Moderation Queue</p><p className="mt-2 text-4xl font-semibold text-ink">{adminSummary.moderation_items}</p></div>
            </div>
          ) : (
            <div className="mt-5 rounded-[24px] border border-dashed border-line bg-white/50 p-5 text-sm leading-7 text-smoke">
              Для роли `User` административный summary скрыт. Эту область используем на `ЭТАПЕ 3`.
            </div>
          )}
        </div>
      </section>

      {workspaceError ? (
        <div className="rounded-3xl border border-black/10 bg-black px-6 py-4 text-sm text-paper">
          {workspaceError}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel flex min-h-[640px] flex-col p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-smoke">Чат с ИИ-бухгалтером</p>
              <p className="mt-2 text-sm text-smoke">Пишите прямо о тратах, вопросах по бюджету и контроле расходов.</p>
            </div>
          </div>

          <div className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-[28px] border border-line bg-white/50 p-4">
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse rounded-[24px] bg-black/5" />)}
              </div>
            ) : overview && overview.messages.length > 0 ? (
              overview.messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                  className={message.role === "assistant" ? "mr-10" : "ml-10"}
                >
                  <div className={message.role === "assistant" ? "rounded-[24px] border border-line bg-paper px-5 py-4 text-sm leading-7 text-ink" : "rounded-[24px] bg-ink px-5 py-4 text-sm leading-7 text-paper"}>
                    <p className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.3em] opacity-60">
                      {message.role === "assistant" ? "Assistant" : "You"}
                    </p>
                    <p className="mt-3 whitespace-pre-wrap">{message.content}</p>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="flex h-full items-center justify-center rounded-[24px] border border-dashed border-line bg-paper/70 px-6 text-center text-sm leading-7 text-smoke">
                История еще пуста. Задайте лимит, импортируйте выписку или напишите о первой трате.
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="mt-5 rounded-[28px] border border-line bg-white/80 p-4">
            <textarea
              value={composer}
              onChange={(event) => setComposer(event.target.value)}
              placeholder="Например: Купил кофе за 1200 тенге и вызвал такси за 2500."
              className="min-h-[110px] w-full resize-none bg-transparent text-sm leading-7 text-ink outline-none"
            />
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button type="button" className="button-primary" onClick={() => void sendMessage()} disabled={isSending || isLoading}>
                {isSending ? "Отправка..." : "Отправить"}
              </button>
              <button type="button" className="button-secondary" onClick={toggleListening} disabled={!speechSupported}>
                {isListening ? "Слушаю..." : "Диктовка"}
              </button>
              <button type="button" className="button-secondary" onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
                Прикрепить файл
              </button>
            </div>
          </div>
        </div>

        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-smoke">Recent Ledger</p>
          <div className="mt-5 space-y-3">
            {(overview?.recent_transactions ?? []).map((transaction: Transaction) => (
              <div key={transaction.id} className="rounded-[24px] border border-line bg-white/70 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">{transaction.category || "Без категории"}</p>
                    <p className="mt-1 text-sm text-smoke">{transaction.description || "Описание не указано"}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-smoke">{formatDate(transaction.occurred_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-ink">{formatCurrency(transaction.amount)}</p>
                    <p className="mt-2 text-xs text-smoke">{transaction.source_filename || "chat-entry"}</p>
                  </div>
                </div>
              </div>
            ))}
            {overview && overview.recent_transactions.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-line bg-white/50 p-5 text-sm leading-7 text-smoke">
                Пока нет транзакций. Импортируйте выписку или сообщите о трате в чате.
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
