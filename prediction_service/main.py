import pandas as pd
import joblib
import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, conlist
from typing import Dict, Any, List

app = FastAPI(title="Prediction Service")

# --- Директории ---
MODELS_DIR = "/app/models"
UPLOAD_DIR = "/app/uploads"

# --- Pydantic Модели ---
class DynamicRequest(BaseModel):
    model_name: str
    features: Dict[str, Any]

class ScoreFileRequest(BaseModel):
    model_name: str
    filename: str

class ScoreFileResponse(BaseModel):
    scores: List[float]


# --- (СКОПИРОВАНО ИЗ training_service) Вспомогательная функция обработки дат ---
def date_feature_extractor(df: pd.DataFrame, date_features: List[str]) -> (pd.DataFrame, List[str]):
    df_processed = df.copy()
    generated_features = []

    for col in date_features:
        if col not in df_processed.columns:
            print(f"Warning: Date feature column '{col}' not found in input data.")
            continue
        try:
            datetime_col = pd.to_datetime(df_processed[col])
            hour_col = f"{col}_hour"
            day_of_week_col = f"{col}_day_of_week"
            df_processed[hour_col] = datetime_col.dt.hour
            df_processed[day_of_week_col] = datetime_col.dt.dayofweek
            generated_features.extend([hour_col, day_of_week_col])
        except Exception as e:
            print(f"Warning: Could not process date feature {col}: {e}")

    return df_processed, generated_features

def generate_features(df: pd.DataFrame, config: Dict[str, Any]) -> (pd.DataFrame, List[str]):
    """
    Генерирует новые признаки: время суток, агрегация за час,
    время с последней транзакции, отклонение от среднего.
    ДОЛЖНА БЫТЬ ИДЕНТИЧНА ВЕРСИИ В training_service!
    """
    df_eng = df.copy()
    generated_eng_features = []

    card_col = config.get("card_id_column")
    ts_col = config.get("timestamp_column")
    amt_col = config.get("amount_column")

    required_cols = [col for col in [card_col, ts_col, amt_col] if col]
    if not all(col in df_eng.columns for col in required_cols):
        print("Warning: Недостаточно колонок для генерации признаков агрегации в prediction.")
        return df_eng, generated_eng_features

    try:
        # --- Преобразования ---
        df_eng[ts_col] = pd.to_datetime(df_eng[ts_col])
        df_eng = df_eng.sort_values(by=[card_col, ts_col]) # Сортировка важна для diff()

        # --- 1. Признаки времени суток ---
        hour_cols = [col for col in df_eng.columns if col.endswith('_hour')]
        if hour_cols:
            hour_col = hour_cols[0]
            df_eng['is_night'] = df_eng[hour_col].apply(lambda x: 1 if (x >= 22 or x <= 6) else 0)
            generated_eng_features.append('is_night')

        # --- 2. Агрегация за последний час (rolling) ---
        # ВНИМАНИЕ: Для /predict_or_score/ (одна строка) rolling window будет
        # Для /score_file/ (весь файл) это будет работать правильно.
        rolling_window_1h = df_eng.groupby(card_col, group_keys=False)[amt_col].rolling('1H', on=ts_col, closed='left')
        df_eng['card_tx_count_1h'] = rolling_window_1h.count().reset_index(level=0, drop=True).fillna(0).astype(int)
        generated_eng_features.append('card_tx_count_1h')
        df_eng['card_tx_amount_sum_1h'] = rolling_window_1h.sum().reset_index(level=0, drop=True).fillna(0)
        generated_eng_features.append('card_tx_amount_sum_1h')

        # --- 3. Время с последней транзакции по карте ---
        df_eng['time_since_last_tx_card'] = df_eng.groupby(card_col)[ts_col].diff().dt.total_seconds()
        df_eng['time_since_last_tx_card'] = df_eng['time_since_last_tx_card'].fillna(86400)
        generated_eng_features.append('time_since_last_tx_card')

        # --- 4. Отклонение от среднего по карте за окно (24 часа) ---
        rolling_window_24h_avg = df_eng.groupby(card_col, group_keys=False)[amt_col].rolling('24H', on=ts_col, closed='left').mean()
        df_eng['card_tx_amount_avg_24h'] = rolling_window_24h_avg.reset_index(level=0, drop=True)
        fill_value_avg = df_eng[amt_col].mean() if not df_eng.empty else 0
        df_eng['card_tx_amount_avg_24h'] = df_eng['card_tx_amount_avg_24h'].fillna(fill_value_avg)

        df_eng['amount_deviation_from_card_avg'] = df_eng[amt_col] - df_eng['card_tx_amount_avg_24h']
        generated_eng_features.append('amount_deviation_from_card_avg')

        df_eng = df_eng.drop(columns=['card_tx_amount_avg_24h'], errors='ignore')

        print(f"Сгенерированы признаки (prediction): {generated_eng_features}")

    except Exception as e:
        print(f"Ошибка во время генерации признаков (prediction): {e}")
        import traceback
        traceback.print_exc()
        return df.copy(), []

    return df_eng, generated_eng_features

# --- Вспомогательная функция загрузки модели и конфига ---
def load_model_and_config(model_name: str):
    model_path = os.path.join(MODELS_DIR, f"{model_name}.joblib")
    config_path = os.path.join(MODELS_DIR, f"{model_name}.json")
    if not os.path.exists(model_path) or not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail=f"Модель '{model_name}' или ее конфиг не найдены.")
    try:
        model = joblib.load(model_path)
        with open(config_path, 'r') as f:
            config = json.load(f)
        return model, config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке модели: {e}")


# --- Эндпоинты ---

@app.post("/predict_or_score/")
async def predict_or_score(request: DynamicRequest):
    model, config = load_model_and_config(request.model_name)
    input_df = pd.DataFrame([request.features])

    # 1. Обработка дат
    date_features = config.get('date_features', [])
    if date_features:
        input_df, _ = date_feature_extractor(input_df, date_features)

    # 2. Генерация признаков
    feature_engineering_config = config.get('feature_engineering_config', {})
    if feature_engineering_config:
        print("Warning: Feature Engineering для одной строки может быть неточным без истории.")
        input_df, generated_eng_features = generate_features(input_df, feature_engineering_config)

    # 3. Определение типа модели
    model_type = config.get('model_type', 'classification')

    # 4. Предсказание/Оценка
    try:
        if model_type == 'anomaly_detection':
            # Логика decision_function остается прежней
            scores = model.decision_function(input_df)
            anomaly_score = scores[0]
            is_anomaly = anomaly_score < 0
            return {
                "model_type": "anomaly_detection",
                "anomaly_score": float(anomaly_score),
                "is_anomaly_predicted": bool(is_anomaly)
            }
        else:
            prediction = model.predict(input_df)
            probabilities = {}
            if hasattr(model, "predict_proba"):
                try:
                     probs = model.predict_proba(input_df)[0]
                     classes = model.named_steps.get('classifier', model).classes_
                     probabilities = dict(zip(classes, probs))
                except Exception as prob_e:
                     print(f"Warning: Could not get probabilities: {prob_e}")
            return {
                "model_type": "classification",
                "prediction": prediction[0],
                "probabilities": probabilities
            }
    except KeyError as e:
         # Эта ошибка может возникать чаще, если FE не сработал корректно
         raise HTTPException(status_code=400, detail=f"Ошибка: Отсутствует необходимый признак '{e}' во входных данных после обработки.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при предсказании/оценке: {e}")

@app.post("/score_file/", response_model=ScoreFileResponse)
async def score_file(request: ScoreFileRequest):
    model, config = load_model_and_config(request.model_name)
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Файл данных '{request.filename}' не найден.")

    model_type = config.get('model_type', 'classification')
    if model_type != 'anomaly_detection':
        raise HTTPException(status_code=400, detail=f"Модель '{request.model_name}' не является моделью обнаружения аномалий.")

    try:
        df = pd.read_csv(file_path)

        # 2. Обрабатываем даты
        date_features = config.get('date_features', [])
        if date_features:
            df, _ = date_feature_extractor(df, date_features)

        # 3. Генерируем признаки
        feature_engineering_config = config.get('feature_engineering_config', {})
        if feature_engineering_config:
             df, generated_eng_features = generate_features(df, feature_engineering_config)
             # Важно: Убедиться, что df теперь содержит новые колонки

        # 4. Получаем оценки для ВСЕХ строк
        all_scores = model.decision_function(df)

        scores_list = [float(score) for score in all_scores]

        return ScoreFileResponse(scores=scores_list)

    except KeyError as e:
         raise HTTPException(status_code=400, detail=f"Ошибка: Не найдена необходимая колонка '{e}' для применения модели.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при пакетной обработке файла: {e}")