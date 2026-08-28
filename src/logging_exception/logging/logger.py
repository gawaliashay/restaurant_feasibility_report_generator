# src\logging_exception\logging\logger.py

"""
Structured logging: run_id, rotating file, readable console, sensitive-field masking.
"""

import logging
import os
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

import structlog
from structlog.contextvars import bind_contextvars

from src.utils.create_unique_uuid import generate_uuid

LOG_CONSOLE_DEV = os.getenv("LOG_CONSOLE_DEV", "1") == "1"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = (os.getenv("LOG_DIRECTORY") or "logs").rstrip("/\\")

_SENSITIVE_KEYS = frozenset({
    "api_key", "secret", "token", "password", "passwd", "key",
    "auth", "authorization", "bearer", "credential", "pwd",
    "access_token", "refresh_token", "client_secret", "private_key",
})

_INLINE_SECRET = re.compile(
    r"(api_key|secret|token|password|authorization|bearer)\s*[=:]\s*\S+",
    re.IGNORECASE,
)

_SKIP_CONSOLE_KEYS = frozenset({
    "event", "level", "timestamp", "run_id", "positional_args",
    "logger", "logger_name", "_record", "_from_structlog",
})

_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.format_exc_info,
    structlog.stdlib.PositionalArgumentsFormatter(),
    lambda _l, _m, ed: _mask_event(ed),
]


def _mask_event(event_dict):
    """Mask sensitive keys and inline secrets in string values."""
    for key, value in list(event_dict.items()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[MASKED]"
        elif isinstance(value, str):
            event_dict[key] = _INLINE_SECRET.sub(r"\1=[MASKED]", value)
    return event_dict


def _readable_console(_logger, _method, event_dict):
    """One-line console format: time, level, message, optional context."""
    ts = event_dict.get("timestamp", "")
    if "T" in ts:
        ts = ts.split("T", 1)[1][:8]

    level = event_dict.get("level", "info").upper()
    if level == "WARNING":
        level = "WARN"
    level = level[:4].ljust(4)

    message = str(event_dict.get("event", ""))

    extras = []
    for key in sorted(event_dict):
        if key in _SKIP_CONSOLE_KEYS:
            continue
        value = event_dict[key]
        if value is None or value == "":
            continue
        text = str(value).replace("\n", " ")
        if len(text) > 80:
            text = text[:77] + "..."
        extras.append(f"{key}={text}")

    line = f"[{ts}] {level} {message}"
    if extras:
        line += "  |  " + "  ".join(extras)
    return line


def _quiet_noisy_loggers() -> None:
    for name in ("httpx", "httpcore", "urllib3", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _setup_logging() -> str:
    run_id = generate_uuid()
    bind_contextvars(run_id=run_id)

    log_root = os.path.join(os.getcwd(), LOG_DIR)
    os.makedirs(log_root, exist_ok=True)
    log_file = os.path.join(log_root, f"{datetime.now():%Y%m%d}.log")

    logging.root.handlers.clear()
    logging.root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    _quiet_noisy_loggers()

    structlog.configure(
        processors=_SHARED_PROCESSORS + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5, encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logging.root.addHandler(file_handler)

    if LOG_CONSOLE_DEV:
        console_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=_SHARED_PROCESSORS,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                _readable_console,
            ],
        )
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(console_formatter)
        logging.root.addHandler(console)
        structlog.get_logger(__name__).info("Log run started", run_id=run_id)

    return run_id


run_id = _setup_logging()
logger = structlog.get_logger(__name__)
