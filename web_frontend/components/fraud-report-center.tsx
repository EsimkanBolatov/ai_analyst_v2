"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

import { ApiError, fetchMyFraudReports, submitFraudReport } from "@/lib/api";
import type { FraudDataType, ModerationItem, TokenPair, User } from "@/lib/types";

type FraudReportCenterProps = {
  user: User;
  accessToken: string;
  refreshToken: string;
  onSession: (session: TokenPair) => void;
  onAuthFailure: () => void;
};

const dataTypeOptions: Array<{ value: FraudDataType; label: string }> = [
  { value: "phone", label: "Телефон" },
  { value: "url", label: "Ссылка" },
  { value: "email", label: "Email" },
  { value: "text", label: "Текст" },
];

const statusStyles: Record<string, string> = {
  pending: "bg-black text-paper",
  approved: "bg-white text-ink border border-line",
  rejected: "bg-white text-smoke border border-line",
};

const statusLabels: Record<string, string> = {
  pending: "На проверке",
  approved: "Одобрено",
  rejected: "Отклонено",
};

export function FraudReportCenter({
  user,
  accessToken,
  refreshToken,
  onSession,
  onAuthFailure,
}: FraudReportCenterProps) {
  const [dataType, setDataType] = useState<FraudDataType>("phone");
  const [value, setValue] = useState("");
  const [comment, setComment] = useState("");
  const [reports, setReports] = useState<ModerationItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const loadReports = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const items = await fetchMyFraudReports({ accessToken, refreshToken, onSession });
        setReports(items);
      } catch (loadError) {
        if (loadError instanceof ApiError && loadError.status === 401) {
          onAuthFailure();
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить жалобы.");
      } finally {
        setIsLoading(false);
      }
    };

    void loadReports();
  }, [accessToken, onAuthFailure, onSession, refreshToken]);

  const submitReport = async () => {
    if (!value.trim()) {
      setError("Введите значение для проверки.");
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);
    setError(null);

    try {
      const response = await submitFraudReport(
        { accessToken, refreshToken, onSession },
        {
          data_type: dataType,
          value: value.trim(),
          user_comment: comment.trim() || undefined,
        },
      );
      setReports((current) => [response.item, ...current]);
      setFeedback(
        response.already_blacklisted
          ? "Жалоба принята. Значение уже присутствует в подтвержденном blacklist."
          : "Жалоба отправлена в очередь модерации.",
      );
      setValue("");
      setComment("");
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onAuthFailure();
        return;
      }
      setError(submitError instanceof Error ? submitError.message : "Не удалось отправить жалобу.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
      <div className="panel p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-smoke">Fraud Report</p>
        <h2 className="mt-4 text-3xl font-semibold text-ink">Краудсорсинг подозрительных кейсов</h2>
        <p className="mt-3 text-sm leading-7 text-smoke">
          Пользователь {user.email} может отправить номер, ссылку, email или текст. AI сначала
          присвоит категорию, затем кейс уйдет в очередь модерации.
        </p>

        <div className="mt-6 grid gap-3">
          <select
            value={dataType}
            onChange={(event) => setDataType(event.target.value as FraudDataType)}
            className="input-field"
          >
            {dataTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            value={value}
            onChange={(event) => setValue(event.target.value)}
            className="input-field"
            placeholder="Введите номер, ссылку, email или текст"
          />
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            className="input-field min-h-[140px] resize-none"
            placeholder="Опишите, почему вы считаете это мошенничеством"
          />
          <button
            type="button"
            className="button-primary w-full"
            onClick={submitReport}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Отправка..." : "Отправить жалобу"}
          </button>
        </div>

        {feedback ? (
          <div className="mt-4 rounded-2xl border border-line bg-paper px-4 py-3 text-sm text-ink">
            {feedback}
          </div>
        ) : null}
        {error ? (
          <div className="mt-4 rounded-2xl border border-black/10 bg-black px-4 py-3 text-sm text-paper">
            {error}
          </div>
        ) : null}
      </div>

      <div className="panel p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-smoke">My Reports</p>
        <div className="mt-5 space-y-3">
          {isLoading ? (
            [1, 2, 3].map((item) => (
              <div key={item} className="h-28 animate-pulse rounded-[24px] bg-black/5" />
            ))
          ) : reports.length > 0 ? (
            reports.map((report) => (
              <motion.article
                key={report.id}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className="rounded-[24px] border border-line bg-white/70 p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-smoke">
                      {report.data_type}
                    </p>
                    <p className="mt-2 text-lg font-semibold text-ink">{report.value}</p>
                    <p className="mt-2 text-sm leading-7 text-smoke">
                      {report.user_comment || "Комментарий не добавлен."}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-2 text-xs font-semibold uppercase tracking-[0.25em] ${statusStyles[report.status] ?? statusStyles.pending}`}
                  >
                    {statusLabels[report.status] ?? report.status}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-line bg-paper px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-smoke">AI-категория</p>
                    <p className="mt-2 text-sm font-semibold text-ink">
                      {report.ai_category || "Обрабатывается"}
                    </p>
                    <p className="mt-2 text-sm text-smoke">
                      {report.ai_summary || "AI-анализ еще не завершился."}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-line bg-paper px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-smoke">Модерация</p>
                    <p className="mt-2 text-sm text-smoke">
                      {report.moderator_comment || "Комментарий модератора еще отсутствует."}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-smoke">
                      {new Intl.DateTimeFormat("ru-RU", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }).format(new Date(report.created_at))}
                    </p>
                  </div>
                </div>
              </motion.article>
            ))
          ) : (
            <div className="rounded-[24px] border border-dashed border-line bg-white/50 p-5 text-sm leading-7 text-smoke">
              Пока нет отправленных жалоб. Первый кейс можно отправить из формы слева.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
