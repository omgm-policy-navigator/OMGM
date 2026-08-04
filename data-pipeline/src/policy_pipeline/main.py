from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any


def load_settings() -> dict[str, str]:
    return {
        "app_env": os.getenv("APP_ENV", "local"),
        "raw_data_dir": os.getenv("POLICY_RAW_DATA_DIR", "data/raw"),
        "processed_data_dir": os.getenv("POLICY_PROCESSED_DATA_DIR", "data/processed"),
        "source_timeout_seconds": os.getenv("POLICY_SOURCE_TIMEOUT_SECONDS", "30"),
    }


def process_sample(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "source": data.get("source", "sample"),
        "policy_count": len(data.get("policies", [])),
        "status": "processed",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Policy data pipeline")
    parser.add_argument("--sample", type=Path, help="Path to a sample policy JSON file")
    return parser


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
    args = build_parser().parse_args()
    settings = load_settings()

    if args.sample:
        result = process_sample(args.sample)
    else:
        result = {"status": "ready", "settings": settings}

    logging.info(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
