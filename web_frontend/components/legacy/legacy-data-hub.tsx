"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import {
  analyzeLegacyFile,
  createLegacyProfile,
  fetchLegacyFiles,
  uploadLegacyFile,
} from "@/lib/legacy-api";
import type { LegacyAiAnalysis } from "@/lib/legacy-types";
import { useSessionContext } from "@/lib/use-session-context";

export function LegacyDataHub() {
  const router = useRouter();
  const { session, onAuthFailure } = useSessionContext();
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<LegacyAiAnalysis | null>(null);

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

  const refreshFiles = async () => {
    if (!session) {
      return;
    }
    const nextFiles = await fetchLegacyFiles(session);
    setFiles(nextFiles);
    setSelectedFile((current) => current || nextFiles[0] || "");
  };

  const handleUpload = async () => {
    if (!session || !uploadFile) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await uploadLegacyFile(session, uploadFile);
      const filename = result.filename ?? uploadFile.name;
      setMessage(`Файл загружен: ${filename}`);
      setSelectedFile(filename);
      setUploadFile(null);
      await refreshFiles();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка загрузки файла.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleProfile = async () => {
    if (!session || !selectedFile) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await createLegacyProfile(session, selectedFile);
      window.localStorage.setItem("legacy:lastProfileReport", result.report_filename);
      window.localStorage.setItem("legacy:lastProfileFile", selectedFile);
      router.push(`/ml-lab/profile?report=${encodeURIComponent(result.report_filename)}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка построения profile-отчета.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalysis = async () => {
    if (!session || !selectedFile) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await analyzeLegacyFile(session, selectedFile);
      setAnalysis(result);
      window.localStorage.setItem("legacy:lastAnalysisFile", selectedFile);
      window.localStorage.setItem("legacy:lastAnalysis", JSON.stringify(result));
      setMessage("AI-анализ завершен. Полный отчет доступен на странице AI Report.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка AI-анализа.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Upload + dataset registry
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Датасеты legacy-контура</h2>
        <p className="mt-3 text-sm leading-7 text-smoke">
          Файлы сохраняются в общий `file_service`, который использовали старые
          Streamlit-страницы и ML-сервисы.
        </p>

        <div className="mt-6 space-y-4">
          <input
            className="input-field"
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
          />
          <button
            className="button-primary w-full disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!uploadFile || isLoading}
            onClick={handleUpload}
          >
            {isLoading ? "Выполняется..." : "Загрузить файл"}
          </button>
        </div>

        <div className="mt-8">
          <label className="text-sm font-semibold text-ink" htmlFor="legacy-file">
            Активный файл
          </label>
          <select
            id="legacy-file"
            className="input-field mt-2"
            value={selectedFile}
            onChange={(event) => setSelectedFile(event.target.value)}
          >
            {files.length === 0 ? <option value="">Файлы не найдены</option> : null}
            {files.map((file) => (
              <option key={file} value={file}>
                {file}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <button
            className="button-secondary disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!selectedFile || isLoading}
            onClick={handleProfile}
          >
            Построить Data Profile
          </button>
          <button
            className="button-primary disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!selectedFile || isLoading}
            onClick={handleAnalysis}
          >
            Запустить AI-анализ
          </button>
        </div>

        {message ? <p className="mt-5 rounded-2xl bg-white/70 p-4 text-sm text-ink">{message}</p> : null}
        {error ? <p className="mt-5 rounded-2xl bg-ink p-4 text-sm text-paper">{error}</p> : null}
      </section>

      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Migrated pages
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Навигация по старым сценариям</h2>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {[
            ["/ml-lab/profile", "Data Profile", "HTML-отчет ydata-profiling"],
            ["/ml-lab/ai-report", "AI Analyst Report", "выводы, аномалии и чат"],
            ["/ml-lab/train", "Train Model", "IsolationForest / LOF / OneClassSVM"],
            ["/ml-lab/prediction", "Prediction", "batch score и ручной predict"],
            ["/ml-lab/fraud-check", "Fraud Check", "phone/email/url/text risk scoring"],
          ].map(([href, title, description]) => (
            <Link key={href} href={href} className="rounded-[24px] border border-line bg-white/70 p-5 hover:border-ink">
              <span className="text-lg font-semibold text-ink">{title}</span>
              <span className="mt-2 block text-sm leading-6 text-smoke">{description}</span>
            </Link>
          ))}
        </div>

        <div className="mt-8 rounded-[24px] border border-line bg-white/70 p-5">
          <h3 className="text-xl font-semibold text-ink">Быстрый результат AI-анализа</h3>
          {analysis ? (
            <div className="mt-4 space-y-4 text-sm leading-7 text-smoke">
              <p>{analysis.main_findings}</p>
              <p>
                Найдено аномалий: <span className="font-semibold text-ink">{analysis.anomalies?.length ?? 0}</span>
              </p>
              <Link href="/ml-lab/ai-report" className="button-secondary">
                Открыть полный AI Report
              </Link>
            </div>
          ) : (
            <p className="mt-4 text-sm leading-7 text-smoke">
              Запустите AI-анализ слева, чтобы увидеть краткий результат и перейти в полный отчет.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
