#frontend/src/pages/1_AI_Analyst_Report.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Отчет AI-Аналитика", layout="wide")
st.title("📊 Отчет AI-Аналитика")

if 'analysis_result' in st.session_state:
    result = st.session_state['analysis_result']
    filename = st.session_state['filename']

    st.header(f"Анализ файла: `{filename}`")

    # Используем вкладки для структурирования отчета
    tab1, tab2, tab3 = st.tabs(["📌 Основные выводы", "🚨 Примеры аномалий", "💡 Рекомендации и идеи"])

    with tab1:
        st.subheader("Ключевые наблюдения от AI")
        st.info(result.get('main_findings', "Нет данных."))

    with tab2:
        st.subheader("Обнаруженные подозрительные записи")
        anomalies = result.get('anomalies', [])
        if not anomalies:
            st.write("AI не обнаружил явных аномалий в предоставленной выборке.")
        for anomaly in anomalies:
            with st.expander(f"Строка {anomaly.get('row_index', 'N/A')}: {anomaly.get('reason', 'Нет объяснения.')}"):
                if anomaly.get('data'):
                    st.dataframe(pd.DataFrame([anomaly['data']]))

    with tab3:
        st.subheader("Идеи по созданию новых признаков (Feature Engineering)")
        ideas = result.get('feature_engineering_ideas', [])
        if not ideas:
            st.write("AI не предложил идей по созданию новых признаков.")
        for i, idea in enumerate(ideas):
            st.markdown(f"**{i + 1}.** {idea}")

        st.subheader("Что делать дальше?")
        st.warning(result.get('recommendations', "Нет данных."))
else:
    st.info("Чтобы увидеть отчет, пожалуйста, сначала загрузите файл на главной странице.")