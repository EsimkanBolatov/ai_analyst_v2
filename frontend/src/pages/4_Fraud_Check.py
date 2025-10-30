import streamlit as st
import requests
import os
import re
import json

# --- Настройки ---
FRAUD_CHECK_SERVICE_URL = os.getenv("FRAUD_CHECK_SERVICE_URL", "http://fraud_check_service:8000")

st.set_page_config(page_title="Проверка данных", layout="wide")
st.title("🔍 Ручная проверка данных на мошенничество")
st.markdown("Введите данные (телефон, email, URL или текст) для получения оценки риска.")

# --- UI Форма для ввода ---
data_type_options = {
    "Телефон": "phone",
    "Email": "email",
    "URL-адрес": "url",
    "Текст сообщения": "text"
}

# Инициализация session_state
if 'last_check_value' not in st.session_state:
    st.session_state.last_check_value = None
if 'last_check_type' not in st.session_state:
    st.session_state.last_check_type = None
if 'check_result' not in st.session_state:
     st.session_state.check_result = None

# --- Форма ввода ---
with st.form("check_form"):
    selected_option = st.selectbox("1. Выберите тип данных:", options=data_type_options.keys())

    if selected_option == "Текст сообщения":
        value_to_check = st.text_area("2. Введите данные для проверки:", height=150)
    else:
        value_to_check = st.text_input("2. Введите данные для проверки:")

    submitted = st.form_submit_button("Проверить")

# --- Логика обработки формы ---
if submitted and value_to_check:
    data_type = data_type_options[selected_option]
    service_name = "fraud_check_service (/check/)"

    with st.spinner("Анализируем данные..."):
        try:
            payload = {"data_type": data_type, "value": value_to_check}
            response = requests.post(f"{FRAUD_CHECK_SERVICE_URL}/check/", json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            st.session_state.check_result = result
            st.session_state.last_check_value = value_to_check
            st.session_state.last_check_type = data_type

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Не удалось связаться с сервисом '{service_name}'. Проверьте Docker.")
            st.session_state.check_result = None
            st.session_state.last_check_value = None
        except requests.exceptions.HTTPError as e:
             st.error(f"❌ Сервис '{service_name}' вернул ошибку: {e.response.status_code}")
             try:
                 error_detail = e.response.json().get("detail", e.response.text)
                 st.error(f"   Сообщение: {error_detail}")
             except Exception:
                 st.error(f"   Ответ: {e.response.text}")
             st.session_state.check_result = None
             st.session_state.last_check_value = None
        except Exception as e:
             st.error(f"❌ Непредвиденная ошибка при проверке: {e}")
             st.session_state.check_result = None
             st.session_state.last_check_value = None


# --- Отображение результата ---
if st.session_state.check_result:
    result = st.session_state.check_result
    risk_level = result.get("risk_level")
    explanation = result.get("explanation")
    risk_score = result.get("risk_score")

    st.subheader("Результат проверки:")

    if risk_level == "Высокий": st.error(f"**Уровень риска: {risk_level} (Оценка: {risk_score})**")
    elif risk_level == "Средний": st.warning(f"**Уровень риска: {risk_level} (Оценка: {risk_score})**")
    else: st.success(f"**Уровень риска: {risk_level} (Оценка: {risk_score})**")

    st.info(f"**Пояснение:** {explanation}")
    st.divider()

# --- Блок Обратной Связи ---
if st.session_state.check_result and st.session_state.last_check_value:

    data_type_to_blacklist = st.session_state.last_check_type
    value_to_blacklist = st.session_state.last_check_value
    original_value_display = st.session_state.last_check_value

    if data_type_to_blacklist == 'url':
        data_type_to_blacklist = 'domain'
        try:
            domain_match = re.search(r"https?://(?:www\.)?([^/:\s]+)", value_to_blacklist)
            if domain_match:
                value_to_blacklist = domain_match.group(1)
            else: # Если URL без http://, пробуем базовый парсинг
                 value_to_blacklist = value_to_blacklist.split('/')[0].split(':')[0]
        except Exception:
            pass

    # Показываем кнопку только для поддерживаемых типов
    if data_type_to_blacklist in ["phone", "email", "domain"]:
        st.subheader("Обратная связь")
        st.write(f"Считаете, что **'{original_value_display}'** (будет добавлено как `{data_type_to_blacklist}: {value_to_blacklist}`) является мошенническим?")

        if st.button("Пометить и добавить в черный список", key="add_to_blacklist_button"):
            with st.spinner("Добавляем в базу данных..."):
                service_name = "fraud_check_service (/add-blacklist/)"
                try:
                    payload = {
                        "data_type": data_type_to_blacklist,
                        "value": value_to_blacklist
                    }
                    response = requests.post(f"{FRAUD_CHECK_SERVICE_URL}/add-blacklist/", json=payload, timeout=60)
                    response.raise_for_status() # Ловим HTTP ошибки

                    st.success(f"Успешно! '{value_to_blacklist}' добавлен в черный список.")
                    st.session_state.last_check_value = None
                    st.session_state.check_result = None
                    st.rerun()

                except requests.exceptions.RequestException as e:
                    st.error(
                        f"❌ Не удалось связаться с сервисом '{service_name}'. "
                        f"Проверьте Docker."
                    )
                except requests.exceptions.HTTPError as e:
                     is_duplicate = False
                     error_detail = ""

                     try:
                          data = e.response.json()
                          if isinstance(data, dict):
                              error_detail = data.get("detail", "")
                          else:
                              error_detail = str(data)
                     except json.JSONDecodeError:
                          error_detail = e.response.text
                     except Exception:
                          error_detail = e.response.text

                     if error_detail:
                         error_lower = str(error_detail).lower()
                         if "unique constraint" in error_lower or \
                            "duplicate key value violates unique constraint" in error_lower or \
                            "уже существует" in error_lower:
                             is_duplicate = True

                     if is_duplicate:
                         st.warning(f"Запись '{value_to_blacklist}' уже существует в черном списке.")
                     else:
                         st.error(f"❌ Сервис '{service_name}' вернул ошибку: {e.response.status_code}")
                         st.error(f"   Сообщение: {error_detail or e.response.text}")

                except Exception as e:
                     st.error(f"❌ Непредвиденная ошибка при добавлении в черный список: {e}")