import streamlit as st
import requests
import os
import json

# --- Настройки ---
PREDICTION_SERVICE_URL = "http://prediction_service:8000"
TRAINING_SERVICE_URL = "http://training_service:8000"  # <-- ДОБАВЛЕНО

st.set_page_config(page_title="Прогнозирование", layout="wide")
st.title("🤖 Прогнозирование на основе обученной модели")

try:
    # --- Правильный способ: Запрашиваем список моделей у сервиса ---
    response = requests.get(f"{TRAINING_SERVICE_URL}/models/")
    response.raise_for_status()
    available_models = response.json().get("models", [])

    if not available_models:
        st.warning(
            "Не найдено ни одной обученной модели. Пожалуйста, сначала обучите модель на странице 'Train Model'.")
    else:
        selected_model_name = st.selectbox("1. Выберите модель для прогнозирования:", available_models)

        if selected_model_name:
            # --- Загружаем конфигурацию выбранной модели через API ---
            config_response = requests.get(f"{TRAINING_SERVICE_URL}/models/{selected_model_name}/config")
            config_response.raise_for_status()
            config = config_response.json()

            # --- Динамически генерируем форму ---
            with st.form("prediction_form"):
                st.header("2. Введите данные для прогноза:")
                input_data = {}

                for col in config['numerical_features']:
                    input_data[col] = st.number_input(f"Введите значение для '{col}'", value=0.0)

                for col in config['categorical_features']:
                    input_data[col] = st.selectbox(f"Выберите значение для '{col}'", config['categorical_values'][col])

                submitted = st.form_submit_button("Получить прогноз")

                if submitted:
                    with st.spinner("Отправляем данные на анализ..."):
                        request_data = {"model_filename": selected_model_name, **input_data}

                        pred_response = requests.post(f"{PREDICTION_SERVICE_URL}/predict/", json=request_data)

                        if pred_response.status_code == 200:
                            result = pred_response.json()
                            st.subheader("🎉 Результат прогноза:")
                            st.success(f"**Предсказанный класс:** `{result['prediction']}`")

                            st.write("**Вероятности по классам:**")
                            st.json(result['probabilities'])
                        else:
                            st.error(f"Произошла ошибка при прогнозировании: {pred_response.text}")

except requests.exceptions.RequestException as e:
    st.error(f"Ошибка при взаимодействии с бэкенд-сервисом: {e}")
except Exception as e:
    st.error(f"Произошла непредвиденная ошибка: {e}")