"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  fetchLegacyColumns,
  fetchLegacyFiles,
  fetchLegacyModels,
  trainLegacyAnomalyDetector,
} from "@/lib/legacy-api";
import type { LegacyModelType, LegacyTrainPayload } from "@/lib/legacy-types";
import { useSessionContext } from "@/lib/use-session-context";

const modelTypes: LegacyModelType[] = ["IsolationForest", "LocalOutlierFactor", "OneClassSVM"];

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function LegacyTrainModel() {
  const { session, onAuthFailure } = useSessionContext();
  const [files, setFiles] = useState<string[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [filename, setFilename] = useState("");
  const [modelName, setModelName] = useState("");
  const [modelType, setModelType] = useState<LegacyModelType>("IsolationForest");
  const [numericalFeatures, setNumericalFeatures] = useState<string[]>([]);
  const [categoricalFeatures, setCategoricalFeatures] = useState<string[]>([]);
  const [dateFeatures, setDateFeatures] = useState<string[]>([]);
  const [enableFeatureEngineering, setEnableFeatureEngineering] = useState(false);
  const [cardIdColumn, setCardIdColumn] = useState("");
  const [timestampColumn, setTimestampColumn] = useState("");
  const [amountColumn, setAmountColumn] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
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
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          onAuthFailure();
          return;
        }
        setError(err instanceof Error ? err.message : "Не удалось загрузить данные legacy-сервисов.");
      }
    };
    void load();
  }, [onAuthFailure, session]);

  useEffect(() => {
    if (!session || !filename) {
      setColumns([]);
      return;
    }
    const loadColumns = async () => {
      try {
        const nextColumns = await fetchLegacyColumns(session, filename);
        setColumns(nextColumns);
        setNumericalFeatures([]);
        setCategoricalFeatures([]);
        setDateFeatures([]);
        setCardIdColumn(nextColumns[0] || "");
        setTimestampColumn(nextColumns[0] || "");
        setAmountColumn(nextColumns[0] || "");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          onAuthFailure();
          return;
        }
        setError(err instanceof Error ? err.message : "Не удалось прочитать колонки файла.");
      }
    };
    void loadColumns();
  }, [filename, onAuthFailure, session]);

  const validate = (): string | null => {
    if (!filename) {
      return "Выберите файл для обучения.";
    }
    if (!modelName.trim()) {
      return "Укажите имя модели.";
    }
    if ([...numericalFeatures, ...categoricalFeatures, ...dateFeatures].length === 0) {
      return "Выберите хотя бы один признак.";
    }
    if (enableFeatureEngineering) {
      if (!cardIdColumn || !timestampColumn || !amountColumn) {
        return "Для feature engineering нужны card_id, timestamp и amount колонки.";
      }
      if (!dateFeatures.includes(timestampColumn)) {
        return "Timestamp-колонка должна быть отмечена как date feature.";
      }
    }
    return null;
  };

  const handleTrain = async () => {
    if (!session) {
      return;
    }
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload: LegacyTrainPayload = {
      filename,
      model_name: modelName.trim(),
      model_type: modelType,
      numerical_features: numericalFeatures,
      categorical_features: categoricalFeatures,
      date_features: dateFeatures,
      enable_feature_engineering: enableFeatureEngineering,
      card_id_column: enableFeatureEngineering ? cardIdColumn : null,
      timestamp_column: enableFeatureEngineering ? timestampColumn : null,
      amount_column: enableFeatureEngineering ? amountColumn : null,
    };

    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await trainLegacyAnomalyDetector(session, payload);
      setMessage(result.message);
      const nextModels = await fetchLegacyModels(session);
      setModels(nextModels.models);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка обучения модели.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Train Model
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Обучение anomaly detector</h2>
        <p className="mt-3 text-sm leading-7 text-smoke">
          Перенос логики страницы `2_Train_Model.py`: выбор файла, признаков, алгоритма и опционального feature engineering.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-semibold text-ink">
            Файл
            <select className="input-field mt-2" value={filename} onChange={(event) => setFilename(event.target.value)}>
              {files.length === 0 ? <option value="">Файлы не найдены</option> : null}
              {files.map((file) => (
                <option key={file} value={file}>
                  {file}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold text-ink">
            Имя модели
            <input
              className="input-field mt-2"
              value={modelName}
              onChange={(event) => setModelName(event.target.value)}
              placeholder="fraud_detector_v1"
            />
          </label>
          <label className="block text-sm font-semibold text-ink">
            Алгоритм
            <select className="input-field mt-2" value={modelType} onChange={(event) => setModelType(event.target.value as LegacyModelType)}>
              {modelTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-line bg-white/70 px-4 py-3 text-sm font-semibold text-ink">
            <input
              type="checkbox"
              checked={enableFeatureEngineering}
              onChange={(event) => setEnableFeatureEngineering(event.target.checked)}
            />
            Включить feature engineering
          </label>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {[
            ["Numerical", numericalFeatures, setNumericalFeatures],
            ["Categorical", categoricalFeatures, setCategoricalFeatures],
            ["Date", dateFeatures, setDateFeatures],
          ].map(([title, values, setter]) => (
            <div key={title as string} className="rounded-[24px] border border-line bg-white/70 p-4">
              <h3 className="text-lg font-semibold text-ink">{title as string}</h3>
              <div className="mt-4 max-h-72 space-y-2 overflow-y-auto pr-1">
                {columns.length === 0 ? <p className="text-sm text-smoke">Колонки не загружены.</p> : null}
                {columns.map((column) => (
                  <label key={`${title}-${column}`} className="flex items-center gap-3 rounded-2xl bg-panel px-3 py-2 text-sm text-smoke">
                    <input
                      type="checkbox"
                      checked={(values as string[]).includes(column)}
                      onChange={() => (setter as React.Dispatch<React.SetStateAction<string[]>>)((current) => toggleValue(current, column))}
                    />
                    {column}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        {enableFeatureEngineering ? (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {[
              ["Card ID", cardIdColumn, setCardIdColumn],
              ["Timestamp", timestampColumn, setTimestampColumn],
              ["Amount", amountColumn, setAmountColumn],
            ].map(([label, value, setter]) => (
              <label key={label as string} className="block text-sm font-semibold text-ink">
                {label as string}
                <select
                  className="input-field mt-2"
                  value={value as string}
                  onChange={(event) => (setter as React.Dispatch<React.SetStateAction<string>>)(event.target.value)}
                >
                  {columns.map((column) => (
                    <option key={`${label}-${column}`} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        ) : null}

        <button
          className="button-primary mt-6 w-full disabled:cursor-not-allowed disabled:opacity-50"
          disabled={isLoading}
          onClick={() => void handleTrain()}
        >
          {isLoading ? "Обучение..." : "Обучить модель"}
        </button>

        {message ? <p className="mt-5 rounded-2xl bg-white/70 p-4 text-sm text-ink">{message}</p> : null}
        {error ? <p className="mt-5 rounded-2xl bg-ink p-4 text-sm text-paper">{error}</p> : null}
      </section>

      <aside className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Model registry
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Сохраненные модели</h2>
        <div className="mt-6 space-y-3">
          {models.length === 0 ? <p className="text-sm leading-7 text-smoke">Модели пока не найдены.</p> : null}
          {models.map((model) => (
            <div key={model} className="rounded-[24px] border border-line bg-white/70 p-5">
              <p className="font-semibold text-ink">{model}</p>
              <p className="mt-2 text-sm text-smoke">Доступна на странице Prediction.</p>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
