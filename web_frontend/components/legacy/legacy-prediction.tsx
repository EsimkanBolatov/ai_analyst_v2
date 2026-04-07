"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  fetchLegacyFiles,
  fetchLegacyModelConfig,
  fetchLegacyModels,
  predictLegacyRow,
  scoreLegacyFile,
} from "@/lib/legacy-api";
import type {
  LegacyModelConfig,
  LegacyPredictionResponse,
  LegacyScoreFileResponse,
} from "@/lib/legacy-types";
import { useSessionContext } from "@/lib/use-session-context";

function scoreStats(scores: number[]) {
  if (scores.length === 0) {
    return { count: 0, min: 0, max: 0, mean: 0, anomalies: 0 };
  }
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const mean = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  const anomalies = scores.filter((score) => score < 0).length;
  return { count: scores.length, min, max, mean, anomalies };
}

function normalizeScore(score: number, min: number, max: number) {
  if (max === min) {
    return 50;
  }
  return Math.max(8, Math.min(100, ((score - min) / (max - min)) * 100));
}

export function LegacyPrediction() {
  const { session, onAuthFailure } = useSessionContext();
  const [files, setFiles] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [filename, setFilename] = useState("");
  const [modelName, setModelName] = useState("");
  const [config, setConfig] = useState<LegacyModelConfig | null>(null);
  const [featureInputs, setFeatureInputs] = useState<Record<string, string>>({});
  const [scoreResult, setScoreResult] = useState<LegacyScoreFileResponse | null>(null);
  const [prediction, setPrediction] = useState<LegacyPredictionResponse | null>(null);
  const [isScoring, setIsScoring] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      return;
    }
    const load = async () => {
      try {
        const [nextFiles, nextModels] = await Promise.all([
          fetchLegacyFiles(session),
          fetchLegacyModels(session),
        ]);
        setFiles(nextFiles);
        setModels(nextModels.models);
        setFilename((current) => current || nextFiles[0] || "");
        setModelName((current) => current || nextModels.models[0] || "");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          onAuthFailure();
          return;
        }
        setError(err instanceof Error ? err.message : "Не удалось загрузить файлы или модели.");
      }
    };
    void load();
  }, [onAuthFailure, session]);

  useEffect(() => {
    if (!session || !modelName) {
      setConfig(null);
      return;
    }
    const loadConfig = async () => {
      try {
        const nextConfig = await fetchLegacyModelConfig(session, modelName);
        setConfig(nextConfig);
        const generated = new Set([
          ...(nextConfig.generated_date_features ?? []),
          ...(nextConfig.generated_eng_features ?? []),
        ]);
        const inputs: Record<string, string> = {};
        for (const feature of [
          ...nextConfig.numerical_features,
          ...nextConfig.categorical_features,
          ...nextConfig.date_features,
        ]) {
          if (!generated.has(feature)) {
            inputs[feature] = "";
          }
        }
        setFeatureInputs(inputs);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          onAuthFailure();
          return;
        }
        setConfig(null);
        setError(err instanceof Error ? err.message : "Не удалось загрузить конфиг модели.");
      }
    };
    void loadConfig();
  }, [modelName, onAuthFailure, session]);

  const stats = useMemo(() => scoreStats(scoreResult?.scores ?? []), [scoreResult]);

  const handleScoreFile = async () => {
    if (!session || !modelName || !filename) {
      return;
    }
    setIsScoring(true);
    setError(null);
    try {
      const result = await scoreLegacyFile(session, { model_name: modelName, filename });
      setScoreResult(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка batch score.");
    } finally {
      setIsScoring(false);
    }
  };

  const handlePredict = async () => {
    if (!session || !modelName || !config) {
      return;
    }

    const features: Record<string, unknown> = {};
    const numeric = new Set(config.numerical_features);
    for (const [key, value] of Object.entries(featureInputs)) {
      features[key] = numeric.has(key) ? Number(value || 0) : value;
    }

    setIsPredicting(true);
    setError(null);
    try {
      const result = await predictLegacyRow(session, { model_name: modelName, features });
      setPrediction(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка ручного predict.");
    } finally {
      setIsPredicting(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Prediction
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Скоринг файла и ручной predict</h2>
        <p className="mt-3 text-sm leading-7 text-smoke">
          Перенос страницы `3_Prediction.py`: batch score по CSV и динамическая форма по конфигу модели.
        </p>

        <div className="mt-6 grid gap-4">
          <label className="block text-sm font-semibold text-ink">
            Модель
            <select className="input-field mt-2" value={modelName} onChange={(event) => setModelName(event.target.value)}>
              {models.length === 0 ? <option value="">Модели не найдены</option> : null}
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold text-ink">
            Файл для batch score
            <select className="input-field mt-2" value={filename} onChange={(event) => setFilename(event.target.value)}>
              {files.length === 0 ? <option value="">Файлы не найдены</option> : null}
              {files.map((file) => (
                <option key={file} value={file}>
                  {file}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          className="button-primary mt-5 w-full disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!modelName || !filename || isScoring}
          onClick={() => void handleScoreFile()}
        >
          {isScoring ? "Скоринг..." : "Score file"}
        </button>

        {scoreResult ? (
          <div className="mt-6 rounded-[24px] border border-line bg-white/70 p-5">
            <h3 className="text-xl font-semibold text-ink">Распределение anomaly score</h3>
            <div className="mt-4 grid gap-3 sm:grid-cols-5">
              {[
                ["Count", stats.count],
                ["Anomaly", stats.anomalies],
                ["Min", stats.min.toFixed(3)],
                ["Mean", stats.mean.toFixed(3)],
                ["Max", stats.max.toFixed(3)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-line bg-panel p-3">
                  <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.2em] text-smoke">{label}</p>
                  <p className="mt-2 text-xl font-semibold text-ink">{value}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 space-y-2">
              {scoreResult.scores.slice(0, 24).map((score, index) => (
                <div key={`${score}-${index}`} className="flex items-center gap-3">
                  <span className="w-10 font-[family-name:var(--font-mono)] text-xs text-smoke">#{index}</span>
                  <div className="h-3 flex-1 overflow-hidden rounded-full bg-line">
                    <div
                      className={score < 0 ? "h-full rounded-full bg-ink" : "h-full rounded-full bg-smoke"}
                      style={{ width: `${normalizeScore(score, stats.min, stats.max)}%` }}
                    />
                  </div>
                  <span className="w-20 text-right font-[family-name:var(--font-mono)] text-xs text-smoke">{score.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {error ? <p className="mt-5 rounded-2xl bg-ink p-4 text-sm text-paper">{error}</p> : null}
      </section>

      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Single row
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Динамическая форма признаков</h2>

        {config ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {Object.keys(featureInputs).length === 0 ? (
              <p className="text-sm leading-7 text-smoke">В конфиге нет ручных признаков для ввода.</p>
            ) : null}
            {Object.entries(featureInputs).map(([feature, value]) => {
              const categoricalOptions = config.categorical_values?.[feature] ?? [];
              const isDate = config.date_features.includes(feature);
              const isNumeric = config.numerical_features.includes(feature);
              return (
                <label key={feature} className="block text-sm font-semibold text-ink">
                  {feature}
                  {categoricalOptions.length > 0 ? (
                    <select
                      className="input-field mt-2"
                      value={value}
                      onChange={(event) => setFeatureInputs((current) => ({ ...current, [feature]: event.target.value }))}
                    >
                      <option value="">Выберите значение</option>
                      {categoricalOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className="input-field mt-2"
                      type={isDate ? "datetime-local" : isNumeric ? "number" : "text"}
                      value={value}
                      onChange={(event) => setFeatureInputs((current) => ({ ...current, [feature]: event.target.value }))}
                    />
                  )}
                </label>
              );
            })}
          </div>
        ) : (
          <p className="mt-6 rounded-[24px] border border-line bg-white/70 p-5 text-sm leading-7 text-smoke">
            Выберите модель, чтобы загрузить ее конфиг.
          </p>
        )}

        <button
          className="button-primary mt-6 w-full disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!config || isPredicting}
          onClick={() => void handlePredict()}
        >
          {isPredicting ? "Predict..." : "Predict / Score row"}
        </button>

        {prediction ? (
          <div className="mt-6 rounded-[24px] border border-line bg-white/70 p-5">
            <h3 className="text-xl font-semibold text-ink">Результат</h3>
            <pre className="mt-4 overflow-x-auto rounded-2xl bg-ink p-4 text-xs leading-6 text-paper">
              {JSON.stringify(prediction, null, 2)}
            </pre>
          </div>
        ) : null}
      </section>
    </div>
  );
}
