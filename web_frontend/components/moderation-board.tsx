"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import {
  ApiError,
  fetchModerationQueue,
  resolveModerationItem,
  type SessionRequestContext,
} from "@/lib/api";
import type { ModerationFilterStatus, ModerationItem } from "@/lib/types";

type ModerationBoardProps = {
  session: SessionRequestContext;
  onAuthFailure: () => void;
};

const statusOptions: Array<{ value: ModerationFilterStatus; label: string }> = [
  { value: "pending", label: "Pending" },
  { value: "all", label: "All" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export function ModerationBoard({ session, onAuthFailure }: ModerationBoardProps) {
  const [statusFilter, setStatusFilter] = useState<ModerationFilterStatus>("pending");
  const [queue, setQueue] = useState<ModerationItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    total_count: 0,
    pending_count: 0,
    approved_count: 0,
    rejected_count: 0,
    blacklist_count: 0,
  });
  const [decisionMap, setDecisionMap] = useState<Record<number, string>>({});
  const [resolvingId, setResolvingId] = useState<number | null>(null);

  useEffect(() => {
    const loadQueue = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchModerationQueue(session, { status: statusFilter });
        setQueue(response.items);
        setStats({
          total_count: response.total_count,
          pending_count: response.pending_count,
          approved_count: response.approved_count,
          rejected_count: response.rejected_count,
          blacklist_count: response.blacklist_count,
        });
      } catch (loadError) {
        if (loadError instanceof ApiError && loadError.status === 401) {
          onAuthFailure();
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить moderation queue.");
      } finally {
        setIsLoading(false);
      }
    };

    void loadQueue();
  }, [onAuthFailure, session, statusFilter]);

  const summaryCards = useMemo(
    () => [
      { label: "Pending", value: stats.pending_count },
      { label: "Approved", value: stats.approved_count },
      { label: "Rejected", value: stats.rejected_count },
      { label: "Blacklist", value: stats.blacklist_count },
    ],
    [stats],
  );

  const resolveItem = async (item: ModerationItem, action: "approved" | "rejected") => {
    setResolvingId(item.id);
    setError(null);
    try {
      const response = await resolveModerationItem(session, item.id, {
        action,
        moderator_comment: decisionMap[item.id]?.trim() || undefined,
      });
      setQueue((current) => {
        if (statusFilter === "pending") {
          return current.filter((entry) => entry.id !== item.id);
        }
        return current.map((entry) => (entry.id === item.id ? response.item : entry));
      });
      setStats((current) => ({
        ...current,
        pending_count: Math.max(0, current.pending_count - (item.status === "pending" ? 1 : 0)),
        approved_count: current.approved_count + (action === "approved" ? 1 : 0),
        rejected_count: current.rejected_count + (action === "rejected" ? 1 : 0),
        blacklist_count: current.blacklist_count + (response.blacklist_entry ? 1 : 0),
      }));
    } catch (resolveError) {
      if (resolveError instanceof ApiError && resolveError.status === 401) {
        onAuthFailure();
        return;
      }
      setError(resolveError instanceof Error ? resolveError.message : "Не удалось обработать решение.");
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        {summaryCards.map((card) => (
          <div key={card.label} className="panel p-5">
            <p className="text-xs uppercase tracking-[0.3em] text-smoke">{card.label}</p>
            <p className="mt-3 text-4xl font-semibold text-ink">{card.value}</p>
          </div>
        ))}
      </section>

      <section className="panel p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-smoke">Moderation Queue</p>
            <h2 className="mt-3 text-3xl font-semibold text-ink">Очередь кейсов на ручную проверку</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {statusOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={statusFilter === option.value ? "button-primary" : "button-secondary"}
                onClick={() => setStatusFilter(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <div className="mt-5 rounded-2xl border border-black/10 bg-black px-4 py-3 text-sm text-paper">
            {error}
          </div>
        ) : null}

        <div className="mt-6 space-y-4">
          {isLoading ? (
            [1, 2, 3].map((item) => (
              <div key={item} className="h-56 animate-pulse rounded-[28px] bg-black/5" />
            ))
          ) : queue.length > 0 ? (
            <AnimatePresence initial={false}>
              {queue.map((item) => (
                <motion.article
                  key={item.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: item.status === "approved" ? 80 : -80 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="rounded-[28px] border border-line bg-white/70 p-6"
                >
                  <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="rounded-full bg-ink px-3 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-paper">
                          {item.data_type}
                        </span>
                        <span className="rounded-full border border-line px-3 py-2 text-xs uppercase tracking-[0.2em] text-smoke">
                          {item.status}
                        </span>
                      </div>
                      <h3 className="mt-4 text-2xl font-semibold text-ink">{item.value}</h3>
                      <p className="mt-3 text-sm leading-7 text-smoke">
                        {item.user_comment || "Комментарий пользователя не добавлен."}
                      </p>
                      <div className="mt-5 rounded-[24px] border border-line bg-paper p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-smoke">AI verdict</p>
                        <p className="mt-2 text-lg font-semibold text-ink">
                          {item.ai_category || "Ожидает фоновой категоризации"}
                        </p>
                        <p className="mt-2 text-sm leading-7 text-smoke">
                          {item.ai_summary || "AI-анализ еще не завершился."}
                        </p>
                        <p className="mt-3 text-xs uppercase tracking-[0.2em] text-smoke">
                          Confidence: {item.ai_confidence ? `${Math.round(item.ai_confidence * 100)}%` : "N/A"}
                        </p>
                      </div>
                    </div>

                    <div>
                      <div className="rounded-[24px] border border-line bg-paper p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-smoke">Reporter</p>
                        <p className="mt-2 text-sm font-semibold text-ink">{item.reporter.email}</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.2em] text-smoke">
                          {new Intl.DateTimeFormat("ru-RU", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(item.created_at))}
                        </p>
                      </div>

                      <textarea
                        value={decisionMap[item.id] ?? ""}
                        onChange={(event) =>
                          setDecisionMap((current) => ({ ...current, [item.id]: event.target.value }))
                        }
                        className="input-field mt-4 min-h-[130px] resize-none"
                        placeholder="Комментарий модератора"
                      />

                      <div className="mt-4 flex flex-wrap gap-3">
                        <button
                          type="button"
                          className="button-primary"
                          onClick={() => void resolveItem(item, "approved")}
                          disabled={resolvingId === item.id}
                        >
                          {resolvingId === item.id ? "Обработка..." : "Одобрить"}
                        </button>
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={() => void resolveItem(item, "rejected")}
                          disabled={resolvingId === item.id}
                        >
                          Отклонить
                        </button>
                      </div>
                    </div>
                  </div>
                </motion.article>
              ))}
            </AnimatePresence>
          ) : (
            <div className="rounded-[28px] border border-dashed border-line bg-white/50 p-6 text-sm leading-7 text-smoke">
              Для выбранного фильтра очередь пуста.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
