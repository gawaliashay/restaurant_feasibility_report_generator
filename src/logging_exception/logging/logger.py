# src/logging_exception/logging/logger.py

import os
import sys
import logging
import re
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
import structlog

LOG_CONSOLE_DEV = os.getenv("LOG_CONSOLE_DEV", "0") == "1"
LOG_JSON = os.getenv("LOG_JSON", "1") != "0"

LOGGER_PATH = os.path.abspath(__file__).replace("\\", "/")
PROJECT_ROOT = os.path.abspath(os.getcwd()).replace("\\", "/")


class SensitiveDataProcessor:
    def __init__(self):
        self.sensitive_patterns = [
            r'api_key[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'api_key\s*=\s*[^\s,]+',
            r'OPENAI_API_KEY=[^\s]+',
            r'MISTRAL_API_KEY=[^\s]+',
            r'GROQ_API_KEY=[^\s]+',
            r'PINECONE_API_KEY=[^\s]+',
            r'HUGGINGFACEHUB_API_TOKEN=[^\s]+',
            r'GOOGLE_API_KEY=[^\s]+',
            r'S3_BUCKET=[^\s]+',
            r'secret[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'token[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'password[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'key[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
        ]

        self.sensitive_keys = {
            'api_key', 'api_secret', 'secret', 'token', 'password', 'key',
            'mistral_api_key', 'openai_api_key', 'groq_api_key',
            'pinecone_api_key', 'huggingfacehub_api_token', 'google_api_key'
        }

    def __call__(self, logger, method_name, event_dict):
        if 'event' in event_dict:
            event_dict['event'] = self._mask_sensitive_string(str(event_dict['event']))

        for key in list(event_dict):
            val = event_dict[key]
            if key in self.sensitive_keys:
                event_dict[key] = '[MASKED]'
            elif isinstance(val, str):
                event_dict[key] = self._mask_sensitive_string(val)
            elif isinstance(val, dict):
                event_dict[key] = self._mask_sensitive_dict(val)

        return event_dict

    def _mask_sensitive_string(self, text):
        for pattern in self.sensitive_patterns:
            text = re.sub(pattern, self._mask_replacement, text)
        return text

    def _mask_sensitive_dict(self, obj):
        if not isinstance(obj, dict):
            return obj
        masked = {}
        for key, value in obj.items():
            if key in self.sensitive_keys:
                masked[key] = '[MASKED]'
            elif isinstance(value, str):
                masked[key] = self._mask_sensitive_string(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_dict(value)
            elif isinstance(value, list):
                masked[key] = [
                    self._mask_sensitive_dict(i) if isinstance(i, dict)
                    else self._mask_sensitive_string(i) if isinstance(i, str)
                    else i
                    for i in value
                ]
            else:
                masked[key] = value
        return masked

    def _mask_replacement(self, match):
        text = match.group(0)
        if '=' in text:
            k, _ = text.split('=', 1)
            return f"{k}=[MASKED]"
        if ':' in text:
            k, _ = text.split(':', 1)
            return f"{k}:[MASKED]"
        return '[MASKED]'


def callsite(logger, method_name, event_dict):
    for frame in inspect.stack():
        path = frame.filename.replace("\\", "/")
        if PROJECT_ROOT in path and "/site-packages/" not in path and path != LOGGER_PATH:
            event_dict["file"] = os.path.basename(path)
            event_dict["function"] = frame.function
            event_dict["line"] = frame.lineno
            break
    return event_dict


class CustomLogger:
    _configured = False

    def __init__(self, log_dir="logs", log_level=logging.INFO, max_bytes=10_000_000, backup_count=5):
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        self.log_file_path = os.path.join(
            self.logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log"
        )
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        if not CustomLogger._configured:
            self._configure_structlog()
            CustomLogger._configured = True

    def _configure_structlog(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        if not root_logger.handlers:
            file_handler = RotatingFileHandler(
                self.log_file_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(self.log_level)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)

            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

        def key_order_processor(logger, method_name, event_dict):
            key_order = [
                "timestamp", "level", "event", "file", "function", "line",
                "message", "context", "traceback"
            ]
            ordered = {k: event_dict[k] for k in key_order if k in event_dict}
            ordered.update({k: v for k, v in event_dict.items() if k not in ordered})
            return ordered

        sensitive_processor = SensitiveDataProcessor()

        if LOG_CONSOLE_DEV and not LOG_JSON:
            renderer = structlog.dev.ConsoleRenderer()
        else:
            renderer = structlog.processors.JSONRenderer(sort_keys=False)

        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.format_exc_info,
                callsite,
                sensitive_processor,
                key_order_processor,
                renderer,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def get_logger(self, name: Optional[str] = None):
        return structlog.get_logger(name or __name__)

    @staticmethod
    def log_separator():
        structlog.get_logger("separator").info("=" * 80)


logger = CustomLogger().get_logger(__name__)
