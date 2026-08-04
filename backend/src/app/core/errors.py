from __future__ import annotations

from http import HTTPStatus


class AppError(Exception):
    def __init__(self, code: str, public_message: str, status_code: HTTPStatus) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.status_code = status_code


class ConfigurationError(AppError):
    def __init__(self, public_message: str) -> None:
        super().__init__("CONFIGURATION_ERROR", public_message, HTTPStatus.INTERNAL_SERVER_ERROR)
