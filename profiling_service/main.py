from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from ydata_profiling import ProfileReport
import os
from fastapi.responses import HTMLResponse
import requests

app = FastAPI(title="Data Profiling Service")

# --- Пути ---
UPLOAD_DIR = "/app/uploads"
REPORTS_DIR = "/app/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8000")


class ProfileRequest(BaseModel):
    filename: str


def _ensure_uploaded_file(filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return file_path

    try:
        response = requests.get(f"{FILE_SERVICE_URL}/download/{filename}", timeout=120, stream=True)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="File not found")
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return file_path
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch file from file_service: {e}")


@app.post("/profile/")
async def create_profile(request: ProfileRequest):

    file_path = _ensure_uploaded_file(request.filename)
    report_filename = f"{os.path.splitext(request.filename)[0]}_profile.html"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    try:
        df = pd.read_csv(file_path)
        profile = ProfileReport(df, title=f"Анализ данных: {request.filename}")
        profile.to_file(report_path)

        return {"status": "success", "report_filename": report_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{report_filename}", response_class=HTMLResponse)
async def get_report(report_filename: str):
    report_path = os.path.join(REPORTS_DIR, report_filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
