from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

app = FastAPI(title="Anomaly Detection Training Service")

# --- Пути ---
UPLOAD_DIR = "/app/uploads"
MODEL_DIR = "/app/models"
os.makedirs(MODEL_DIR, exist_ok=True)

# --- Модель входных данных ---
class TrainingRequest(BaseModel):
    filename: str
    #target_column: str
    numerical_features: list[str]
    categorical_features: list[str]
    date_features: list[str]

@app.post("/train/")
async def train_model(request: TrainingRequest):
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        df = pd.read_csv(file_path)
        df_processed = df.copy() # Копируем для обработки

        # --- ОБРАБОТКА ДАТ ---
        generated_date_features = [] # Будем хранить имена новых колонок
        for col in request.date_features:
            try:
                # Преобразуем колонку в datetime
                df_processed[col] = pd.to_datetime(df_processed[col])
                # Создаем новые числовые признаки
                df_processed[f'{col}_hour'] = df_processed[col].dt.hour
                df_processed[f'{col}_dayofweek'] = df_processed[col].dt.dayofweek
                df_processed[f'{col}_month'] = df_processed[col].dt.month
                df_processed[f'{col}_day'] = df_processed[col].dt.day
                # Добавляем новые признаки в список для дальнейшей обработки
                generated_date_features.extend([f'{col}_hour', f'{col}_dayofweek', f'{col}_month', f'{col}_day'])
            except Exception as e:
                print(f"Предупреждение: Не удалось обработать колонку даты '{col}': {e}")
                # Если колонка не парсится как дата, просто пропускаем ее

        # Удаляем исходные колонки с датами, они больше не нужны
        df_processed = df_processed.drop(columns=request.date_features, errors='ignore')

        final_numerical_features = request.numerical_features + generated_date_features
        final_categorical_features = request.categorical_features

        features_to_use = final_numerical_features + final_categorical_features
        if not features_to_use:
             raise HTTPException(status_code=400, detail="Необходимо выбрать хотя бы один признак.")

        X = df_processed[features_to_use]
        y = df_processed[request.target_column]

        # --- Конвейер предобработки ---
        numeric_transformer = StandardScaler()
        categorical_transformer = OneHotEncoder(handle_unknown='ignore')

        transformers = []
        # Важно: используем final_numerical_features
        if final_numerical_features:
            transformers.append(('num', numeric_transformer, final_numerical_features))
        if final_categorical_features:
            transformers.append(('cat', categorical_transformer, final_categorical_features))

        if not transformers:
             raise HTTPException(status_code=400, detail="Ошибка в конфигурации трансформеров.")

        preprocessor = ColumnTransformer(transformers=transformers)

        # --- Обучение ---
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', RandomForestClassifier(random_state=42)) # Пока только RF
        ])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        model_pipeline.fit(X_train, y_train)
        report = classification_report(y_test, model_pipeline.predict(X_test), output_dict=True)

        # --- Сохранение ---
        model_path = os.path.join(MODEL_DIR, f"{request.filename}_model.joblib")
        config_path = os.path.join(MODEL_DIR, f"{request.filename}_config.json")
        joblib.dump(model_pipeline, model_path)

        # ВАЖНО: Сохраняем информацию о том, какие колонки были датами
        config = {
            'target': request.target_column,
            'numerical_features': request.numerical_features, # Исходные числовые
            'categorical_features': request.categorical_features,
            'date_features': request.date_features, # Список колонок-дат
            'categorical_values': {col: df[col].astype(str).unique().tolist() for col in request.categorical_features}
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

        return {"status": "success", "message": "Model trained successfully", "report": report}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: Колонка '{e}' не найдена в датасете.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервиса обучения: {str(e)}")

@app.post("/train_anomaly_detector/")
async def train_anomaly_detector(request: TrainingRequest):
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        df = pd.read_csv(file_path)
        df_processed = df.copy()

        # --- ОБРАБОТКА ДАТ ---
        generated_date_features = []
        for col in request.date_features:
            try:
                df_processed[col] = pd.to_datetime(df_processed[col])
                df_processed[f'{col}_hour'] = df_processed[col].dt.hour
                df_processed[f'{col}_dayofweek'] = df_processed[col].dt.dayofweek
                df_processed[f'{col}_month'] = df_processed[col].dt.month
                df_processed[f'{col}_day'] = df_processed[col].dt.day
                generated_date_features.extend([f'{col}_hour', f'{col}_dayofweek', f'{col}_month', f'{col}_day'])
            except Exception as e:
                print(f"Предупреждение: Не удалось обработать колонку даты '{col}': {e}")

        df_processed = df_processed.drop(columns=request.date_features, errors='ignore')

        # --- ПОДГОТОВКА ПРИЗНАКОВ ---
        final_numerical_features = request.numerical_features + generated_date_features
        final_categorical_features = request.categorical_features
        features_to_use = final_numerical_features + final_categorical_features
        if not features_to_use:
             raise HTTPException(status_code=400, detail="Необходимо выбрать хотя бы один признак.")

        # Для Isolation Forest важно иметь данные только в числовом виде
        X = df_processed[features_to_use]

        # --- Конвейер предобработки (только числовые + OHE для категориальных) ---
        numeric_transformer = StandardScaler()
        # Важно: handle_unknown='ignore', sparse_output=False (Isolation Forest может не любить разреженные матрицы)
        categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)

        transformers = []
        if final_numerical_features:
            transformers.append(('num', numeric_transformer, final_numerical_features))
        if final_categorical_features:
            transformers.append(('cat', categorical_transformer, final_categorical_features))

        if not transformers:
             raise HTTPException(status_code=400, detail="Ошибка в конфигурации трансформеров.")

        preprocessor = ColumnTransformer(transformers=transformers)

        # --- СОЗДАНИЕ ПАЙПЛАЙНА С ISOLATION FOREST ---
        # contamination='auto' - модель сама попробует определить долю аномалий
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('detector', IsolationForest(contamination='auto', random_state=42))
        ])

        # --- Обучение (без X_test, y_test) ---
        model_pipeline.fit(X) # Обучение без учителя происходит на всех данных

        # --- Сохранение модели и конфига ---
        model_name_base = f"{request.filename}_anomaly" # Добавим суффикс
        model_path = os.path.join(MODEL_DIR, f"{model_name_base}_model.joblib")
        config_path = os.path.join(MODEL_DIR, f"{model_name_base}_config.json")
        joblib.dump(model_pipeline, model_path)

        # Сохраняем конфиг, указывая тип модели
        config = {
            'model_type': 'anomaly_detection', # <-- ВАЖНО: Указываем тип
            'numerical_features': request.numerical_features,
            'categorical_features': request.categorical_features,
            'date_features': request.date_features,
            'categorical_values': {col: df[col].astype(str).unique().tolist() for col in request.categorical_features}
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

        # Оценка качества для unsupervised моделей сложна, возвращаем только успех
        return {"status": "success", "message": "Anomaly detection model trained successfully"}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: Колонка '{e}' не найдена в датасете.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервиса обучения: {str(e)}")

@app.get("/models/")
async def list_models():
    """
    Сканирует папку с моделями и возвращает список доступных моделей.
    """
    try:
        # Ищем файлы конфигурации, чтобы понять, какие модели существуют
        configs = [f for f in os.listdir(MODEL_DIR) if f.endswith('_config.json')]
        # Извлекаем "базовые" имена файлов
        model_names = [f.replace('_config.json', '') for f in configs]
        return {"models": model_names}
    except FileNotFoundError:
        return {"models": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model_name}/config")
async def get_model_config(model_name: str):
    """
    Возвращает JSON-конфигурацию для выбранной модели.
    """
    config_path = os.path.join(MODEL_DIR, f"{model_name}_config.json")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Config file not found")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))