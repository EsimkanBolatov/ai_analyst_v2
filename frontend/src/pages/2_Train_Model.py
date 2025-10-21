#frontend/src/pages/2_Train_Model.py
import streamlit as st
import pandas as pd
import requests
import os

# --- Настройки ---
TRAINING_SERVICE_URL = "http://training_service:8000"
FILE_SERVICE_URL = "http://file_service:8000"

st.set_page_config(page_title="Обучение детектора аномалий", layout="wide")
st.title("🔬 Обучение детектора аномалий (без учителя)")

if 'filename' not in st.session_state:
    st.warning("Пожалуйста, сначала загрузите файл на главной странице.")
else:
    filename = st.session_state['filename']
    st.info(f"Работаем с файлом: `{filename}`")

    try:
        response = requests.get(f"{FILE_SERVICE_URL}/columns/{filename}")
        response.raise_for_status()
        columns = response.json().get("columns", [])

        if not columns:
            st.error("Не удалось получить колонки из файла.")
        else:
            st.header("Настройка модели")
            # target_column = st.selectbox("1. Выберите целевую колонку", columns) # <-- УБРАЛИ

            # Нумерация сдвинулась
            feature_columns = columns  # Все колонки доступны как признаки
            numerical_features = st.multiselect("1. Выберите ЧИСЛОВЫЕ признаки", feature_columns)

            available_for_cat = [col for col in feature_columns if col not in numerical_features]
            categorical_features = st.multiselect("2. Выберите КАТЕГОРИАЛЬНЫЕ признаки", available_for_cat)

            available_for_date = [col for col in available_for_cat if col not in categorical_features]
            date_features = st.multiselect("3. Выберите признаки с ДАТОЙ/ВРЕМЕНЕМ", available_for_date)

            if st.button("Начать обучение детектора аномалий"):
                with st.spinner("Модель обучается..."):
                    training_request = {
                        "filename": filename,
                        # "target_column": target_column, # <-- УБРАЛИ
                        "numerical_features": numerical_features,
                        "categorical_features": categorical_features,
                        "date_features": date_features
                    }

                    # --- ВЫЗЫВАЕМ НОВЫЙ ЭНДПОИНТ ---
                    response = requests.post(f"{TRAINING_SERVICE_URL}/train_anomaly_detector/", json=training_request)

                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ {result['message']}")
                        # Отчета о качестве больше нет
                    else:
                        st.error(f"Произошла ошибка при обучении: {response.text}")

    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при получении метаданных файла от сервиса: {e}")
    except Exception as e:
        st.error(f"Произошла непредвиденная ошибка: {e}")