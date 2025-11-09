#profiling_service/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --timeout=100 --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]