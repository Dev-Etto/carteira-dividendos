"""Exporta o OpenAPI da API para openapi.json na raiz, de onde o front gera os tipos (make types)."""

import json
import os
from pathlib import Path

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def main() -> None:
    os.environ.setdefault("ENABLE_SCHEDULER", "false")
    os.environ.setdefault("INITIAL_SYNC", "false")
    from app.main import app

    OPENAPI_PATH.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
