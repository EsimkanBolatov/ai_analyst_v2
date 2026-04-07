"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  analyzeLegacyFile,
  fetchLegacyFiles,
  sendLegacyAiChat,
} from "@/lib/legacy-api";
import type { LegacyAiAnalysis, LegacyChatMessage } from "@/lib/legacy-types";
import { useSessionContext } from "@/lib/use-session-context";

const statLabels: Record<string, string> = {
  min_val: "Min",
  p25: "P25",
  median: "Median",
  p75: "P75",
  max_val: "Max",
  mean_val: "Mean",
  count: "Count",
};

function formatValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toString() : value.toFixed(2);
  }
  if (value === null || value === undefined) {
    return "n/a";
  }
  return String(value);
}

export function LegacyAiReport() {
  const { session, onAuthFailure } = useSessionContext();
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [analysis, setAnalysis] = useState<LegacyAiAnalysis | null>(null);
  const [chatHistory, setChatHistory] = useState<LegacyChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedFile = window.localStorage.getItem("legacy:lastAnalysisFile");
    const storedAnalysis = window.localStorage.getItem("legacy:lastAnalysis");
    if (storedFile) {
      setSelectedFile(storedFile);
    }
    if (storedAnalysis) {
      try {
        setAnalysis(JSON.parse(storedAnalysis) as LegacyAiAnalysis);
      } catch {
        window.localStorage.removeItem("legacy:lastAnalysis");
      }
    }
  }, []);

  useEffect(() => {
    if (!session) {
      return;
    }
    const loadFiles = async () => {
      try {
        const nextFiles = await fetchLegacyFiles(session);
        setFiles(nextFiles);
        setSelectedFile((current) => current || nextFiles[0] || "");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          onAuthFailure();
          return;
        }
        setError(err instanceof Error ? err.message : "Не удалось загрузить список файлов.");
      }
    };
    void loadFiles();
  }, [onAuthFailure, session]);

  const handleAnalyze = async () => {
    if (!session || !selectedFile) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await analyzeLegacyFile(session, selectedFile);
      setAnalysis(result);
      window.localStorage.setItem("legacy:lastAnalysisFile", selectedFile);
      window.localStorage.setItem("legacy:lastAnalysis", JSON.stringify(result));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Не удалось выполнить AI-анализ.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChat = async () => {
    if (!session || !selectedFile || !prompt.trim()) {
      return;
    }
    const nextHistory = [...chatHistory, { role: "user", content: prompt.trim() }];
    setChatHistory(nextHistory);
    setPrompt("");
    setIsChatLoading(true);
    setError(null);
    try {
      const response = await sendLegacyAiChat(session, {
        filename: selectedFile,
        chat_history: nextHistory,
      });
      setChatHistory([...nextHistory, response]);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Чат AI-аналитика недоступен.");
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="panel p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
              AI Analyst Report
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-ink">Отчет по датасету и аномалиям</h2>
          </div>
          <div className="flex min-w-0 flex-col gap-3 sm:min-w-[420px] sm:flex-row">
            <select className="input-field" value={selectedFile} onChange={(event) => setSelectedFile(event.target.value)}>
              {files.length === 0 ? <option value="">Файлы не найдены</option> : null}
              {files.map((file) => (
                <option key={file} value={file}>
                  {file}
                </option>
              ))}
            </select>
            <button
              className="button-primary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!selectedFile || isLoading}
              onClick={handleAnalyze}
            >
              {isLoading ? "Анализ..." : "Запустить"}
            </button>
          </div>
        </div>

        {error ? <p className="mt-6 rounded-2xl bg-ink p-4 text-sm text-paper">{error}</p> : null}

        {analysis ? (
          <div className="mt-6 space-y-6">
            <article className="rounded-[24px] border border-line bg-white/70 p-5">
              <h3 className="text-xl font-semibold text-ink">Основные выводы</h3>
              <p className="mt-3 text-sm leading-7 text-smoke">{analysis.main_findings}</p>
            </article>

            {analysis.amount_distribution_stats ? (
              <article className="rounded-[24px] border border-line bg-white/70 p-5">
                <h3 className="text-xl font-semibold text-ink">Распределение суммы</h3>
                <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
                  {Object.entries(analysis.amount_distribution_stats).map(([key, value]) => (
                    <div key={key} className="rounded-2xl border border-line bg-panel p-4">
                      <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.2em] text-smoke">
                        {statLabels[key] ?? key}
                      </p>
                      <p className="mt-2 text-2xl font-semibold text-ink">{formatValue(value)}</p>
                    </div>
                  ))}
                </div>
              </article>
            ) : null}

            <article className="rounded-[24px] border border-line bg-white/70 p-5">
              <h3 className="text-xl font-semibold text-ink">Аномалии</h3>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-[0.2em] text-smoke">
                    <tr>
                      <th className="border-b border-line px-3 py-3">Row</th>
                      <th className="border-b border-line px-3 py-3">Reason</th>
                      <th className="border-b border-line px-3 py-3">Amount</th>
                      <th className="border-b border-line px-3 py-3">Hour</th>
                      <th className="border-b border-line px-3 py-3">MCC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.anomalies.map((item) => (
                      <tr key={`${item.row_index}-${item.reason}`} className="text-smoke">
                        <td className="border-b border-line px-3 py-3 font-semibold text-ink">{item.row_index}</td>
                        <td className="border-b border-line px-3 py-3">{item.reason}</td>
                        <td className="border-b border-line px-3 py-3">{formatValue(item.plot_data?.transaction_amount_kzt)}</td>
                        <td className="border-b border-line px-3 py-3">{formatValue(item.plot_data?.transaction_hour)}</td>
                        <td className="border-b border-line px-3 py-3">{formatValue(item.plot_data?.mcc_category)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="rounded-[24px] border border-line bg-white/70 p-5">
              <h3 className="text-xl font-semibold text-ink">Feature engineering</h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {analysis.feature_engineering_ideas.map((idea) => (
                  <span key={idea} className="rounded-full border border-line bg-panel px-4 py-2 text-sm text-smoke">
                    {idea}
                  </span>
                ))}
              </div>
              <h3 className="mt-6 text-xl font-semibold text-ink">Рекомендации</h3>
              <p className="mt-3 text-sm leading-7 text-smoke">{analysis.recommendations}</p>
            </article>
          </div>
        ) : (
          <div className="mt-6 rounded-[24px] border border-line bg-white/70 p-8 text-sm leading-7 text-smoke">
            Выберите файл и запустите анализ. Результат будет сохранен в localStorage для быстрого возврата на страницу.
          </div>
        )}
      </section>

      <aside className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Analyst chat
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Чат по датасету</h2>
        <div className="mt-5 h-[520px] space-y-3 overflow-y-auto rounded-[24px] border border-line bg-white/60 p-4">
          {chatHistory.length === 0 ? (
            <p className="text-sm leading-7 text-smoke">
              Спросите AI-аналитика о выбранном файле. Контекстом будет head датасета из старого `groq_service`.
            </p>
          ) : null}
          {chatHistory.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={message.role === "user" ? "ml-auto max-w-[85%] rounded-3xl bg-ink p-4 text-sm text-paper" : "max-w-[85%] rounded-3xl border border-line bg-panel p-4 text-sm leading-7 text-smoke"}
            >
              {message.content}
            </div>
          ))}
        </div>
        <div className="mt-4 flex gap-3">
          <input
            className="input-field"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Что необычного в транзакциях?"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                void handleChat();
              }
            }}
          />
          <button
            className="button-primary disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!selectedFile || !prompt.trim() || isChatLoading}
            onClick={() => void handleChat()}
          >
            {isChatLoading ? "..." : "Send"}
          </button>
        </div>
      </aside>
    </div>
  );
}
