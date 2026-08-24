# src\logging_exception\logging\logger.py

"""
Simple structured logger with run_id tracking.
"""

import os
import sys
import logging
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime
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
# PROCESSORS
# =====================================
def add_callsite(logger, method_name, event_dict):
    """Add file, function, line where log was called."""
    for frame in inspect.stack():
        path = frame.filename.replace("\\", "/")
        if PROJECT_ROOT in path and "/site-packages/" not in path and path != LOGGER_PATH:
            event_dict["file"] = os.path.basename(path)
            event_dict["function"] = frame.function
            event_dict["line"] = frame.lineno
            break
    return event_dict


def add_run_id(logger, method_name, event_dict):
    """Add run_id from context."""
    ctx = structlog.contextvars.get_contextvars()
    if "run_id" in ctx:
        event_dict["run_id"] = ctx["run_id"]
    return event_dict


def mask_sensitive(logger, method_name, event_dict):
    """Mask sensitive data."""
    sensitive_keys = {'api_key', 'secret', 'token', 'password', 'key'}
    for key in list(event_dict):
        if key in sensitive_keys:
            event_dict[key] = '[MASKED]'
    return event_dict


# =====================================
# CONSOLE RENDERER (dev only)
# =====================================
def console_renderer(logger, method_name, event_dict):
    """Pretty console output."""
    level = event_dict.get("level", "info").upper()
    event = event_dict.get("event", "")
    timestamp = event_dict.get("timestamp", "")[11:19]
    file_info = event_dict.get("file", "")
    line = event_dict.get("line", "")
    function = event_dict.get("function", "")
    
    location = f"{file_info}:{line}" if file_info and line else ""
    if function:
        location += f" in {function}"
    
    log_line = f"[{timestamp}] {level:8} {location}\n    → {event}"
    
    # Show extra fields
    extra = {k: v for k, v in event_dict.items() 
             if k not in ["timestamp", "level", "event", "file", "function", "line", "run_id"]}
    if extra:
        import json
        log_line += f"\n    └─ {json.dumps(extra, default=str)[:200]}"
    
    return log_line


# =====================================
# LOGGER SETUP
# =====================================
class Logger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # Generate run_id
        self.run_id = generate_uuid()
        bind_contextvars(run_id=self.run_id)
        
        # Setup logging
        self._setup_logging()
        self._initialized = True
    
    def _setup_logging(self):
        # Clear any existing handlers
        logging.root.handlers.clear()
        
        # Create log directories
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(os.path.join(log_dir, "runs"), exist_ok=True)
        
        # Log file paths
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f"{date_str}.log")
        run_log = os.path.join(log_dir, "runs", f"run_{self.run_id}.log")
        
        # Add file handlers
        for path in [log_file, run_log]:
            handler = RotatingFileHandler(path, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
            handler.setLevel(logging.DEBUG)
            logging.root.addHandler(handler)
        
        # Add console handler (dev only)
        if LOG_CONSOLE_DEV:
            console = logging.StreamHandler(sys.stdout)
            console.setLevel(logging.INFO)
            logging.root.addHandler(console)
        
        logging.root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        
        # Configure structlog
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            add_callsite,
            add_run_id,
            mask_sensitive,
        ]
        
        # Use different renderer for dev/prod
        if LOG_CONSOLE_DEV:
            processors.append(console_renderer)
        else:
            processors.append(structlog.processors.JSONRenderer())
        
        structlog.configure(
            processors=processors,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def get_logger(self, name=None):
        return structlog.get_logger(name or __name__)
    
    def get_run_id(self):
        return self.run_id


# =====================================
# SINGLETON INSTANCE
# =====================================
_logger = Logger()
logger = _logger.get_logger()
run_id = _logger.get_run_id()