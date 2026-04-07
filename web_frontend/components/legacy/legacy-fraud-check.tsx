"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import {
  addLegacyBlacklist,
  checkLegacyFraud,
} from "@/lib/legacy-api";
import type { LegacyFraudCheckResponse, LegacyFraudDataType } from "@/lib/legacy-types";
import { useSessionContext } from "@/lib/use-session-context";

const dataTypes: Array<{ value: LegacyFraudDataType; label: string; placeholder: string }> = [
  { value: "phone", label: "Телефон", placeholder: "+79991234567" },
  { value: "email", label: "Email", placeholder: "fraud@example.com" },
  { value: "url", label: "URL", placeholder: "https://bad-site-example.com/login" },
  { value: "text", label: "Текст", placeholder: "Сообщение для NLP-проверки" },
];

function deriveBlacklistPayload(dataType: LegacyFraudDataType, value: string) {
  if (dataType === "phone" || dataType === "email") {
    return { data_type: dataType, value };
  }
  if (dataType === "url") {
    try {
      return { data_type: "domain" as const, value: new URL(value).hostname };
    } catch {
      return { data_type: "domain" as const, value };
    }
  }
  return null;
}

export function LegacyFraudCheck() {
  const { session, onAuthFailure } = useSessionContext();
  const [dataType, setDataType] = useState<LegacyFraudDataType>("phone");
  const [value, setValue] = useState("");
  const [result, setResult] = useState<LegacyFraudCheckResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentType = dataTypes.find((item) => item.value === dataType) ?? dataTypes[0];
  const blacklistPayload = result ? deriveBlacklistPayload(dataType, value.trim()) : null;

  const handleCheck = async () => {
    if (!session || !value.trim()) {
      return;
    }
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await checkLegacyFraud(session, {
        data_type: dataType,
        value: value.trim(),
      });
      setResult(response);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка fraud-проверки.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddBlacklist = async () => {
    if (!session || !blacklistPayload) {
      return;
    }
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await addLegacyBlacklist(session, blacklistPayload);
      setMessage(response.message);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onAuthFailure();
        return;
      }
      setError(err instanceof Error ? err.message : "Не удалось добавить запись в blacklist.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Fraud Check
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Ручная risk-проверка</h2>
        <p className="mt-3 text-sm leading-7 text-smoke">
          Перенос страницы `4_Fraud_Check.py`: проверка телефона, email, URL или текста через старый fraud_check_service.
        </p>

        <div className="mt-6 space-y-4">
          <label className="block text-sm font-semibold text-ink">
            Тип данных
            <select className="input-field mt-2" value={dataType} onChange={(event) => setDataType(event.target.value as LegacyFraudDataType)}>
              {dataTypes.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-semibold text-ink">
            Значение
            {dataType === "text" ? (
              <textarea
                className="input-field mt-2 min-h-36"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder={currentType.placeholder}
              />
            ) : (
              <input
                className="input-field mt-2"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder={currentType.placeholder}
              />
            )}
          </label>
        </div>

        <button
          className="button-primary mt-5 w-full disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!value.trim() || isLoading}
          onClick={() => void handleCheck()}
        >
          {isLoading ? "Проверка..." : "Проверить"}
        </button>

        {blacklistPayload ? (
          <button
            className="button-secondary mt-3 w-full disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isLoading}
            onClick={() => void handleAddBlacklist()}
          >
            Добавить в blacklist: {blacklistPayload.value}
          </button>
        ) : null}

        {message ? <p className="mt-5 rounded-2xl bg-white/70 p-4 text-sm text-ink">{message}</p> : null}
        {error ? <p className="mt-5 rounded-2xl bg-ink p-4 text-sm text-paper">{error}</p> : null}
      </section>

      <section className="panel p-6">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
          Risk output
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-ink">Результат проверки</h2>

        {result ? (
          <div className="mt-6 grid gap-4">
            <div className="rounded-[28px] border border-line bg-white/70 p-6">
              <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
                Risk level
              </p>
              <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <p className="text-5xl font-semibold text-ink">{result.risk_level}</p>
                <p className="rounded-full bg-ink px-5 py-3 font-[family-name:var(--font-mono)] text-sm text-paper">
                  score {result.risk_score}
                </p>
              </div>
            </div>
            <div className="rounded-[28px] border border-line bg-white/70 p-6">
              <h3 className="text-xl font-semibold text-ink">Объяснение</h3>
              <p className="mt-3 text-sm leading-7 text-smoke">{result.explanation}</p>
            </div>
            <div className="rounded-[28px] border border-line bg-white/70 p-6">
              <h3 className="text-xl font-semibold text-ink">Input</h3>
              <p className="mt-3 break-words font-[family-name:var(--font-mono)] text-sm text-smoke">{result.input_value}</p>
            </div>
          </div>
        ) : (
          <div className="mt-6 rounded-[28px] border border-line bg-white/70 p-8 text-sm leading-7 text-smoke">
            Заполните форму слева и выполните проверку. Для URL старый Streamlit-сценарий добавлял в blacklist домен,
            поэтому новый интерфейс повторяет это поведение.
          </div>
        )}
      </section>
    </div>
  );
}
