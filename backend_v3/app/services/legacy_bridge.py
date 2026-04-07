from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from fastapi import HTTPException

from app.core.config import settings


DEFAULT_TIMEOUT = 180


def _service_error(service_name: str, response: requests.Response) -> HTTPException:
    detail: Any
    try:
        payload = response.json()
        detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
    except ValueError:
        detail = response.text

    status_code = response.status_code if 400 <= response.status_code < 500 else 502
    return HTTPException(
        status_code=status_code,
        detail=f"{service_name} returned an error: {detail}",
    )


def _request_json(
    service_name: str,
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    try:
        response = requests.request(
            method,
            url,
            json=json_payload,
            files=files,
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"{service_name} is unavailable: {exc}") from exc

    if not response.ok:
        raise _service_error(service_name, response)

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{service_name} returned a non-JSON response.",
        ) from exc


def _request_text(
    service_name: str,
    method: str,
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    try:
        response = requests.request(method, url, timeout=timeout)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"{service_name} is unavailable: {exc}") from exc

    if not response.ok:
        raise _service_error(service_name, response)
    return response.text


def list_files() -> list[str]:
    return _request_json("file_service", "GET", f"{settings.file_service_url}/files/", timeout=60)


def upload_direct(filename: str, content: bytes, content_type: str | None) -> Any:
    safe_name = Path(filename).name
    return _request_json(
        "file_service",
        "POST",
        f"{settings.file_service_url}/upload-direct/",
        files={"file": (safe_name, content, content_type or "application/octet-stream")},
    )


def list_columns(filename: str) -> list[str]:
    encoded_filename = quote(filename, safe="")
    return _request_json(
        "file_service",
        "GET",
        f"{settings.file_service_url}/columns/{encoded_filename}",
        timeout=60,
    )


def create_profile(filename: str) -> Any:
    return _request_json(
        "profiling_service",
        "POST",
        f"{settings.profiling_service_url}/profile/",
        json_payload={"filename": filename},
        timeout=300,
    )


def get_profile_report(report_filename: str) -> str:
    encoded_report = quote(report_filename, safe="")
    return _request_text(
        "profiling_service",
        "GET",
        f"{settings.profiling_service_url}/reports/{encoded_report}",
        timeout=120,
    )


def analyze_file(filename: str) -> Any:
    return _request_json(
        "groq_service",
        "POST",
        f"{settings.groq_service_url}/analyze/",
        json_payload={"filename": filename},
        timeout=300,
    )


def chat_with_file(filename: str, chat_history: list[dict[str, Any]]) -> Any:
    return _request_json(
        "groq_service",
        "POST",
        f"{settings.groq_service_url}/chat/",
        json_payload={"filename": filename, "chat_history": chat_history},
        timeout=300,
    )


def list_models() -> Any:
    return _request_json("training_service", "GET", f"{settings.training_service_url}/models/", timeout=60)


def get_model_config(model_name: str) -> Any:
    encoded_model = quote(model_name, safe="")
    return _request_json(
        "training_service",
        "GET",
        f"{settings.training_service_url}/models/{encoded_model}/config",
        timeout=60,
    )


def train_anomaly_detector(payload: dict[str, Any]) -> Any:
    return _request_json(
        "training_service",
        "POST",
        f"{settings.training_service_url}/train_anomaly_detector/",
        json_payload=payload,
        timeout=600,
    )


def score_file(payload: dict[str, Any]) -> Any:
    return _request_json(
        "prediction_service",
        "POST",
        f"{settings.prediction_service_url}/score_file/",
        json_payload=payload,
        timeout=300,
    )


def predict_or_score(payload: dict[str, Any]) -> Any:
    return _request_json(
        "prediction_service",
        "POST",
        f"{settings.prediction_service_url}/predict_or_score/",
        json_payload=payload,
        timeout=180,
    )


def fraud_check(payload: dict[str, Any]) -> Any:
    return _request_json(
        "fraud_check_service",
        "POST",
        f"{settings.fraud_check_service_url}/check/",
        json_payload=payload,
        timeout=120,
    )


def add_blacklist(payload: dict[str, Any]) -> Any:
    return _request_json(
        "fraud_check_service",
        "POST",
        f"{settings.fraud_check_service_url}/add-blacklist/",
        json_payload=payload,
        timeout=120,
    )
