#frontend/src/app.py
import streamlit as st
import requests
import uuid
import math
import json

# --- Настройки ---
FILE_SERVICE_URL = "http://file_service:8000"
GROQ_SERVICE_URL = "http://groq_service:8000"
PROFILING_SERVICE_URL = "http://profiling_service:8000"
CHUNK_SIZE = 1024 * 1024 * 10 # 10 МБ (этот размер теперь менее важен)

# --- Интерфейс ---
st.set_page_config(page_title="AI-Analyst v2.0", layout="wide")
st.title("🚀 AI-Analyst v2.0: Платформа для интеллектуального анализа данных")
st.subheader("Шаг 1: Загрузите ваш файл для анализа")

# --- ВОЗВРАЩАЕМ СТАНДАРТНЫЙ ЗАГРУЗЧИК ---
uploaded_file = st.file_uploader(
    "Выберите CSV файл (максимум 200 МБ)", # Обновляем текст
    type="csv"
)

if uploaded_file is not None:
    st.success(f"Файл '{uploaded_file.name}' готов к загрузке на сервер.")

    if st.button("Начать загрузку и анализ"):
        session_id = str(uuid.uuid4())
        total_chunks = math.ceil(uploaded_file.size / CHUNK_SIZE)
        progress_bar = st.progress(0, text="Инициализация загрузки...")

        try:
            # --- ВОЗВРАЩАЕМ ЛОГИКУ ПОБЛОЧНОЙ ЗАГРУЗКИ В PYTHON ---
            # Эта логика будет работать только для файлов < 200 МБ
            for i in range(total_chunks):
                chunk = uploaded_file.read(CHUNK_SIZE)
                if not chunk: break
                files = {'file': (uploaded_file.name, chunk)}
                data = {'session_id': session_id, 'chunk_index': i}
                response = requests.post(f"{FILE_SERVICE_URL}/upload/", files=files, data=data)
                response.raise_for_status()
                progress_percent = (i + 1) / total_chunks
                progress_bar.progress(progress_percent, text=f"Загрузка... {i + 1}/{total_chunks} частей")

            # --- Сборка файла на сервере ---
            progress_bar.progress(1.0, text="Файл загружен. Собираем на сервере...")
            assemble_data = {'filename': uploaded_file.name}
            response = requests.post(f"{FILE_SERVICE_URL}/assemble/{session_id}", data=assemble_data)
            response.raise_for_status()

            st.success("✅ Файл успешно загружен!")

            # --- ПОСЛЕДОВАТЕЛЬНЫЙ ЗАПУСК АНАЛИЗОВ ---
            # ... (Этот блок остается без изменений) ...
            with st.spinner("⏳ Генерируется быстрый авто-анализ данных..."):
                 profile_req = {"filename": uploaded_file.name}
                 profile_resp = requests.post(f"{PROFILING_SERVICE_URL}/profile/", json=profile_req)

            if profile_resp.status_code == 200:
                st.session_state['profile_report_filename'] = profile_resp.json()['report_filename']
                st.success("✅ Авто-анализ готов!")
            else:
                st.error(f"❌ Ошибка при генерации авто-анализа: {profile_resp.text}")

            with st.spinner("🤖 AI-Аналитик (Groq) изучает ваши данные..."):
                groq_req = {"filename": uploaded_file.name}
                groq_resp = requests.post(f"{GROQ_SERVICE_URL}/analyze/", json=groq_req)

            if groq_resp.status_code == 200:
                st.session_state['analysis_result'] = groq_resp.json()
                st.session_state['filename'] = uploaded_file.name
                st.success("✅ AI-Анализ завершен!")
            else:
                st.error(f"❌ Ошибка при AI-анализе: {groq_resp.json().get('detail', groq_resp.text)}")

            st.info("Результаты готовы! Перейдите на соответствующие страницы, чтобы их увидеть.")

        except Exception as e:
            st.error(f"❌ Произошла непредвиденная ошибка: {e}")