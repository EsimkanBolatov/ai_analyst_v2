#frontend\Dockerfile
FROM python:3.10-slim

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY ./src .

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
