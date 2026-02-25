from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from app.services.data_processor import DataProcessor

router = APIRouter()
processor = DataProcessor()

UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload_data")
async def upload_data(
        transactions: UploadFile = File(...),
        behavior: UploadFile = File(...)
):
    """
    Принимает два CSV файла, сохраняет их и запускает объединение.
    """
    trx_path = os.path.join(UPLOAD_DIR, "transactions.csv")
    beh_path = os.path.join(UPLOAD_DIR, "behavior.csv")

    # Сохраняем файлы
    with open(trx_path, "wb") as buffer:
        shutil.copyfileobj(transactions.file, buffer)

    with open(beh_path, "wb") as buffer:
        shutil.copyfileobj(behavior.file, buffer)

    try:
        # Запускаем логику объединения и генерации фичей
        df = processor.load_and_merge(trx_path, beh_path)
        df = processor.generate_features()

        # Сохраняем "Супер-таблицу" для обучения
        processed_path = os.path.join(UPLOAD_DIR, "processed_train_data.csv")
        df.to_csv(processed_path, index=False)

        return {
            "status": "success",
            "message": "Files uploaded and processed successfully",
            "rows_count": len(df),
            "columns": list(df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))