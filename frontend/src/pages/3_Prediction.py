import streamlit as st
import requests
import os
import json
import datetime

# --- Настройки ---
PREDICTION_SERVICE_URL = "http://prediction_service:8000"
TRAINING_SERVICE_URL = "http://training_service:8000"

st.set_page_config(page_title="Оценка аномальности", layout="wide")
st.title("🤖 Оценка аномальности транзакции")

try:
    response = requests.get(f"{TRAINING_SERVICE_URL}/models/")
    response.raise_for_status()
    available_models = response.json().get("models", [])

    if not available_models:
        st.warning("Не найдено ни одной обученной модели.")
    else:
        selected_model_name = st.selectbox("1. Выберите модель:", available_models)

        if selected_model_name:
            config_response = requests.get(f"{TRAINING_SERVICE_URL}/models/{selected_model_name}/config")
            config_response.raise_for_status()
            config = config_response.json()
            model_type = config.get('model_type', 'classification') # Определяем тип модели

            st.info(f"Выбрана модель типа: {'Обнаружение аномалий' if model_type == 'anomaly_detection' else 'Классификация'}")

            with st.form("prediction_form"):
                st.header("2. Введите данные для оценки:")
                input_data = {}

                for col in config['numerical_features']:
                    input_data[col] = st.number_input(f"Введите '{col}'", value=0.0)
                for col in config['categorical_features']:
                    input_data[col] = st.selectbox(f"Выберите '{col}'", config['categorical_values'][col])
                for col in config.get('date_features', []):
                    date_value = st.date_input(f"Дата '{col}'", datetime.date.today())
                    time_value = st.time_input(f"Время '{col}'", datetime.time(12, 00))
                    input_data[col] = f"{date_value.isoformat()}T{time_value.isoformat()}"

                submitted = st.form_submit_button("Получить оценку")

                if submitted:
                    with st.spinner("Отправляем данные на анализ..."):
                        # --- ВЫЗЫВАЕМ НОВЫЙ ЭНДПОИНТ ---
                        request_data = {"model_filename": selected_model_name, **input_data}
                        pred_response = requests.post(f"{PREDICTION_SERVICE_URL}/predict_or_score/", json=request_data)

                        if pred_response.status_code == 200:
                            result = pred_response.json()
                            st.subheader("🎉 Результат оценки:")

                            # --- НОВОЕ ОТОБРАЖЕНИЕ РЕЗУЛЬТАТА ---
                            if result.get("model_type") == "anomaly_detection":
                                score = result.get("anomaly_score", 0)
                                is_anomaly = result.get("is_anomaly_predicted", False)
                                st.metric("Оценка аномальности (Anomaly Score)", f"{score:.4f}")
                                if is_anomaly:
                                    st.error("🔴 Транзакция определена как АНОМАЛИЯ (score < 0)")
                                else:
                                    st.success("🟢 Транзакция определена как НОРМА (score >= 0)")
                                st.caption("Чем ниже значение, тем более аномальной считается транзакция.")
                            else: # Старая логика для классификации
                                st.success(f"**Предсказанный класс:** `{result.get('prediction', 'N/A')}`")
                                st.write("**Вероятности по классам:**")
                                st.json(result.get('probabilities', {}))
                            # ------------------------------------

                        else:
                            st.error(f"Произошла ошибка при оценке: {pred_response.text}")
except requests.exceptions.RequestException as e:
    st.error(f"Ошибка при взаимодействии с бэкенд-сервисом: {e}")
except Exception as e:
    st.error(f"Произошла непредвиденная ошибка: {e}")