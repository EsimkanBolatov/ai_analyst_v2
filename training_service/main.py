import pandas as pd
import joblib
import json
import os
import io
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from sqlalchemy import create_engine, Column, String, LargeBinary, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import requests

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

app = FastAPI(title="Model Training Service")

# --- Директории ---
UPLOAD_DIR = "/app/uploads"
MODELS_DIR = "/app/models"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8000")

# --- Хранилище моделей ---
# Render services do not share a local filesystem.
# If DATABASE_URL is set, models/configs are stored in Postgres (Neon).
DATABASE_URL = os.getenv("DATABASE_URL")
USE_DB_STORAGE = bool(DATABASE_URL)

Base = declarative_base()


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    model_name = Column(String, primary_key=True, index=True)
    model_blob = Column(LargeBinary, nullable=False)
    config_json = Column(Text, nullable=False)


engine = create_engine(DATABASE_URL, pool_pre_ping=True) if USE_DB_STORAGE else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if USE_DB_STORAGE else None


@app.on_event("startup")
def on_startup():
    if USE_DB_STORAGE:
        Base.metadata.create_all(bind=engine)


def _save_model_artifact(model_name: str, model_pipeline: Pipeline, config_json: str) -> None:
    if not USE_DB_STORAGE:
        return
    buffer = io.BytesIO()
    joblib.dump(model_pipeline, buffer)
    model_bytes = buffer.getvalue()

    db = SessionLocal()
    try:
        artifact = db.get(ModelArtifact, model_name)
        if artifact is None:
            artifact = ModelArtifact(
                model_name=model_name,
                model_blob=model_bytes,
                config_json=config_json,
            )
            db.add(artifact)
        else:
            artifact.model_blob = model_bytes
            artifact.config_json = config_json
        db.commit()
    finally:
        db.close()


def _ensure_uploaded_file(filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return file_path

    try:
        response = requests.get(f"{FILE_SERVICE_URL}/download/{filename}", timeout=120, stream=True)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Файл '{filename}' не найден.")
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return file_path
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Не удалось получить файл '{filename}' из file_service: {e}")


# --- Pydantic Модели ---
class TrainingRequest(BaseModel):
    filename: str
    model_name: str
    model_type: str = Field(
        "IsolationForest",
        description="Тип модели: IsolationForest, LocalOutlierFactor или OneClassSVM"
    )
    numerical_features: List[str]
    categorical_features: List[str]
    date_features: List[str] = []
    enable_feature_engineering: bool = Field(False, description="Включить Feature Engineering")
    card_id_column: str | None = Field(None)
    timestamp_column: str | None = Field(None)
    amount_column: str | None = Field(None)


class ModelConfig(BaseModel):
    model_type: str
    algorithm_class: str  # Добавлено ранее
    numerical_features: List[str]
    categorical_features: List[str]
    date_features: List[str]
    categorical_values: Dict[str, List[Any]]
    generated_date_features: List[str]
    generated_eng_features: List[str]
    feature_engineering_config: Dict[str, Any]


# --- Вспомогательные функции date_feature_extractor ---
def date_feature_extractor(df: pd.DataFrame, date_features: List[str]) -> (pd.DataFrame, List[str]):
    df_processed = df.copy()
    generated_features = []
    for col in date_features:
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


# --- Автоматическое создание признаков ---
def generate_features(df: pd.DataFrame, config: Dict[str, Any]) -> (pd.DataFrame, List[str]):
    df_eng = df.copy()
    generated_eng_features = []

    card_col = config.get("card_id_column")
    ts_col = config.get("timestamp_column")
    amt_col = config.get("amount_column")

    required_cols_present = all(col in df_eng.columns for col in [card_col, ts_col, amt_col] if col)

    if not required_cols_present:
        print("Warning: Недостаточно колонок для Feature Engineering.")
        return df_eng, generated_eng_features

    try:
        # --- Преобразования ---
        df_eng[ts_col] = pd.to_datetime(df_eng[ts_col])
        df_eng = df_eng.sort_values(by=[card_col, ts_col])  # Сортировка обязательна!

        # --- 1. Признаки времени суток ---
        hour_cols = [col for col in df_eng.columns if col.endswith('_hour')]
        if hour_cols:
            hour_col = hour_cols[0]
            df_eng['is_night'] = df_eng[hour_col].apply(lambda x: 1 if (x >= 22 or x <= 6) else 0)
            generated_eng_features.append('is_night')

        # --- 2. Агрегация за последний час (rolling) ---
        rolling_window_1h = df_eng.groupby(card_col, group_keys=False)[amt_col].rolling('1H', on=ts_col, closed='left')
        df_eng['card_tx_count_1h'] = rolling_window_1h.count().reset_index(level=0, drop=True).fillna(0).astype(int)
        generated_eng_features.append('card_tx_count_1h')
        df_eng['card_tx_amount_sum_1h'] = rolling_window_1h.sum().reset_index(level=0, drop=True).fillna(0)
        generated_eng_features.append('card_tx_amount_sum_1h')

        # --- 3. Время с последней транзакции по карте ---
        df_eng['time_since_last_tx_card'] = df_eng.groupby(card_col)[ts_col].diff().dt.total_seconds()
        df_eng['time_since_last_tx_card'] = df_eng['time_since_last_tx_card'].fillna(86400)
        generated_eng_features.append('time_since_last_tx_card')

        # --- 4. Отклонение от среднего по карте за окно ---
        rolling_window_24h_avg = df_eng.groupby(card_col, group_keys=False)[amt_col].rolling(
            '24H', on=ts_col, closed='left'
        ).mean()
        df_eng['card_tx_amount_avg_24h'] = rolling_window_24h_avg.reset_index(level=0, drop=True)
        df_eng['card_tx_amount_avg_24h'] = df_eng['card_tx_amount_avg_24h'].fillna(df_eng[amt_col].mean())

        # Рассчитываем отклонение
        df_eng['amount_deviation_from_card_avg'] = df_eng[amt_col] - df_eng['card_tx_amount_avg_24h']
        generated_eng_features.append('amount_deviation_from_card_avg')

        # Удаляем вспомогательную колонку среднего
        df_eng = df_eng.drop(columns=['card_tx_amount_avg_24h'], errors='ignore')

        print(f"Сгенерированы признаки (training): {generated_eng_features}")

    except Exception as e:
        print(f"Ошибка во время генерации признаков (training): {e}")
        import traceback
        traceback.print_exc()
        return df.copy(), []

    return df_eng, generated_eng_features


# --- Эндпоинт обучения ---
@app.post("/train_anomaly_detector/")
async def train_anomaly_detector(request: TrainingRequest):
    file_path = _ensure_uploaded_file(request.filename)

    try:
        df = pd.read_csv(file_path)

        # 1. Обработка дат
        df_processed, generated_date_features = date_feature_extractor(df, request.date_features)

        # 2. Генерация признаков
        generated_eng_features = []
        feature_engineering_config = {}
        if request.enable_feature_engineering:
            if not all([request.card_id_column, request.timestamp_column, request.amount_column]):
                raise HTTPException(status_code=400,
                                    detail="Для Feature Engineering необходимо указать колонки card_id, timestamp и amount.")
            feature_engineering_config = {
                "card_id_column": request.card_id_column,
                "timestamp_column": request.timestamp_column,
                "amount_column": request.amount_column
            }
            df_processed, generated_eng_features = generate_features(df_processed, feature_engineering_config)

        # Обновляем списки фичей
        final_numerical_features = request.numerical_features + generated_date_features + generated_eng_features
        final_categorical_features = request.categorical_features
        final_numerical_features = sorted(list(set(final_numerical_features)))
        final_categorical_features = sorted(list(set(final_categorical_features)))

        # 3. Сбор уникальных категориальных значений
        categorical_values = {}
        for col in final_categorical_features:
            if col in df_processed.columns:
                categorical_values[col] = df_processed[col].astype(str).unique().tolist()
            else:
                print(f"Warning: Категориальная колонка {col} не найдена после обработки.")

        # 4. Создание препроцессора
        numeric_transformer = Pipeline(steps=[('scaler', StandardScaler())])
        categorical_transformer = Pipeline(steps=[('onehot', OneHotEncoder(handle_unknown='ignore'))])
        actual_numerical = [f for f in final_numerical_features if f in df_processed.columns]
        actual_categorical = [f for f in final_categorical_features if f in df_processed.columns]
        transformers = []
        if actual_numerical:
            transformers.append(('num', numeric_transformer, actual_numerical))
        if actual_categorical:
            transformers.append(('cat', categorical_transformer, actual_categorical))
        if not transformers:
            raise HTTPException(status_code=400, detail="Не удалось определить признаки для препроцессора.")
        preprocessor = ColumnTransformer(transformers=transformers, remainder='drop')

        # 5. Выбор и инициализация модели
        if request.model_type == "IsolationForest":
            model_instance = IsolationForest(contamination='auto', random_state=42)
        elif request.model_type == "LocalOutlierFactor":
            model_instance = LocalOutlierFactor(novelty=True, contamination='auto')
        elif request.model_type == "OneClassSVM":
            model_instance = OneClassSVM(nu=0.05, kernel="rbf", gamma='scale')
        else:
            raise HTTPException(status_code=400, detail=f"Неизвестный тип модели: {request.model_type}")

        # 6. Создание и обучение полного пайплайна
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('detector', model_instance)
        ])
        features_to_train_on = actual_numerical + actual_categorical
        if not features_to_train_on:
            raise HTTPException(status_code=400, detail="Нет признаков для обучения после обработки.")
        X = df_processed[features_to_train_on]
        model_pipeline.fit(X)

        # 7. Сохранение модели и конфига
        if not USE_DB_STORAGE:
            model_path = os.path.join(MODELS_DIR, f"{request.model_name}.joblib")
            config_path = os.path.join(MODELS_DIR, f"{request.model_name}.json")
            joblib.dump(model_pipeline, model_path)
        config_data = ModelConfig(
            model_type='anomaly_detection',
            algorithm_class=request.model_type,
            numerical_features=request.numerical_features,
            categorical_features=request.categorical_features,
            date_features=request.date_features,
            categorical_values=categorical_values,
            generated_date_features=generated_date_features,
            generated_eng_features=generated_eng_features,
            feature_engineering_config=feature_engineering_config
        )
        config_json = config_data.model_dump_json(indent=4)

        if USE_DB_STORAGE:
            _save_model_artifact(request.model_name, model_pipeline, config_json)
        else:
            with open(config_path, 'w') as f:
                f.write(config_json)

        return {"message": f"Модель '{request.model_name}' ({request.model_type}) успешно обучена и сохранена."}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: Не найдена необходимая колонка '{e}' в датасете.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при обучении: {str(e)}")


# --- Эндпоинты /models/ и /models/{model_name}/config ---
@app.get("/models/", response_model=Dict[str, List[str]])
async def get_models():
    try:
        if USE_DB_STORAGE:
            db = SessionLocal()
            try:
                model_names = [row[0] for row in db.query(ModelArtifact.model_name).all()]
            finally:
                db.close()
        else:
            all_files = os.listdir(MODELS_DIR)
            model_names = [f.split('.joblib')[0] for f in all_files if f.endswith('.joblib')]
        return {"models": model_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось прочитать список моделей: {e}")


@app.get("/models/{model_name}/config")
async def get_model_config(model_name: str):
    try:
        if USE_DB_STORAGE:
            db = SessionLocal()
            try:
                artifact = db.get(ModelArtifact, model_name)
                if artifact is None:
                    raise HTTPException(status_code=404, detail=f"Конфиг для модели '{model_name}' не найден.")
                config = json.loads(artifact.config_json)
            finally:
                db.close()
        else:
            config_path = os.path.join(MODELS_DIR, f"{model_name}.json")
            if not os.path.exists(config_path):
                raise HTTPException(status_code=404, detail=f"Конфиг для модели '{model_name}' не найден.")
            with open(config_path, 'r') as f:
                config = json.load(f)
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении конфига: {e}")


