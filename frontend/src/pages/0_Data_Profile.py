#frontend/src/pages/0_Data_Profile.p
import streamlit as st
import requests

# --- Настройки ---
PROFILING_SERVICE_URL = "http://profiling_service:8000"

st.set_page_config(page_title="Авто-анализ данных", layout="wide")
st.title("📊 Автоматический профиль данных (ydata-profiling)")

if 'profile_report_filename' in st.session_state:
    report_filename = st.session_state['profile_report_filename']

    try:
        # --- Правильный способ: Запрашиваем HTML-отчет у сервиса ---
        with st.spinner("Загрузка отчета..."):
            response = requests.get(f"{PROFILING_SERVICE_URL}/reports/{report_filename}")
            response.raise_for_status()  # Проверяем на ошибки

            html_content = response.text
            st.components.v1.html(html_content, height=1000, scrolling=True)

    except requests.exceptions.RequestException as e:
        st.error(f"Не удалось загрузить отчет от сервиса. Ошибка: {e}")
    except Exception as e:
        st.error(f"Произошла непредвиденная ошибка: {e}")

else:
    st.info("Чтобы увидеть отчет, пожалуйста, сначала загрузите файл на главной странице.")