#file_service/main.py
import os
import shutil
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="File Ingestion Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Принимает одну часть (чанк) файла и сохраняет ее

    try:
        session_path = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_path, exist_ok=True)

        chunk_path = os.path.join(session_path, f"chunk_{chunk_index}")
        with open(chunk_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"status": "success", "message": f"Chunk {chunk_index} uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assemble/{session_id}")
async def assemble_chunks(
    session_id: str,
    filename: str = Form(...)
):
    session_path = os.path.join(UPLOAD_DIR, session_id)
    final_file_path = os.path.join(UPLOAD_DIR, filename)

    try:
        chunks = sorted(
            os.listdir(session_path),
            key=lambda x: int(x.split('_')[1])
        )
        with open(final_file_path, "wb") as final_file:
            for chunk_name in chunks:
                chunk_path = os.path.join(session_path, chunk_name)
                with open(chunk_path, "rb") as chunk_file:
                    final_file.write(chunk_file.read())
        shutil.rmtree(session_path)

        return {"status": "success", "message": f"File '{filename}' assembled successfully at {final_file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/", response_model=List[str])
async def get_uploaded_files():
    try:
        files = [f for f in os.listdir(UPLOAD_DIR) if
                 f.endswith('.csv') and os.path.isfile(os.path.join(UPLOAD_DIR, f))]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read upload directory: {e}")


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type="text/csv")


# --- Эндпоинт получения колонок ---
@app.get("/columns/{filename}", response_model=List[str])
async def get_file_columns(filename: str):
    """
    Читает CSV-файл (только заголовки)
    и возвращает список имен колонок
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    logger.info(f"Запрос колонок для файла: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")  # <-- Логирование
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Читаем первую строку, явно указывая, что это header
        df_cols = pd.read_csv(file_path, nrows=0, header=0)

        column_list = df_cols.columns.tolist()

        logger.info(f"Найденные колонки: {column_list}")

        # Проверка на странный баг
        if column_list == ["columns"]:
            logger.warning("Pandas вернул ['columns']. Похоже, файл не имеет шапки.")
            df_cols_no_header = pd.read_csv(file_path, nrows=0, header=None)
            column_list_no_header = [str(c) for c in df_cols_no_header.columns.tolist()]
            logger.info(f"Попытка 2 (без шапки): {column_list_no_header}")
            return column_list_no_header

        return column_list

    except pd.errors.EmptyDataError:
        logger.warning(f"Файл пустой: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Не удалось прочитать колонки: {e}")
        raise HTTPException(status_code=500, detail=f"Could not read file columns: {e}")
