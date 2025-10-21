import streamlit as st
import requests

# --- Настройки ---
FRAUD_CHECK_SERVICE_URL = "http://fraud_check_service:8000" # URL нашего нового сервиса

st.set_page_config(page_title="Проверка данных", layout="wide")
st.title("🔍 Проверка данных на мошенничество")
st.write("Введите данные, чтобы проверить их по внутренним и внешним базам на признаки мошенничества.")

# --- Элементы интерфейса ---

# Выбор типа данных
data_type_options = {
    "Телефон": "phone",
    "Email": "email",
    "URL (адрес сайта)": "url",
    "Текст сообщения": "text"
}
selected_data_type_label = st.selectbox(
    "1. Выберите тип данных:",
    options=list(data_type_options.keys())
)
selected_data_type = data_type_options[selected_data_type_label] # Получаем ключ для API

# Поле для ввода значения
if selected_data_type == 'text':
    input_value = st.text_area("2. Введите текст для проверки:", height=150)
else:
    input_value = st.text_input(f"2. Введите {selected_data_type_label.lower()} для проверки:")

# Кнопка для запуска проверки
submit_button = st.button("Проверить")

# --- Логика обработки ---
if submit_button and input_value:
    with st.spinner("Выполняется проверка..."):
        try:
            # Формируем запрос к бэкенду
            request_data = {
                "data_type": selected_data_type,
                "value": input_value
            }
            response = requests.post(f"{FRAUD_CHECK_SERVICE_URL}/check/", json=request_data)
            response.raise_for_status() # Проверяем на HTTP ошибки (4xx, 5xx)

            result = response.json()

            # --- Отображение результата ---
            st.subheader("Результат проверки:")
            risk_level = result.get("risk_level", "Ошибка")
            explanation = result.get("explanation", "Не удалось получить объяснение.")
            checked_value = result.get("input_value", input_value) # Показываем, что именно проверяли

            st.write(f"**Проверенное значение:** `{checked_value}`")

            if risk_level == "Высокий":
                st.error(f"**Уровень риска:** {risk_level}")
                st.warning(f"**Пояснение:** {explanation}")
            elif risk_level == "Средний":
                st.warning(f"**Уровень риска:** {risk_level}")
                st.info(f"**Пояснение:** {explanation}")
            elif risk_level == "Низкий":
                st.success(f"**Уровень риска:** {risk_level}")
                st.info(f"**Пояснение:** {explanation}")
            else: # Ошибка валидации или другая проблема
                st.error(f"**Статус:** {risk_level}")
                st.error(f"**Пояснение:** {explanation}")

        except requests.exceptions.RequestException as e:
            st.error(f"Ошибка при соединении с сервисом проверки: {e}")
        except Exception as e:
            st.error(f"Произошла непредвиденная ошибка: {e}")

elif submit_button and not input_value:
    st.warning("Пожалуйста, введите значение для проверки.")