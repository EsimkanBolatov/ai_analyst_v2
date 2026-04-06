from pathlib import Path

import requests

from app.core.config import settings


def store_file_via_file_service(filename: str, content: bytes) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    safe_name = Path(filename).name
    try:
        response = requests.post(
            f"{settings.file_service_url}/upload-direct/",
            files={"file": (safe_name, content)},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("filename") or safe_name, warnings
    except Exception as exc:
        warnings.append(f"File service unavailable: {exc}")
        return None, warnings
