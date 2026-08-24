# src\logging_exception\exception\custom_exception.py

"""
Custom exception with structured logging and sensitive data masking.
"""

import os
import sys
import logging
import re
from typing import Optional, Any, Dict
from src.logging_exception.logging.logger import logger


class CustomException(Exception):
    """
    Exception that logs a single structured entry with sensitive data masked.
    """

    # Common sensitive field names
    SENSITIVE_KEYS = {
        'api_key', 'secret', 'token', 'password', 'passwd', 'key',
        'auth', 'authorization', 'bearer', 'credential', 'pwd',
        'access_token', 'refresh_token', 'client_secret', 'private_key'
    }

    def __init__(
        self,
        error_message: str,
        error_details: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        log_level: int = logging.ERROR,
    ):
        self.error_message = str(error_message)
        self.context = self._mask_sensitive_data(context or {})
        self.log_level = log_level

        # Get exception info
        self.exc_type, self.exc_value, self.exc_tb = self._get_exception_info(error_details)

        # Log it
        self._log_exception()

        super().__init__(self.error_message)

    @classmethod
    def _mask_sensitive_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive values in dict."""
        if not data:
            return {}
        
        masked = {}
        for key, value in data.items():
            # Check if this key is sensitive
            key_lower = key.lower()
            is_sensitive = (
                key_lower in cls.SENSITIVE_KEYS or 
                any(s in key_lower for s in ['pass', 'secret', 'token', 'key', 'auth'])
            )
            
            if is_sensitive and value is not None:
                # Mask the value
                if isinstance(value, str) and len(value) > 8:
                    masked[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    masked[key] = '[MASKED]'
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                masked[key] = cls._mask_sensitive_data(value)
            else:
                masked[key] = value
        
        return masked

    def _get_exception_info(self, error_details):
        """Extract exception type, value, and traceback."""
        if error_details is None:
            return sys.exc_info()
        if isinstance(error_details, BaseException):
            return type(error_details), error_details, error_details.__traceback__
        return None, None, None

    def _log_exception(self):
        """Log a single structured entry."""
        # Build log payload
        payload = {
            'event': self.error_message,
            'error_type': self.exc_type.__name__ if self.exc_type else "UnknownError",
        }

        # Add masked context
        if self.context:
            payload.update(self.context)

        # Add cause if different
        if self.exc_value and str(self.exc_value) != self.error_message:
            payload['cause'] = str(self.exc_value)

        # Let structlog handle traceback via exc_info
        if self.exc_tb and os.getenv("LOG_FULL_TRACEBACK", "0") == "1":
            payload['exc_info'] = (self.exc_type, self.exc_value, self.exc_tb)

        # Log at appropriate level
        if self.log_level >= logging.ERROR:
            logger.error(**payload)
        elif self.log_level >= logging.WARNING:
            logger.warning(**payload)
        else:
            logger.info(**payload)

    def __str__(self):
        return f"{self.error_message} ({self.exc_type.__name__ if self.exc_type else 'Error'})"