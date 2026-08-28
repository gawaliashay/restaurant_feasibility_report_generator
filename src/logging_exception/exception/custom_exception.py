# src/logging_exception/exception/custom_exception.py

"""Log once on raise; optional chained cause from error_details."""

import os
import sys
from typing import Any

from src.logging_exception.logging.logger import logger


class CustomException(Exception):
    def __init__(self, error_message: str, error_details: Any = None):
        self.error_message = str(error_message)
        self.exc_type, self.exc_value, self.exc_tb = self._exception_info(error_details)

        payload: dict[str, Any] = {
            "event": self.error_message,
            "error_type": self.exc_type.__name__ if self.exc_type else "UnknownError",
        }
        if self.exc_value and str(self.exc_value) != self.error_message:
            payload["cause"] = str(self.exc_value)
        if self.exc_tb and os.getenv("LOG_FULL_TRACEBACK", "0") == "1":
            payload["exc_info"] = (self.exc_type, self.exc_value, self.exc_tb)

        logger.error(**payload)
        super().__init__(self.error_message)

    @staticmethod
    def _exception_info(error_details: Any):
        if error_details is None:
            return sys.exc_info()
        if isinstance(error_details, BaseException):
            return type(error_details), error_details, error_details.__traceback__
        return None, None, None

    def __str__(self) -> str:
        name = self.exc_type.__name__ if self.exc_type else "Error"
        return f"{self.error_message} ({name})"
