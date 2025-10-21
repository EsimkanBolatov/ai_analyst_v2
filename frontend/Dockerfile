#frontend\Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Просто копируем все из локальной папки src в /app контейнера
COPY ./src .

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]