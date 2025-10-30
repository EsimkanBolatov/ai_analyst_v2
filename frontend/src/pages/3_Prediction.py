import streamlit as st
import requests
import os
import json
import datetime
import pandas as pd
import plotly.express as px
import numpy as np

# --- Настройки ---
FILE_SERVICE_URL = "http://file_service:8000"
PREDICTION_SERVICE_URL = "http://prediction_service:8000"
TRAINING_SERVICE_URL = "http://training_service:8000"

st.set_page_config(page_title="Анализ и Оценка", layout="wide")
st.title("🎯 Анализ аномалий и предсказания")

# --- Вспомогательные функции с улучшенной обработкой ошибок ---
@st.cache_data(ttl=30)
def get_file_list():
    try:
        response = requests.get(f"{FILE_SERVICE_URL}/files/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.toast(f"Warning: Could not fetch file list from file_service: {e}", icon="⚠️")
    return []

@st.cache_data(ttl=60)
def get_model_list():
    try:
        response = requests.get(f"{TRAINING_SERVICE_URL}/models/")
        response.raise_for_status()
        return response.json().get("models", [])
    except requests.exceptions.RequestException as e:
         st.toast(f"Warning: Could not fetch model list from training_service: {e}", icon="⚠️")
    return []

# --- Получаем списки файлов и моделей ---
file_list = get_file_list()
model_list = get_model_list()

if not model_list:
    st.warning("Не найдено ни одной обученной модели. Пожалуйста, обучите модель на странице 'Train Model'.")
    st.stop()
if not file_list:
    st.warning("Не найдено загруженных файлов. Пожалуйста, загрузите файл на главной странице.")
    st.stop()

# --- Используем вкладки для разделения функционала ---
tab1, tab2 = st.tabs(["Анализ всего файла (визуализация)", "Одиночная оценка (вручную)"])

# --- АНАЛИЗ ВСЕГО ФАЙЛА ---
with tab1:
    st.header("1. Визуализация распределения аномалий (весь файл)")
    st.markdown("""
    Выберите файл и обученную модель (`IsolationForest`).
    Сервис применит модель ко **всему** файлу и вернет оценки аномальности для каждой строки.
    Это поможет вам визуально определить порог для выявления аномалий.
    """)

    col1, col2 = st.columns(2)
    with col1:
        selected_file_tab1 = st.selectbox(
            "Выберите файл для анализа:",
            options=file_list,
            index=None,
            placeholder="Выберите файл...",
            key="tab1_file"
        )
    with col2:
        selected_model_tab1 = st.selectbox(
            "Выберите обученную модель:",
            options=model_list,
            index=None,
            placeholder="Выберите модель...",
            key="tab1_model"
        )

    if st.button("Рассчитать и визуализировать оценки", key="score_file_button"):
        if selected_file_tab1 and selected_model_tab1:
            with st.spinner(f"Применяем модель '{selected_model_tab1}' ко всему файлу '{selected_file_tab1}'..."):
                service_name = "prediction_service (/score_file/)" # Для ошибок
                try:
                    payload = {
                        "model_name": selected_model_tab1,
                        "filename": selected_file_tab1
                    }
                    response = requests.post(f"{PREDICTION_SERVICE_URL}/score_file/", json=payload, timeout=600)
                    response.raise_for_status() # Ловим HTTP ошибки

                    data = response.json()
                    scores = data.get("scores")

                    if scores:
                        st.session_state['anomaly_scores'] = scores
                        st.success("Расчет завершен!")
                    else:
                        st.error("Сервис вернул пустой список оценок.")

                except requests.exceptions.RequestException as e:
                    st.error(
                        f"❌ Не удалось связаться с сервисом '{service_name}'. "
                        f"Проверьте Docker и обновите страницу."
                    )
                except requests.exceptions.HTTPError as e:
                     st.error(f"❌ Сервис '{service_name}' вернул ошибку: {e.response.status_code}")
                     try:
                         error_detail = e.response.json().get("detail", e.response.text)
                         st.error(f"   Сообщение: {error_detail}")
                     except Exception:
                         st.error(f"   Ответ: {e.response.text}")
                except Exception as e:
                     st.error(f"❌ Непредвиденная ошибка при расчете оценок: {e}")
        else:
            st.warning("Пожалуйста, выберите и файл, и модель.")

    # --- Отображение результатов для вкладки 1 ---
    if 'anomaly_scores' in st.session_state:
        scores = st.session_state['anomaly_scores']
        df_scores = pd.DataFrame(scores, columns=["score"])

        st.subheader("Результаты анализа")
        stats_cols = st.columns(4)
        stats_cols[0].metric("Среднее (Mean)", f"{df_scores['score'].mean():.4f}")
        stats_cols[1].metric("Медиана (Median)", f"{df_scores['score'].median():.4f}")
        stats_cols[2].metric("Мин. (Min)", f"{df_scores['score'].min():.4f}")
        stats_cols[3].metric("Макс. (Max)", f"{df_scores['score'].max():.4f}")

        st.markdown("#### Распределение оценок аномальности")
        fig = px.histogram(
            df_scores, x="score", nbins=100, title="Распределение оценок аномальности (Anomaly Score)",
            labels={"score": "Оценка аномальности"}
        )
        fig.add_vline(x=0.0, line_dash="dash", line_color="red", annotation_text="Порог (0.0)")
        st.plotly_chart(fig, use_container_width=True)
        st.info("""
        **Как читать этот график:**
        * Модель `IsolationForest` помечает значения **< 0** (слева от красной линии) как **аномалии**.
        * Чем **ниже** оценка (дальше влево), тем более "аномальной" считается транзакция.
        """)

# --- ОДИНОЧНАЯ ОЦЕНКА ---
with tab2:
    st.header("1. Выберите модель для одиночной оценки")

    selected_model_tab2 = st.selectbox(
        "Выберите модель:",
        options=model_list,
        key="tab2_model"
    )

    if selected_model_tab2:
        service_name = "training_service (/models/.../config)"
        try:
            # Загружаем конфиг для выбранной модели
            config_response = requests.get(f"{TRAINING_SERVICE_URL}/models/{selected_model_tab2}/config")
            config_response.raise_for_status()
            config = config_response.json()
            model_type = config.get('model_type', 'classification')

            st.info(f"Выбрана модель типа: {'Обнаружение аномалий' if model_type == 'anomaly_detection' else 'Классификация'}")

            # Форма для ввода данных
            with st.form("prediction_form"):
                st.header("2. Введите данные для оценки:")
                input_data = {}

                # Динамическое создание полей на основе конфига
                date_features = config.get('date_features', [])
                num_features = config.get('numerical_features', [])
                cat_features = config.get('categorical_features', [])
                cat_values = config.get('categorical_values', {})
                gen_date_features = config.get('generated_date_features', []) # Получаем список сгенерированных фичей

                for col in num_features:
                    # Не показываем поля, которые генерируются из дат
                    if col not in gen_date_features:
                        input_data[col] = st.number_input(f"Введите '{col}'", value=0.0, key=f"num_{col}")

                for col in cat_features:
                    options = cat_values.get(col, [])
                    if options:
                        input_data[col] = st.selectbox(f"Выберите '{col}'", options, key=f"cat_{col}")
                    else:
                         # Если опций нет (редкий случай), даем текстовое поле
                         input_data[col] = st.text_input(f"Введите '{col}' (нет сохраненных значений)", value="", key=f"cat_{col}")

                for col in date_features:
                    date_value = st.date_input(f"Дата '{col}'", datetime.date.today(), key=f"date_{col}")
                    time_value = st.time_input(f"Время '{col}'", datetime.time(12, 00), key=f"time_{col}")
                    input_data[col] = f"{date_value.isoformat()}T{time_value.isoformat()}"

                submitted = st.form_submit_button("Получить оценку")

                if submitted:
                    with st.spinner("Отправляем данные на анализ..."):
                        service_name = "prediction_service (/predict_or_score/)" # Для ошибок
                        try:
                            request_data = {
                                "model_name": selected_model_tab2,
                                "features": input_data
                            }
                            pred_response = requests.post(f"{PREDICTION_SERVICE_URL}/predict_or_score/", json=request_data)
                            pred_response.raise_for_status() # Ловим HTTP ошибки

                            result = pred_response.json()
                            st.subheader("🎉 Результат оценки:")

                            if result.get("model_type") == "anomaly_detection":
                                score = result.get("anomaly_score", 0)
                                is_anomaly = result.get("is_anomaly_predicted", False)
                                st.metric("Оценка аномальности (Anomaly Score)", f"{score:.4f}")
                                if is_anomaly:
                                    st.error("🔴 Транзакция определена как АНОМАЛИЯ (score < 0)")
                                else:
                                    st.success("🟢 Транзакция определена как НОРМА (score >= 0)")
                                st.caption("Чем ниже значение, тем более аномальной считается транзакция.")
                            else:
                                st.success(f"**Предсказанный класс:** `{result.get('prediction', 'N/A')}`")

                        except requests.exceptions.RequestException as e:
                            st.error(
                                f"❌ Не удалось связаться с сервисом '{service_name}'. "
                                f"Проверьте Docker."
                            )
                        except requests.exceptions.HTTPError as e:
                             st.error(f"❌ Сервис '{service_name}' вернул ошибку при оценке: {e.response.status_code}")
                             try:
                                 error_detail = e.response.json().get("detail", e.response.text)
                                 st.error(f"   Сообщение: {error_detail}")
                             except Exception:
                                 st.error(f"   Ответ: {e.response.text}")
                        except Exception as e:
                             st.error(f"❌ Непредвиденная ошибка при получении оценки: {e}")

        except requests.exceptions.RequestException as e:
            st.error(
                f"❌ Не удалось загрузить конфигурацию для модели '{selected_model_tab2}' от '{service_name}'. "
                f"Проверьте Docker."
            )
        except requests.exceptions.HTTPError as e:
             st.error(f"❌ Сервис '{service_name}' вернул ошибку при запросе конфига: {e.response.status_code}")
             try:
                 error_detail = e.response.json().get("detail", e.response.text)
                 st.error(f"   Сообщение: {error_detail}")
             except Exception:
                 st.error(f"   Ответ: {e.response.text}")
        except Exception as e:
             st.error(f"❌ Непредвиденная ошибка при загрузке конфигурации модели: {e}")