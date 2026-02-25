FROM python:3.10-slim

ENV PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=10

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --timeout 180 --retries 10 -r /app/requirements.txt

RUN pip install --no-cache-dir --timeout 180 --retries 10 \
    https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.8.0/ru_core_news_sm-3.8.0-py3-none-any.whl

COPY . /app

RUN chmod +x /app/wait-for-it.sh

CMD /app/wait-for-it.sh db:5432 && uvicorn main:app --host 0.0.0.0 --port 8000

