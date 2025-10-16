from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Extra
import pandas as pd
import joblib
import json
import os

app = FastAPI(title="Prediction Service")

# --- Пути к моделям ---
MODEL_DIR = "/app/models"


# --- Динамическая модель Pydantic ---
# Позволяет принимать любые поля, которые придут от фронтенда
class DynamicPredictionRequest(BaseModel, extra=Extra.allow):
    model_filename: str


@app.post("/predict/")
async def predict(request: DynamicPredictionRequest):
    """
    Загружает указанную модель и делает прогноз на основе переданных данных.
    """
    model_path = os.path.join(MODEL_DIR, f"{request.model_filename}_model.joblib")
    config_path = os.path.join(MODEL_DIR, f"{request.model_filename}_config.json")

    if not os.path.exists(model_path) or not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Model or config not found")

    try:
        # Загружаем модель и конфигурацию
        model = joblib.load(model_path)
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Преобразуем входные данные Pydantic в словарь
        input_data_dict = request.model_dump()
        # Удаляем служебное поле с именем модели
        del input_data_dict['model_filename']

        # Создаем DataFrame для предсказания
        input_df = pd.DataFrame([input_data_dict])

        # Предсказание
        prediction = model.predict(input_df)
        prediction_proba = model.predict_proba(input_df)

        # Формируем ответ
        response = {
            # ИСПРАВЛЕНИЕ: Преобразуем типы NumPy в стандартные типы Python
            "prediction": str(prediction[0]),  # str() безопасно преобразует и числа, и текст
            "probabilities": {str(model.classes_[i]): float(prob) for i, prob in enumerate(prediction_proba[0])}
        }
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))