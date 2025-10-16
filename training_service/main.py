from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

app = FastAPI(title="Model Training Service")

# --- Пути к данным и моделям ---
UPLOAD_DIR = "/app/uploads"
MODEL_DIR = "/app/models"
os.makedirs(MODEL_DIR, exist_ok=True)


# --- Модель входных данных для запроса ---
class TrainingRequest(BaseModel):
    filename: str
    target_column: str
    numerical_features: list[str]
    categorical_features: list[str]


@app.post("/train/")
async def train_model(request: TrainingRequest):
    """
    Обучает модель на указанном файле и с указанными параметрами.
    """
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        df = pd.read_csv(file_path)

        # --- Логика обучения (похожа на наш старый код) ---
        X = df[request.numerical_features + request.categorical_features]
        y = df[request.target_column]

        numeric_transformer = StandardScaler()
        categorical_transformer = OneHotEncoder(handle_unknown='ignore')

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, request.numerical_features),
                ('cat', categorical_transformer, request.categorical_features)
            ])

        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', RandomForestClassifier(random_state=42))
        ])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        model_pipeline.fit(X_train, y_train)

        report = classification_report(y_test, model_pipeline.predict(X_test), output_dict=True)

        # --- Сохранение модели и конфигурации ---
        model_path = os.path.join(MODEL_DIR, f"{request.filename}_model.joblib")
        config_path = os.path.join(MODEL_DIR, f"{request.filename}_config.json")

        joblib.dump(model_pipeline, model_path)

        config = {
            'target': request.target_column,
            'numerical_features': request.numerical_features,
            'categorical_features': request.categorical_features,
            'categorical_values': {col: df[col].unique().tolist() for col in request.categorical_features}
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

        return {"status": "success", "message": "Model trained successfully", "report": report}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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