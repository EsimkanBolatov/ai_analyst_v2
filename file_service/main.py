#file_service/main.py
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import pandas as pd

# Создаем папку для загрузок, если ее нет
# ИСПРАВЛЕНИЕ: Используем абсолютный путь внутри контейнера
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="File Ingestion Service")

# --- Настройка CORS ---
# Позволяет нашему фронтенду (с другого порта) общаться с этим сервисом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В реальном проекте здесь должен быть адрес фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload/")
async def upload_chunk(
    file: UploadFile = File(...),
    session_id: str = Form(...), # Уникальный ID для каждой сессии загрузки
    chunk_index: int = Form(...) # Номер текущей части файла
):
    """
    Принимает одну часть (чанк) файла и сохраняет ее.
    """
    try:
        # Создаем папку для конкретной сессии загрузки
        session_path = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_path, exist_ok=True)

        # Сохраняем чанк во временный файл
        chunk_path = os.path.join(session_path, f"chunk_{chunk_index}")
        with open(chunk_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"status": "success", "message": f"Chunk {chunk_index} uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assemble/{session_id}")
async def assemble_chunks(
    session_id: str,
    filename: str = Form(...) # Имя оригинального файла
):
    """
    Собирает все чанки в один финальный файл.
    """
    session_path = os.path.join(UPLOAD_DIR, session_id)
    final_file_path = os.path.join(UPLOAD_DIR, filename)

    try:
        # Получаем список всех чанков и сортируем их по номеру
        chunks = sorted(
            os.listdir(session_path),
            key=lambda x: int(x.split('_')[1])
        )

        # "Склеиваем" чанки в один файл
        with open(final_file_path, "wb") as final_file:
            for chunk_name in chunks:
                chunk_path = os.path.join(session_path, chunk_name)
                with open(chunk_path, "rb") as chunk_file:
                    final_file.write(chunk_file.read())

        # Удаляем временную папку с чанками
        shutil.rmtree(session_path)

        return {"status": "success", "message": f"File '{filename}' assembled successfully at {final_file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/columns/{filename}")
async def get_columns(filename: str):
    """
    Читает CSV-файл и возвращает список его колонок (с расширенным логированием).
    """
    print(f"--- Получен запрос на получение колонок для файла: {filename} ---")
    file_path = os.path.join(UPLOAD_DIR, filename)
    print(f"Пытаюсь прочитать файл по абсолютному пути: {file_path}")

    if not os.path.exists(file_path):
        print(f"ОШИБКА: Файл не существует по пути: {file_path}")
        raise HTTPException(status_code=404, detail=f"Файл не найден по пути {file_path}")
    try:
        print("Файл существует. Пытаюсь прочитать его с помощью pandas...")
        df_head = pd.read_csv(file_path, nrows=0)
        columns = df_head.columns.tolist()
        print(f"Успешно прочитаны колонки: {columns}")
        return {"columns": columns}
    except Exception as e:
        # ЭТО САМОЕ ВАЖНОЕ: МЫ ВЫВЕДЕМ ТОЧНУЮ ОШИБКУ В ЛОГИ
        print(f"!!!!!!!!!! ОШИБКА ВНУТРИ PANDAS !!!!!!!!!")
        print(f"Точная ошибка: {e}")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении колонок файла: {str(e)}")