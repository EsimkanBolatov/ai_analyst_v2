#frontend/src/app
import streamlit as st
import requests
import os
import time
import pandas as pd
import uuid
import math
import tempfile

# --- Конфигурация страницы ---
st.set_page_config(
    page_title="AI-Analyst v2.0",
    page_icon="🌞",
    layout="wide"
)

# --- URL сервисов ---
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8000")
PROFILING_SERVICE_URL = os.getenv("PROFILING_SERVICE_URL", "http://profiling_service:8000")
GROQ_SERVICE_URL = os.getenv("GROQ_SERVICE_URL", "http://groq_service:8000")
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://training_service:8000")


# --- Вспомогательные функции с кэшированием ---

@st.cache_data(ttl=30)
def get_file_list():
    try:
        response = requests.get(f"{FILE_SERVICE_URL}/files/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.toast(
            f"Не удалось получить список файлов от file_service. Убедитесь, что все Docker контейнеры запущены.",
            icon="⚠️"
        )
    return []


@st.cache_data(ttl=60)
def get_model_list():
    try:
        response = requests.get(f"{TRAINING_SERVICE_URL}/models/")
        response.raise_for_status()
        return response.json().get("models", [])
    except requests.exceptions.RequestException as e:
        st.toast(
            f"Не удалось получить список моделей от training_service. Убедитесь, что все Docker контейнеры запущены.",
            icon="⚠️"
        )
    return []


# --- Основной интерфейс Дашборда ---

st.title("🌚 Дашборд AI-Аналитика")
st.markdown("Обзор состояния системы и загрузка новых данных.")

# --- Секция 1: Обзор состояния ---
st.header("Состояние системы")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🗂️ Загруженные файлы")
    file_list = get_file_list()
    if file_list:
        df_files = pd.DataFrame(file_list, columns=["Имя файла"])
        st.dataframe(df_files, width=None, use_container_width=True)
    else:
        st.info("Пока нет загруженных файлов.")

with col2:
    st.subheader("🗿 Обученные модели")
    model_list = get_model_list()
    if model_list:
        df_models = pd.DataFrame(model_list, columns=["Имя модели"])
        st.dataframe(df_models, width=None, use_container_width=True)
    else:
        st.info("Пока нет обученных моделей.")

st.divider()

# --- Секция 2: Загрузка нового файла ---
st.header("Загрузка и анализ нового файла")

uploaded_file = st.file_uploader(
    "Выберите CSV файл для загрузки",
    type=['csv'],
    key="main_uploader"
)
if uploaded_file is not None:
    st.info("Загрузка началась, подождите...")
    tmp = tempfile.NamedTemporaryFile(delete=False)
    CHUNK = 10 * 1024 * 1024  # 10 МБ

    with open(tmp.name, "wb") as f:
        while chunk := uploaded_file.read(CHUNK):
            f.write(chunk)

    st.success(f"Файл сохранён: {tmp.name}")

if st.button("Начать загрузку и анализ", key="main_upload_button"):
    if uploaded_file is not None:
        filename = uploaded_file.name

        CHUNK_SIZE = 10 * 1024 * 1024
        session_id = str(uuid.uuid4())
        total_chunks = math.ceil(uploaded_file.size / CHUNK_SIZE)
        progress_bar = st.progress(0, text="Инициализация загрузки...")

        analysis_successful = True

        try:
            # Загрузка чанков
            for i in range(total_chunks):
                chunk = uploaded_file.read(CHUNK_SIZE)
                if not chunk: break
                files = {'file': (filename, chunk)}
                data = {'session_id': session_id, 'chunk_index': i}
                service_name = "file_service (upload)"
                response = requests.post(f"{FILE_SERVICE_URL}/upload/", files=files, data=data, timeout=1000)
                response.raise_for_status()
                progress_percent = (i + 1) / total_chunks
                progress_bar.progress(progress_percent, text=f"Загрузка... {i + 1}/{total_chunks} частей")

            # Сборка файла
            progress_bar.progress(1.0, text="Файл загружен. Собираем на сервере...")
            assemble_data = {'filename': filename}
            service_name = "file_service (assemble)"
            response = requests.post(f"{FILE_SERVICE_URL}/assemble/{session_id}", data=assemble_data, timeout=1000)
            response.raise_for_status()

            st.success(f"✅ Файл '{filename}' успешно загружен!")
            st.info("Запускаем автоматические анализы...")

            # --- Запуск Профилирования ---
            profile_report_filename = None
            with st.spinner("⏳ Генерируется детальный авто-анализ данных..."):
                profile_req = {"filename": filename}
                service_name = "profiling_service"
                profile_resp = requests.post(f"{PROFILING_SERVICE_URL}/profile/", json=profile_req, timeout=1000)
                profile_resp.raise_for_status()  # Теперь эта строка ловит HTTP ошибки

                st.success("✅ Авто-анализ готов!")
                profile_report_filename = profile_resp.json().get('report_filename')
                if profile_report_filename:
                    st.session_state['last_profile_report'] = profile_report_filename

            # --- Запуск AI-Анализа ---
            analysis_result_json = None
            with st.spinner("🤖 AI-Аналитик (Groq) изучает ваши данные..."):
                groq_req = {"filename": filename}
                service_name = "groq_service"
                groq_resp = requests.post(f"{GROQ_SERVICE_URL}/analyze/", json=groq_req, timeout=1000)
                groq_resp.raise_for_status()  # Ловим HTTP ошибки

                st.success("✅ AI-Анализ завершен!")
                analysis_result_json = groq_resp.json()
                st.session_state['last_analysis_result'] = analysis_result_json
                st.session_state['last_analyzed_filename'] = filename

        except requests.exceptions.RequestException as e:
            analysis_successful = False
            st.error(
                f"❌ Не удалось связаться с сервисом '{service_name}'. "
                f"Пожалуйста, убедитесь, что все Docker-контейнеры запущены ('docker-compose up') "
                f"и попробуйте обновить страницу или повторить действие."
            )

        except requests.exceptions.HTTPError as e:
            analysis_successful = False
            st.error(f"❌ Сервис '{service_name}' вернул ошибку: {e.response.status_code}")
            try:
                error_detail = e.response.json().get("detail", e.response.text)
                st.error(f"   Сообщение: {error_detail}")
            except Exception:
                st.error(f"   Ответ: {e.response.text}")

        except Exception as e:
            # Общая обработка других ошибок
            analysis_successful = False
            st.error(f"❌ Произошла непредвиденная ошибка во время '{service_name}': {e}")

        # --- Финальное сообщение ---
        if analysis_successful:
            st.info("Анализы завершены! Перейдите на страницы 'Data Profile' и 'AI Analyst Report' для просмотра.")
            st.cache_data.clear()
        # else:
        # Сообщения об ошибках уже были выведены выше

    else:
        st.warning("Пожалуйста, выберите файл для загрузки.")