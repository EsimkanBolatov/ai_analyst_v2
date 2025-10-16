#frontend/src/pages/2_Train_Model.py
import streamlit as st
import pandas as pd
import requests
import os

# --- Настройки ---
TRAINING_SERVICE_URL = "http://training_service:8000"

st.set_page_config(page_title="Обучение своей модели", layout="wide")
st.title("🔬 Обучение своей модели")

# Проверяем, был ли загружен файл
if 'filename' not in st.session_state:
    st.warning("Пожалуйста, сначала загрузите файл на главной странице.")
else:
    filename = st.session_state['filename']
    st.info(f"Работаем с файлом: `{filename}`")

    # --- Читаем первые строки файла для получения колонок ---
    # В реальной системе здесь мог бы быть запрос к file_service за метаданными
    try:
        FILE_SERVICE_URL = "http://file_service:8000"
        response = requests.get(f"{FILE_SERVICE_URL}/columns/{filename}")
        response.raise_for_status()  # Проверяем на HTTP ошибки

        columns = response.json().get("columns", [])

        if not columns:
            st.error("Не удалось получить колонки из файла. Файл может быть пустым или иметь неверный формат.")
        else:
            # --- Интерфейс настройки модели (остается без изменений) ---
            st.header("Настройка модели")
            target_column = st.selectbox("1. Выберите целевую колонку (что предсказываем?)", columns)

            feature_columns = [col for col in columns if col != target_column]
            numerical_features = st.multiselect("2. Выберите числовые признаки", feature_columns)

            available_for_cat = [col for col in feature_columns if col not in numerical_features]
            categorical_features = st.multiselect("3. Выберите категориальные признаки", available_for_cat)

            if st.button("Начать обучение"):
                with st.spinner("Модель обучается... Это может занять несколько минут."):
                    training_request = {
                        "filename": filename,
                        "target_column": target_column,
                        "numerical_features": numerical_features,
                        "categorical_features": categorical_features
                    }

                    response = requests.post(f"{TRAINING_SERVICE_URL}/train/", json=training_request)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Модель успешно обучена и сохранена!")
                        st.subheader("Отчет о качестве модели:")
                        st.json(result['report'])
                    else:
                        st.error(f"Произошла ошибка при обучении: {response.text}")

    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при получении метаданных файла от сервиса: {e}")
    except Exception as e:
        st.error(f"Произошла непредвиденная ошибка: {e}")