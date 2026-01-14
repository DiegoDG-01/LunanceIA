import logging
import logging.config
from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings


class LogProvider(Enum):
    CONSOLE = "console"
    GRAFANA = "grafana"
    FILE = "file"
    HYBRID = "hybrid"


class LogFormat(Enum):
    JSON = "json"
    TEXT = "text"


class LoggingSettings(BaseSettings):
    # General
    LOG_PROVIDER: LogProvider = LogProvider.CONSOLE
    LOG_FORMAT: LogFormat = LogFormat.JSON
    LOG_LEVEL: str = "INFO"

    # Grafana Loki
    LOKI_URL: Optional[str] = None
    LOKI_USERNAME: Optional[str] = None
    LOKI_PASSWORD: Optional[str] = None
    LOKI_APP_NAME: Optional[str] = None
    LOKI_ENV: Optional[str] = None

    # File logging
    LOG_FILE_PATH: Optional[str] = "logs/app.log"
    LOG_FILE_MAX_BYTES: int = 1024 * 1024 * 10 # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


def get_logging_config(settings: LoggingSettings) -> dict:

    formatters = {
        "json": {
            "()": "infrastructure.logging.formatters.JsonFormatter",
            "app_name": settings.LOKI_APP_NAME,
            "environment": settings.LOKI_ENV
        },
        "text": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    }

    handlers = {}
    root_handlers = []

    handlers['console'] = {
        "class": "logging.StreamHandler",
        "level": settings.LOG_LEVEL,
        "formatter": settings.LOG_FORMAT.value,
        "stream": "ext://sys.stdout"
    }

    if settings.LOG_PROVIDER == LogProvider.CONSOLE:
        root_handlers.append("console")

    elif settings.LOG_PROVIDER == LogProvider.GRAFANA:
        handlers['loki'] = {
            "()": "infrastructure.logging.providers.grafana_loki.LokiHandler",
            "url": settings.LOKI_URL,
            "username": settings.LOKI_USERNAME,
            "password": settings.LOKI_PASSWORD,
            "app_name": settings.LOKI_APP_NAME,
            "environment": settings.LOKI_ENV,
            "level": settings.LOG_LEVEL
        }
        root_handlers = ["loki"]

    elif settings.LOG_PROVIDER == LogProvider.FILE:
        handlers['file'] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "json",
            "filename": settings.LOG_FILE_PATH,
            "maxBytes": settings.LOG_FILE_MAX_BYTES,
            "backupCount": settings.LOG_FILE_BACKUP_COUNT
        }
        root_handlers = ["console","file"]

    elif settings.LOG_PROVIDER == LogProvider.HYBRID:
        handlers['loki'] = {
            "()": "infrastructure.logging.providers.grafana_loki.LokiHandler",
            "url": settings.LOKI_URL,
            "username": settings.LOKI_USERNAME,
            "password": settings.LOKI_PASSWORD,
            "app_name": settings.LOKI_APP_NAME,
            "environment": settings.LOKI_ENV,
            "level": settings.LOG_LEVEL
        }
        root_handlers = ["console", "loki"]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "filters": {
            "request_context": {
                "()": "infrastructure.logging.filters.RequestContextFilter"
            }
        },
        "loggers": {
            "": {
                "handlers": root_handlers,
                "level": settings.LOG_LEVEL,
                "filters": ["request_context"]
            },
            "src": {
                "handlers": root_handlers,
                "level": settings.LOG_LEVEL,
                "filters": ["request_context"],
                "propagate": False
            },
            "uvicorn": {
                "level": "WARNING",
                "handlers": ['console'],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ['console'],
                "propagate": False
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ['console'],
                "propagate": False
            }
        }
    }


def setup_logging():
    settings = LoggingSettings()
    config = get_logging_config(settings)
    logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized",
        extra={
            "provider": settings.LOG_PROVIDER.value,
            "format": settings.LOG_FORMAT.value,
            "level": settings.LOG_LEVEL
        }
    )

















































