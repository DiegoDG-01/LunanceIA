import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):

    def __init__(
            self,
            app_name: str = "app",
            environment: str = "development",
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.app_name = app_name
        self.environment = environment


    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "app": self.app_name,
            "env": self.environment
        }

        extra_fields = [
            "request_id", "user_id", "path", "method",
            "status_code", "duration_ms", "client_ip"
        ]

        for field in extra_fields:
            if hasattr(record, field):
                value = getattr(record, field)
                if value is not None:
                    log_data[field] = value

        if record.exc_info:
            log_data['exception'] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "value": record.exc_info[1] if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        return json.dumps(log_data, default=str, ensure_ascii=False)