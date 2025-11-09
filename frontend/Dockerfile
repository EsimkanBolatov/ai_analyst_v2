# frontend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем настройки Streamlit
COPY .streamlit/ .streamlit/

# Копируем исходники приложения
COPY ./src .

# Открываем порт Streamlit
EXPOSE 8501

# Запускаем с безопасными флагами и увеличенным буфером
CMD ["streamlit", "run", "app.py", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
