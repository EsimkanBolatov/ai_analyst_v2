#groq_service/main
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field  # Добавляем Field
import pandas as pd
import os
from groq import Groq, GroqError
import json
from typing import List, Dict, Any  # Добавляем Dict, Any

app = FastAPI(title="Groq AI Analyst Service")

# --- КЛЮЧ API ---
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None


# --- Модели данных ---
class AnomalyPlotData(BaseModel):
    transaction_amount_kzt: float | None = None
    transaction_hour: int | None = None
    mcc_category: str | None = None


class AnomalyExample(BaseModel):
    row_index: int
    reason: str
    data: Dict[str, Any]
    plot_data: AnomalyPlotData | None = None


# Для хранения статистик распределения
class DistributionStats(BaseModel):
    min_val: float | None = None
    p25: float | None = None  # 25-й перцентиль
    median: float | None = None  # 50-й перцентиль
    p75: float | None = None  # 75-й перцентиль
    max_val: float | None = None
    mean_val: float | None = None
    count: int | None = None


class AIAnalysisResponse(BaseModel):
    main_findings: str
    anomalies: list[AnomalyExample]
    recommendations: str
    feature_engineering_ideas: list[str] = []
    # Статистики для гистограммы
    amount_distribution_stats: DistributionStats | None = None


class AnalyzeRequest(BaseModel):
    filename: str


# --- Модели для чата ---
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    filename: str
    chat_history: List[ChatMessage]


class ChatResponse(BaseModel):
    role: str
    content: str


# --- Путь к файлам ---
UPLOAD_DIR = "/app/uploads"

# --- Вспомогательные функции get_chat_context_prompt  ---
def get_chat_context_prompt(dataframe_head: str) -> str:
    return f"""
        Ты продолжаешь диалог с аналитиком данных.
        Для контекста, вот первые несколько строк данных, которые вы обсуждаете:
        ---
        {dataframe_head}
        ---
        Учитывай этот контекст, отвечая на следующий вопрос пользователя. Будь кратким и по делу.
    """


# --- Эндпоинт /analyze/  ---
@app.post("/analyze/", response_model=AIAnalysisResponse)
async def analyze_dataset(request: AnalyzeRequest):
    if not client:
        raise HTTPException(status_code=500, detail="API-ключ Groq не настроен в сервисе.")

    file_path = f"/app/uploads/{request.filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден.")

    try:
        # Читаем больше строк, чтобы у Groq было больше контекста
        df = pd.read_csv(file_path, nrows=100)

        # Попытаемся извлечь час, если есть timestamp
        ts_col = next((col for col in df.columns if 'timestamp' in col.lower()), None)
        hour_col_name = None
        if ts_col:
            try:
                df[ts_col] = pd.to_datetime(df[ts_col])
                hour_col_name = f"{ts_col}_hour"
                df[hour_col_name] = df[ts_col].dt.hour
            except Exception:
                hour_col_name = None

        prompt = f"""
                Ты — опытный финансовый аналитик (фрод-анализ). Проанализируй фрагмент датасета транзакций.

                КОНТЕКСТ ДАННЫХ (первые строки):
                {df.head(15).to_string()}

                СТАТИСТИКА (по первым 100 строкам):
                {df.describe(include='all').to_string()}

                ЗАДАНИЯ:
                1.  **Основные выводы:** Кратко опиши данные и важные поля для фрод-анализа.
                2.  **Распределение Сумм:** Рассчитай и предоставь основные статистики для колонки `transaction_amount_kzt` (если она есть) по первым 100 строкам: `min_val`, `p25` (25-й перцентиль), `median` (50-й перцентиль), `p75` (75-й перцентиль), `max_val`, `mean_val` (среднее), `count` (количество непустых значений). Если колонки нет, все значения должны быть null.
                3.  **Поиск аномалий:** Найди 3-5 подозрительных строк. Для каждой укажи:
                    * `row_index`: Индекс строки (из данных).
                    * `reason`: Четкое объяснение подозрительности.
                    * `plot_data`: Объект JSON с ключевыми значениями для ГРАФИКА:
                        * `transaction_amount_kzt`: Значение суммы (если есть).
                        * `transaction_hour`: Значение часа (если колонка {hour_col_name} есть).
                        * `mcc_category`: Значение категории (если есть).
                      Если какого-то поля нет, ставь null.
                4.  **Создание признаков:** Предложи 2-3 конкретные идеи новых признаков.
                5.  **Рекомендации:** Краткие шаги для построения ML-модели.

                ВАЖНО: Ответь СТРОГО в формате JSON. Структура:
                {{
                  "main_findings": "...",
                  "amount_distribution_stats": {{
                      "min_val": <число_или_null>,
                      "p25": <число_или_null>,
                      "median": <число_или_null>,
                      "p75": <число_или_null>,
                      "max_val": <число_или_null>,
                      "mean_val": <число_или_null>,
                      "count": <число_или_null>
                  }},
                  "anomalies": [
                      {{
                        "row_index": <индекс>,
                        "reason": "...",
                        "plot_data": {{...}}
                      }}
                  ],
                  "feature_engineering_ideas": ["...", "..."],
                  "recommendations": "..."
                }}
                """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        response_content = json.loads(chat_completion.choices[0].message.content)

        # Дополняем ответ ПОЛНЫМИ данными строки для аномалий
        anomalies_list = response_content.get("anomalies", [])
        if anomalies_list:
            try:
                full_df = pd.read_csv(file_path)
                for anomaly in anomalies_list:
                    idx = anomaly.get("row_index")
                    if idx is not None and 0 <= idx < len(full_df):
                        anomaly['data'] = {k: v.item() if hasattr(v, 'item') else v for k, v in
                                           full_df.iloc[idx].to_dict().items()}
                    else:
                        anomaly['data'] = {}
            except Exception as read_err:
                print(f"Ошибка при чтении полного файла для аномалий: {read_err}")
                for anomaly in anomalies_list:
                    anomaly['data'] = {}

        # Дополнительная валидация перед возвратом (на случай если Groq ошибся)
        try:
            validated_response = AIAnalysisResponse(**response_content)
            return validated_response
        except Exception as pydantic_err:
            print(f"Ошибка валидации Pydantic: {pydantic_err}")
            return response_content


    except GroqError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка от API Groq: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервиса: {str(e)}")


# --- Эндпоинт /chat/  ---
@app.post("/chat/", response_model=ChatResponse)
async def chat_with_analyst(request: ChatRequest):
    if not client: raise HTTPException(status_code=500, detail="API-ключ Groq не настроен.")
    file_path = f"/app/uploads/{request.filename}"
    if not os.path.exists(file_path): raise HTTPException(status_code=404,
                                                          detail=f"Файл '{request.filename}' не найден.")
    try:
        df_head = pd.read_csv(file_path, nrows=20)
        df_head_str = df_head.to_string()
        messages_for_api = [
            {"role": "system", "content": get_chat_context_prompt(df_head_str)},
            *[msg.model_dump() for msg in request.chat_history]
        ]
        chat_completion = client.chat.completions.create(messages=messages_for_api, model="llama-3.1-8b-instant",
                                                         temperature=0.3)
        response_content = chat_completion.choices[0].message.content
        return ChatResponse(role="assistant", content=response_content)
    except GroqError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка от API Groq: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервиса в чате: {str(e)}")