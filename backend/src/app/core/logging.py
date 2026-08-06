from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEY = re.compile(r"(authorization|cookie|token|password|secret|api[_-]?key|income|asset)", re.I)
EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
PHONE = re.compile(r"(?<!\d)(?:01[016789][ -]?\d{3,4}[ -]?\d{4})(?!\d)")
BEARER_TOKEN = re.compile(r"\bBearer\s+[^\s,;]+", re.I)
DATABASE_URL = re.compile(r"\b(?:postgres(?:ql)?|mysql|mariadb)\+?[^\s]*://[^\s]+", re.I)


def sanitize_log_text(value: str) -> str:
    value = DATABASE_URL.sub("[DATABASE_URL]", value)
    value = BEARER_TOKEN.sub("Bearer [REDACTED]", value)
    value = EMAIL.sub("[EMAIL]", value)
    return PHONE.sub("[PHONE]", value)


def mask_sensitive(value: Any, key: str = "") -> Any:
    if SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item_key: mask_sensitive(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask_sensitive(item) for item in value]
    if isinstance(value, str):
        return sanitize_log_text(value)
    return value


class JsonFormatter(logging.Formatter):
    RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": sanitize_log_text(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = mask_sensitive(value, key)
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
