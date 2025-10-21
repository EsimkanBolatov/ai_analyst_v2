#prediction_service\main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Extra
import pandas as pd
import joblib
import json
import os
import datetime

app = FastAPI(title="Prediction & Anomaly Scoring Service")

# --- Пути ---
MODEL_DIR = "/app/models"

class DynamicRequest(BaseModel, extra=Extra.allow):
    model_filename: str # Базовое имя файла модели (без _model.joblib)

@app.post("/predict_or_score/") # <-- Переименовали эндпоинт
async def predict_or_score(request: DynamicRequest):
    model_name_base = request.model_filename
    model_path = os.path.join(MODEL_DIR, f"{model_name_base}_model.joblib")
    config_path = os.path.join(MODEL_DIR, f"{model_name_base}_config.json")

    if not os.path.exists(model_path) or not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Model or config not found")

    try:
        model = joblib.load(model_path)
        with open(config_path, 'r') as f:
            config = json.load(f)

        input_data_dict = request.model_dump()
        del input_data_dict['model_filename']
        input_df = pd.DataFrame([input_data_dict])

        # --- Обработка дат (остается такой же) ---
        date_features = config.get('date_features', [])
        for col in date_features:
            try:
                input_df[col] = pd.to_datetime(input_df[col])
                input_df[f'{col}_hour'] = input_df[col].dt.hour
                input_df[f'{col}_dayofweek'] = input_df[col].dt.dayofweek
                input_df[f'{col}_month'] = input_df[col].dt.month
                input_df[f'{col}_day'] = input_df[col].dt.day
            except Exception:
                 input_df[f'{col}_hour'] = 0
                 input_df[f'{col}_dayofweek'] = 0
                 input_df[f'{col}_month'] = 0
                 input_df[f'{col}_day'] = 0
        input_df = input_df.drop(columns=date_features, errors='ignore')

        # --- Определяем тип модели и делаем прогноз/оценку ---
        model_type = config.get('model_type', 'classification') # По умолчанию - классификация

        if model_type == 'anomaly_detection':
            # Для Isolation Forest используем decision_function
            # Чем меньше значение, тем "нормальнее" точка. Отрицательные - аномалии.
            scores = model.decision_function(input_df)
            anomaly_score = scores[0]
            # Можно добавить флаг на основе стандартного порога 0
            is_anomaly = anomaly_score < 0
            response = {
                "model_type": "anomaly_detection",
                "anomaly_score": float(anomaly_score),
                "is_anomaly_predicted": bool(is_anomaly) # Предсказание: Аномалия (True) или Норма (False)
            }
        else: # Логика для классификации (старая)
            prediction = model.predict(input_df)
            prediction_proba = model.predict_proba(input_df)
            response = {
                "model_type": "classification",
                "prediction": str(prediction[0]),
                "probabilities": {str(model.classes_[i]): float(prob) for i, prob in enumerate(prediction_proba[0])}
            }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при прогнозировании/оценке: {str(e)}")