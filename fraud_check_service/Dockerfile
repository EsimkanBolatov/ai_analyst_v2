FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

RUN python -m spacy download ru_core_news_sm

COPY . /app

RUN chmod +x /app/wait-for-it.sh

CMD /app/wait-for-it.sh db:5432 && uvicorn main:app --host 0.0.0.0 --port 8000

