# src/logging_exception/logging/logger.py

"""
Simple structured logger with run_id tracking.
"""

import os
import sys
import logging
import re
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any
import structlog
from structlog.contextvars import bind_contextvars

from src.utils.create_unique_uuid import generate_uuid

# =====================================
# CONFIG
# =====================================
LOG_CONSOLE_DEV = os.getenv("LOG_CONSOLE_DEV", "1") == "1"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

PROJECT_ROOT = os.path.abspath(os.getcwd()).replace("\\", "/")
LOGGER_PATH = os.path.abspath(__file__).replace("\\", "/")


# =====================================
# MASK SENSITIVE DATA
# =====================================
class SensitiveDataProcessor:
    def __init__(self):
        self.sensitive_keys = {
            'api_key', 'secret', 'token', 'password', 'key',
            'openai_api_key', 'groq_api_key', 'qdrant_api_key'
        }

    def __call__(self, logger, method_name, event_dict):
        for key in list(event_dict):
            if key in self.sensitive_keys:
                event_dict[key] = '[MASKED]'
        return event_dict


# =====================================
# CONTEXT PROCESSORS
# =====================================
def callsite(logger, method_name, event_dict):
    for frame in inspect.stack():
        path = frame.filename.replace("\\", "/")
        if PROJECT_ROOT in path and "/site-packages/" not in path and path != LOGGER_PATH:
            event_dict["file"] = os.path.basename(path)
            event_dict["function"] = frame.function
            event_dict["line"] = frame.lineno
            break
    return event_dict


def add_run_id(logger, method_name, event_dict):
    ctx = structlog.contextvars.get_contextvars()
    if "run_id" in ctx:
        event_dict["run_id"] = ctx["run_id"]
    return event_dict


# =====================================
# CONSOLE RENDERER - WITH RUN ID
# =====================================
def console_renderer(logger, method_name, event_dict):
    level = event_dict.get("level", "info").upper()
    event = event_dict.get("event", "")
    timestamp = event_dict.get("timestamp", "")[11:19]
    file_info = event_dict.get("file", "")
    line = event_dict.get("line", "")
    function = event_dict.get("function", "")
    
    location = f"{file_info}:{line}" if file_info and line else file_info
    if function:
        location += f" in {function}"
    
    log_line = f"[{timestamp}] {level:8} {location}\n    → {event}"
    
    # Add extra fields
    extra = {k: v for k, v in event_dict.items() 
             if k not in ["timestamp", "level", "event", "file", "function", "line", "run_id"]}
    if extra:
        import json
        log_line += f"\n    └─ {json.dumps(extra, default=str)[:200]}"
    
    return log_line


# =====================================
# MAIN LOGGER
# =====================================
class CustomLogger:
    _configured = False

    def __init__(self, log_dir="logs"):
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(os.path.join(self.logs_dir, "runs"), exist_ok=True)
        
        # Generate run_id
        self.run_id = generate_uuid()
        bind_contextvars(run_id=self.run_id)
        
        self.log_file = os.path.join(self.logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        self.run_log = os.path.join(self.logs_dir, "runs", f"run_{self.run_id}.log")
        
        if not CustomLogger._configured:
            self._configure()
            CustomLogger._configured = True

    def _configure(self):
        root = logging.getLogger()
        root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        root.handlers.clear()
        
        # File handlers
        for path in [self.log_file, self.run_log]:
            handler = RotatingFileHandler(path, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
            handler.setLevel(logging.INFO)
            root.addHandler(handler)
        
        # Console
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        root.addHandler(console)
        
        # Renderer
        renderer = console_renderer if LOG_CONSOLE_DEV else structlog.processors.JSONRenderer(sort_keys=False)
        
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.format_exc_info,
                callsite,
                add_run_id,
                SensitiveDataProcessor(),
                renderer,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def get_logger(self, name=None):
        return structlog.get_logger(name or __name__)

    def get_run_id(self):
        return self.run_id


# =====================================
# USE IT
# =====================================
logger = CustomLogger().get_logger()