import streamlit as st
import requests
import os

# --- URL сервисов ---
FILE_SERVICE_URL = "http://file_service:8000"
TRAINING_SERVICE_URL = "http://training_service:8000"

st.set_page_config(page_title="Train Model", layout="wide")
st.title("🗿 Обучение модели детектора аномалий")

# --- Вспомогательные функции ---
@st.cache_data(ttl=30)
def get_file_list():
    try:
        response = requests.get(f"{FILE_SERVICE_URL}/files/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.toast(f"Warning: Could not fetch file list from file_service: {e}", icon="⚠️")
    return []

@st.cache_data(ttl=5)
def get_columns_for_file(filename: str):
    if not filename: return []
    try:
        response = requests.get(f"{FILE_SERVICE_URL}/columns/{filename}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Не удалось получить список колонок от 'file_service'. Проверьте Docker.")
    except requests.exceptions.HTTPError as e:
         st.error(f"❌ Сервис 'file_service' вернул ошибку при запросе колонок: {e.response.status_code}")
         try:
             error_detail = e.response.json().get("detail", e.response.text)
             st.error(f"   Сообщение: {error_detail}")
         except Exception:
             st.error(f"   Ответ: {e.response.text}")
    return []

# --- Выбор файла ---
st.header("Шаг 1: Выберите файл для обучения")
file_list = get_file_list()

if not file_list:
    st.warning("Не найдено загруженных файлов. Пожалуйста, загрузите файл на главной странице.")
    st.stop()

selected_file = st.selectbox(
    "Выберите .csv файл:",
    options=file_list,
    index=None,
    placeholder="Выберите файл..."
)

# --- Выбор признаков ---
if selected_file:
    all_columns = get_columns_for_file(selected_file)
    if all_columns:
        st.header("Шаг 2: Настройте признаки")

        col1, col2, col3 = st.columns(3)
        with col1:
            numerical_features = st.multiselect(
                "Выберите **числовые** признаки:",
                options=all_columns
            )
        with col2:
            categorical_features = st.multiselect(
                "Выберите **категориальные** признаки:",
                options=all_columns
            )
        with col3:
            date_features = st.multiselect(
                "Выберите **признаки-даты**:",
                options=all_columns,
                help="Выберите колонки с датами/временем. Они будут преобразованы (час, день недели и т.д.)."
            )

        st.header("Шаг 3: Настройте Feature Engineering (Опционально)")

        enable_fe = st.checkbox("Включить автоматическое создание признаков (Feature Engineering)?")

        card_id_col = None
        timestamp_col = None
        amount_col = None

        if enable_fe:
            st.info("""
            Будут созданы признаки:
            - `is_night`: 1 если транзакция ночью (22:00-06:00), иначе 0.
            - `card_tx_count_1h`: Кол-во транзакций по этой карте за последний час.
            - `card_tx_amount_sum_1h`: Сумма транзакций по этой карте за последний час.

            **Важно:** Для этого необходимо правильно выбрать соответствующие колонки ниже.
            Колонка с временем должна быть также выбрана в **"признаках-датах"** выше для генерации `_hour`.
            """)
            fe_cols = st.columns(3)
            with fe_cols[0]:
                card_id_col = st.selectbox(
                    "Колонка ID карты:", options=all_columns, index=None, placeholder="Выберите колонку..."
                )
            with fe_cols[1]:
                timestamp_col = st.selectbox(
                    "Колонка Времени транзакции:", options=all_columns, index=None, placeholder="Выберите колонку..."
                )
            with fe_cols[2]:
                amount_col = st.selectbox(
                    "Колонка Суммы транзакции:", options=all_columns, index=None, placeholder="Выберите колонку..."
                )

        st.header("Шаг 4: Настройте и запустите обучение")

        model_name = st.text_input(
            "Введите имя для сохранения модели (например, 'my_anomaly_model_1')",
            placeholder="my_anomaly_model_1"
        )

        # --- OneClassSVM в список ---
        model_type = st.selectbox(
            "Выберите тип модели:",
            ["IsolationForest", "LocalOutlierFactor", "OneClassSVM"]
        )
        # ---------------------------------------------------

        st.markdown("---")

        if st.button("Начать обучение детектора аномалий", type="primary"):
            # Проверки перед отправкой
            if not model_name:
                st.error("Ошибка: Пожалуйста, введите имя для сохранения модели.")
            elif not numerical_features and not categorical_features and not date_features:
                st.error("Ошибка: Выберите хотя бы один признак (числовой, категориальный или дату).")
            elif enable_fe and not all([card_id_col, timestamp_col, amount_col]):
                 st.error("Ошибка: Если Feature Engineering включен, необходимо выбрать колонки ID карты, Времени и Суммы.")
            elif enable_fe and timestamp_col not in date_features:
                 st.error(f"Ошибка: Если Feature Engineering включен, колонка времени ('{timestamp_col}') должна быть также выбрана в 'Признаках-датах'.")
            else:
                with st.spinner("Идет обучение модели... Это может занять несколько минут."):
                    service_name = "training_service"
                    try:
                        payload = {
                            "filename": selected_file,
                            "model_name": model_name,
                            "model_type": model_type,
                            "numerical_features": numerical_features,
                            "categorical_features": categorical_features,
                            "date_features": date_features,
                            "enable_feature_engineering": enable_fe,
                            "card_id_column": card_id_col,
                            "timestamp_column": timestamp_col,
                            "amount_column": amount_col
                        }

                        response = requests.post(
                            f"{TRAINING_SERVICE_URL}/train_anomaly_detector/",
                            json=payload,
                            timeout=600 # 10 минут
                        )
                        response.raise_for_status()

                        st.success(f"Модель '{model_name}' успешно обучена и сохранена!")
                        st.json(response.json())

                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Не удалось связаться с сервисом '{service_name}'. Проверьте Docker.")
                    except requests.exceptions.HTTPError as e:
                         st.error(f"❌ Сервис '{service_name}' вернул ошибку при обучении: {e.response.status_code}")
                         try:
                             error_detail = e.response.json().get("detail", e.response.text)
                             st.error(f"   Сообщение: {error_detail}")
                         except Exception:
                             st.error(f"   Ответ: {e.response.text}")
                    except Exception as e:
                         st.error(f"❌ Непредвиденная ошибка при обучении: {e}")