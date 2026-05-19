import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.dependencies.logger import logger


REQUEST_FILE = os.getenv(
    "NAVIDROME_HOOK_REQUEST_FILE",
    "/app/data/navidrome_refresh/request.json",
)


def request_navidrome_refresh(
    reason: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Signal the host-level Navidrome refresh hook without blocking the app flow."""
    try:
        request_dir = os.path.dirname(REQUEST_FILE)
        os.makedirs(request_dir, exist_ok=True)

        request_payload = {
            "reason": reason,
            "payload": payload or {},
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        tmp_file = f"{REQUEST_FILE}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as file:
            json.dump(request_payload, file, ensure_ascii=False)
        os.replace(tmp_file, REQUEST_FILE)
        logger.info(f"已送出 Navidrome refresh hook: {reason}")
    except Exception as exc:
        logger.warning(f"送出 Navidrome refresh hook 失敗: {exc}")
