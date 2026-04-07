"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/api";
import { fetchLegacyProfileReport } from "@/lib/legacy-api";
import { useSessionContext } from "@/lib/use-session-context";

export function LegacyProfileViewer() {
  const searchParams = useSearchParams();
  const { session, onAuthFailure } = useSessionContext();
  const [reportFilename, setReportFilename] = useState("");
  const [html, setHtml] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fromUrl = searchParams.get("report");
    const fromStorage =
      typeof window !== "undefined" ? window.localStorage.getItem("legacy:lastProfileReport") : null;
    setReportFilename(fromUrl || fromStorage || "");
  }, [searchParams]);

  const loadReport = async (target = reportFilename) => {
    if (!session || !target) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const reportHtml = await fetchLegacyProfileReport(session, target);
      setHtml(reportHtml);
      window.localStorage.setItem("legacy:lastProfileReport", target);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Не удалось открыть profile-отчет.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (session && reportFilename) {
      void loadReport(reportFilename);
    }
    // loadReport intentionally stays out of deps to avoid repeating iframe reloads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportFilename, session]);

  return (
    <section className="panel p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
            Data Profile
          </p>
          <h2 className="mt-3 text-3xl font-semibold text-ink">HTML-отчет ydata-profiling</h2>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-smoke">
            Это перенос страницы `0_Data_Profile.py`: отчет генерируется старым
            `profiling_service`, а новый фронт показывает его внутри защищенного интерфейса.
          </p>
        </div>
        <div className="flex min-w-0 flex-col gap-3 sm:min-w-[360px] sm:flex-row">
          <input
            className="input-field"
            value={reportFilename}
            onChange={(event) => setReportFilename(event.target.value)}
            placeholder="example_profile.html"
          />
          <button
            className="button-primary whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!reportFilename || isLoading}
            onClick={() => void loadReport()}
          >
            {isLoading ? "Загрузка..." : "Открыть"}
          </button>
        </div>
      </div>

      {error ? <p className="mt-6 rounded-2xl bg-ink p-4 text-sm text-paper">{error}</p> : null}

      <div className="mt-6 overflow-hidden rounded-[24px] border border-line bg-white">
        {html ? (
          <iframe
            title="Data profile report"
            className="h-[760px] w-full bg-white"
            srcDoc={html}
          />
        ) : (
          <div className="flex min-h-[360px] items-center justify-center p-8 text-center text-sm leading-7 text-smoke">
            Постройте профиль на странице “Данные” или укажите имя ранее созданного HTML-отчета.
          </div>
        )}
      </div>
    </section>
  );
}
