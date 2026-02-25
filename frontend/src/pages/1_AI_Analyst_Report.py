import streamlit as st
import requests
import os
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

# --- Конфигурация страницы ---
st.set_page_config(
    page_title="AI Analyst Report",
    page_icon="🤖",
    layout="wide"
)

# --- URL сервисов ---
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8000")
GROQ_SERVICE_URL = os.getenv("GROQ_SERVICE_URL", "http://groq_service:8000")

# --- Вспомогательные функции ---
def get_analyzed_file():
    return st.session_state.get("last_analyzed_filename")

def set_analyzed_file(filename):
    st.session_state["last_analyzed_filename"] = filename
    if "chat_history" in st.session_state:
        del st.session_state["chat_history"]
    if "last_analysis_result" in st.session_state:
        del st.session_state['last_analysis_result']

@st.cache_data(ttl=30)
def get_file_list():
    try:
        response = requests.get(f"{FILE_SERVICE_URL}/files/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.toast(f"Warning: Could not fetch file list: {e}", icon="⚠️")
    return []


# --- Основной интерфейс страницы ---
st.title("🤖 Отчет AI-Аналитика")
st.markdown("Выберите загруженный датасет для получения анализа от AI (на базе Groq) или просмотра предыдущего анализа.")

# --- Блок выбора файла ---
st.subheader("1. Выберите файл для анализа")
file_list = get_file_list()
if not file_list:
    st.warning("Не найдено загруженных файлов.")
    st.stop()

selected_file = st.selectbox(
    "Выберите файл из списка:",
    options=file_list,
    index=file_list.index(get_analyzed_file()) if get_analyzed_file() in file_list else None,
    placeholder="Выберите файл..."
)

# --- Кнопка для запуска НОВОГО анализа ---
if st.button("Запустить новый анализ для выбранного файла", key="analyze_button"):
    if selected_file:
        set_analyzed_file(selected_file)
        with st.spinner("🤖 AI-Аналитик изучает данные..."):
            service_name = "groq_service (analyze)"
            try:
                groq_req = {"filename": selected_file}
                groq_resp = requests.post(f"{GROQ_SERVICE_URL}/analyze/", json=groq_req, timeout=180)
                groq_resp.raise_for_status()
                analysis_data = groq_resp.json()
                st.session_state["last_analysis_result"] = analysis_data
                st.session_state["chat_history"] = [{"role": "assistant", "content": json.dumps(analysis_data)}]
                st.success("Новый анализ завершен!")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Не удалось связаться с '{service_name}'. Проверьте Docker.")
            except requests.exceptions.HTTPError as e:
                 st.error(f"❌ Сервис '{service_name}' вернул ошибку: {e.response.status_code}")
            except Exception as e:
                 st.error(f"❌ Непредвиденная ошибка при анализе: {e}")
    else:
        st.warning("Пожалуйста, выберите файл.")

# --- Блок отображения отчета и чата ---
current_analysis = st.session_state.get("last_analysis_result")
current_filename = st.session_state.get("last_analyzed_filename")

if current_analysis and selected_file == current_filename:

    st.header(f"2. Результаты анализа для файла: {current_filename}")

    # --- Текстовые результаты ---
    with st.container(border=True):
        st.subheader("📝 Основные выводы")
        st.write(current_analysis.get("main_findings", "Нет данных."))
        st.subheader("💡 Идеи Feature Engineering")
        for idea in current_analysis.get("feature_engineering_ideas", []):
            st.markdown(f"- {idea}")
        st.subheader("📑 Рекомендации")
        st.write(current_analysis.get("recommendations", "Нет данных."))


    # --- Распределение Сумм Транзакций ---
    st.header("Распределение Сумм Транзакций (transaction_amount_kzt)")
    dist_stats = current_analysis.get("amount_distribution_stats")

    if dist_stats and dist_stats.get("count", 0) > 0:
        st.subheader("📊 Ключевые статистики (по первым 100 строкам)")
        stats_cols = st.columns(5)
        stats_cols[0].metric("Минимум", f"{dist_stats.get('min_val', 'N/A'):,.2f}")
        stats_cols[1].metric("25% (Q1)", f"{dist_stats.get('p25', 'N/A'):,.2f}")
        stats_cols[2].metric("Медиана (Q2)", f"{dist_stats.get('median', 'N/A'):,.2f}")
        stats_cols[3].metric("75% (Q3)", f"{dist_stats.get('p75', 'N/A'):,.2f}")
        stats_cols[4].metric("Максимум", f"{dist_stats.get('max_val', 'N/A'):,.2f}")
        st.metric("Среднее", f"{dist_stats.get('mean_val', 'N/A'):,.2f}")
        st.caption(f"Статистика рассчитана по {dist_stats.get('count')} значениям.")

        # Строим Box Plot
        st.subheader("График Box Plot (Ящик с усами)")
        try:
            fig_box = go.Figure()
            fig_box.add_trace(go.Box(
                name='Amount Distribution',
                q1=[dist_stats.get('p25')],
                median=[dist_stats.get('median')],
                q3=[dist_stats.get('p75')],
                lowerfence=[dist_stats.get('min_val')],
                upperfence=[dist_stats.get('max_val')],
                mean=[dist_stats.get('mean_val')],
                sd=[0],
                boxpoints=False
            ))
            fig_box.update_layout(
                 title="Распределение transaction_amount_kzt (Box Plot)",
                 yaxis_title="Сумма (KZT)"
            )
            st.plotly_chart(fig_box, use_container_width=True)
            st.info("""
            **Как читать Box Plot:**
            * **Ящик:** Показывает диапазон между 25-м (Q1) и 75-м (Q3) перцентилями. Внутри него находится 50% данных.
            * **Линия внутри ящика:** Медиана (50-й перцентиль).
            * **Усы:** Линии, идущие от ящика к минимальному и максимальному значениям (в данном случае).
            * **Точка (если есть):** Среднее значение.
            Длинные усы или большой разрыв между медианой и средним могут указывать на выбросы (аномально большие/маленькие суммы).
            """)
        except Exception as plot_err:
             st.warning(f"Не удалось построить Box Plot: {plot_err}")

    else:
        st.info("Статистика распределения сумм не была получена от AI-аналитика.")


    # --- Визуализация аномалий Scatter Plot ---
    st.header("Найденные аномалии")
    anomalies = current_analysis.get("anomalies", [])
    if anomalies:
        plot_data_list = []
        for anom in anomalies:
            p_data = anom.get("plot_data")
            if p_data:
                 plot_data_list.append({
                     "index": anom.get("row_index"), "reason": anom.get("reason", "N/A"),
                     "amount": p_data.get("transaction_amount_kzt"), "hour": p_data.get("transaction_hour"),
                     "category": p_data.get("mcc_category", "Unknown")
                 })
                 
        if plot_data_list:
            df_plot = pd.DataFrame(plot_data_list)
            
            # Очищаем данные от NaN и подготавливаем размер точек
            df_plot_clean = df_plot.dropna(subset=['amount', 'hour']).copy()
            
            if not df_plot_clean.empty:
                # Plotly требует, чтобы size был строго >= 0. Берем абсолютное значение.
                df_plot_clean['point_size'] = df_plot_clean['amount'].abs()
                
                st.subheader("📈 Интерактивный график аномалий (Сумма vs Час)")
                fig = px.scatter(
                    df_plot_clean, 
                    x="hour", 
                    y="amount", 
                    color="category", 
                    size="point_size", 
                    hover_name="index", 
                    hover_data={"reason": True, "category": True, "amount": True, "hour": True, "point_size": False},
                    title="Аномальные транзакции: Сумма vs Час", 
                    labels={"hour": "Час", "amount": "Сумма (KZT)"}
                )
                fig.update_layout(xaxis=dict(range=[-1, 24]))
                st.plotly_chart(fig, use_container_width=True)
            else: 
                st.info("Недостаточно данных для графика аномалий (у найденных аномалий отсутствуют суммы или часы).")
                 
        st.subheader("Таблица аномалий")
        anomalies_for_table = [{k: v for k, v in anom.items() if k != 'plot_data'} for anom in anomalies]
        df_anomalies = pd.DataFrame(anomalies_for_table)
        st.dataframe(df_anomalies, width=None, use_container_width=True)
    else: 
        st.info("Аномалии не выделены.")

    # -------------- Чат  ------------------------
    st.header("3. 💬 Чат с AI-Аналитиком")
    st.markdown("Задайте уточняющий вопрос по отчету выше.")
    if "chat_history" in st.session_state:
        for msg in st.session_state.chat_history[1:]:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
                
    if prompt := st.chat_input("Ваш вопрос..."):
        if "chat_history" not in st.session_state: st.session_state.chat_history = []
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Думаю..."):
                service_name = "groq_service (chat)"
                try:
                    chat_req = {"filename": current_filename, "chat_history": st.session_state.chat_history}
                    chat_resp = requests.post(f"{GROQ_SERVICE_URL}/chat/", json=chat_req, timeout=180)
                    chat_resp.raise_for_status()
                    response_data = chat_resp.json()
                    response_content = response_data.get("content")
                    st.markdown(response_content)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_content})
                except requests.exceptions.RequestException as e: st.error(f"❌ Не удалось связаться с '{service_name}'.")
                except requests.exceptions.HTTPError as e: st.error(f"❌ Сервис '{service_name}' вернул ошибку: {e.response.status_code}")
                except Exception as e: st.error(f"❌ Непредвиденная ошибка в чате: {e}")

elif selected_file:
     st.info(f"Для файла '{selected_file}' еще не был запущен анализ. Нажмите кнопку выше.")