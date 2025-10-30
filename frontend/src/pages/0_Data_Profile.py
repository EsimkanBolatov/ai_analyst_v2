#frontend/src/pages/0_Data_Profile.p
import streamlit as st
import requests
import os
import streamlit.components.v1 as components

# --- Конфигурация страницы ---
st.set_page_config(
    page_title="Data Profile Report",
    page_icon="📋",
    layout="wide"
)

# --- URL сервиса профилирования ---
PROFILING_SERVICE_URL = os.getenv("PROFILING_SERVICE_URL", "http://profiling_service:8000")

st.title("📋 Отчет о профилировании данных (ydata-profiling)")

# --- Проверка наличия имени файла отчета в session_state ---
report_filename = st.session_state.get('last_profile_report')

if report_filename:
    st.info(f"Отображается отчет для файла: **{report_filename.replace('_profile.html', '.csv')}**")

    report_url = f"{PROFILING_SERVICE_URL}/reports/{report_filename}"

    try:
        # Загружаем HTML-контент
        with st.spinner(f"Загрузка отчета '{report_filename}'..."):
            service_name = "profiling_service"
            response = requests.get(report_url, timeout=60)
            response.raise_for_status()
            report_html = response.text
            components.html(report_html, height=800, scrolling=True)

    except requests.exceptions.RequestException as e:
        # Улучшенная обработка ошибок сети
        st.error(
            f"❌ Не удалось связаться с сервисом '{service_name}'. "
            f"Пожалуйста, убедитесь, что все Docker-контейнеры запущены ('docker-compose up') "
            f"и попробуйте обновить страницу."
        )

    except requests.exceptions.HTTPError as e:
        # Улучшенная обработка ошибок от бэкенда
        st.error(f"❌ Сервис '{service_name}' вернул ошибку при запросе отчета: {e.response.status_code}")
        try:
            error_detail = e.response.json().get("detail", e.response.text)
            st.error(f"   Сообщение: {error_detail}")
        except Exception:
            st.error(f"   Ответ: {e.response.text}")

    except Exception as e:
        # Общая обработка других ошибок
        st.error(f"❌ Произошла непредвиденная ошибка при отображении отчета: {e}")

else:
    # Сообщение, если анализ еще не был запущен
    st.warning("Чтобы увидеть отчет, пожалуйста, сначала загрузите файл и запустите анализ на главной странице.")