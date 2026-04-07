from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import HTMLResponse

from app.api.deps import get_current_user
from app.schemas.legacy import (
    LegacyBlacklistRequest,
    LegacyChatRequest,
    LegacyFilenameRequest,
    LegacyFraudCheckRequest,
    LegacyPredictRequest,
    LegacyScoreFileRequest,
    LegacyTrainingRequest,
)
from app.services import legacy_bridge

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/files")
def read_files() -> list[str]:
    return legacy_bridge.list_files()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Any:
    content = await file.read()
    return legacy_bridge.upload_direct(file.filename or "dataset.csv", content, file.content_type)


@router.get("/columns/{filename}")
def read_columns(filename: str) -> list[str]:
    return legacy_bridge.list_columns(filename)


@router.post("/profile")
def create_profile(payload: LegacyFilenameRequest) -> Any:
    return legacy_bridge.create_profile(payload.filename)


@router.get("/profile-report/{report_filename}", response_class=HTMLResponse)
def read_profile_report(report_filename: str) -> HTMLResponse:
    return HTMLResponse(content=legacy_bridge.get_profile_report(report_filename))


@router.post("/ai/analyze")
def analyze_file(payload: LegacyFilenameRequest) -> Any:
    return legacy_bridge.analyze_file(payload.filename)


@router.post("/ai/chat")
def chat_with_file(payload: LegacyChatRequest) -> Any:
    return legacy_bridge.chat_with_file(
        payload.filename,
        [message.model_dump() for message in payload.chat_history],
    )


@router.get("/models")
def read_models() -> Any:
    return legacy_bridge.list_models()


@router.get("/models/{model_name}/config")
def read_model_config(model_name: str) -> Any:
    return legacy_bridge.get_model_config(model_name)


@router.post("/train-anomaly-detector")
def train_anomaly_detector(payload: LegacyTrainingRequest) -> Any:
    return legacy_bridge.train_anomaly_detector(payload.model_dump())


@router.post("/score-file")
def score_file(payload: LegacyScoreFileRequest) -> Any:
    return legacy_bridge.score_file(payload.model_dump())


@router.post("/predict-or-score")
def predict_or_score(payload: LegacyPredictRequest) -> Any:
    return legacy_bridge.predict_or_score(payload.model_dump())


@router.post("/fraud-check")
def check_fraud(payload: LegacyFraudCheckRequest) -> Any:
    return legacy_bridge.fraud_check(payload.model_dump())


@router.post("/fraud-blacklist")
def add_blacklist(payload: LegacyBlacklistRequest) -> Any:
    return legacy_bridge.add_blacklist(payload.model_dump())
