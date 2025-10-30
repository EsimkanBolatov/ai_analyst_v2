from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from ydata_profiling import ProfileReport
import os
from fastapi.responses import HTMLResponse

app = FastAPI(title="Data Profiling Service")

# --- Пути ---
UPLOAD_DIR = "/app/uploads"
REPORTS_DIR = "/app/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


class ProfileRequest(BaseModel):
    filename: str


@app.post("/profile/")
async def create_profile(request: ProfileRequest):

    file_path = os.path.join(UPLOAD_DIR, request.filename)
    report_filename = f"{os.path.splitext(request.filename)[0]}_profile.html"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

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