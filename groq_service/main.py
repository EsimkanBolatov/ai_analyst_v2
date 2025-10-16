from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import os
import time
from groq import Groq, GroqError
import json

app = FastAPI(title="Groq AI Analyst Service")

# --- КЛЮЧ API ---
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None


# --- Модели данных ---
class AnomalyExample(BaseModel):
    row_index: int
    reason: str
    data: dict


class AIAnalysisResponse(BaseModel):
    main_findings: str
    anomalies: list[AnomalyExample]
    recommendations: str
    feature_engineering_ideas: list[str] = []  # Добавим поле по умолчанию


class AnalyzeRequest(BaseModel):
    filename: str


# --- Путь к загруженным файлам ---
UPLOAD_DIR = "/app/uploads"


@app.post("/analyze/", response_model=AIAnalysisResponse)
async def analyze_dataset(request: AnalyzeRequest):
    if not client:
        raise HTTPException(status_code=500, detail="API-ключ Groq не настроен в сервисе.")

    file_path = f"/app/uploads/{request.filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден.")

    try:
        df = pd.read_csv(file_path, nrows=100)

        prompt = f"""
        Ты — элитный аналитик данных, специализирующийся на поиске мошенничества и аномалий в финансовых данных. Твоя задача — провести глубокий анализ предоставленного датасета.

        КОНТЕКСТ:
        Вот основная статистика по данным:
        {df.describe().to_string()}

        Вот несколько примеров строк:
        {df.head(10).to_string()}

        ЗАДАНИЯ:
        1.  **Основные выводы:** Сделай 1-2 главных вывода о природе этих данных.
        2.  **Поиск аномалий:** Найди 3-5 конкретных строк, которые выглядят наиболее подозрительно. Для каждой строки укажи ее индекс и подробно, но просто объясни, почему она является аномалией.
        3.  **Создание признаков:** Предложи 2-3 новые колонки (признака), которые можно было бы создать из существующих, чтобы улучшить обнаружение мошенничества. Опиши, как их рассчитать.
        4.  **Рекомендации:** Дай краткую рекомендацию по дальнейшим шагам для анализа этого датасета.

        ВАЖНО: Ответь строго в формате JSON, без каких-либо вводных слов или комментариев. Структура JSON должна быть такой:
        {{
          "main_findings": "...",
          "anomalies": [{{ "row_index": <индекс>, "reason": "..." }}],
          "feature_engineering_ideas": ["Идея 1...", "Идея 2..."],
          "recommendations": "..."
        }}
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",  # Актуальная модель
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        # Теперь команда json.loads будет работать
        response_content = json.loads(chat_completion.choices[0].message.content)

        # Дополняем ответ данными из датасета для аномалий
        for anomaly in response_content.get("anomalies", []):
            try:
                full_row_df = pd.read_csv(file_path, skiprows=lambda x: x != 0 and x != anomaly['row_index'] + 1,
                                          header=0 if anomaly['row_index'] == 0 else None)
                if not full_row_df.empty:
                    full_row_df.columns = df.columns
                    anomaly['data'] = full_row_df.iloc[0].to_dict()
            except Exception:
                anomaly['data'] = {}

        return response_content

    except GroqError as e:
        if e.status_code == 401:
            raise HTTPException(status_code=401, detail="Недействительный API-ключ. Проверьте ваш .env файл.")
        else:
            raise HTTPException(status_code=500, detail=f"Ошибка от API Groq: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервиса: {str(e)}")