import logging
from typing import Any
import json
import time
import threading
import queue
import httpx


class LokiHandler(logging.Handler):
    """
    Handler to send logs to Grafana Loki.

    Features:
    - Thread-safe
    - Batched HTTP requests
    - Automatic retries
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        app_name: str,
        environment: str,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        level: int = logging.INFO,
    ):
        super().__init__(level)
        self.url = f"{url.strip('/')}/loki/api/v1/push"
        self.auth = (username, password) if username and password else None
        self.app_name = app_name
        self.environment = environment
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # Buffer batch
        self._queue: queue.Queue = queue.Queue()
        self._shutdown = threading.Event()

        # Thread to send logs
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()

    def _format_for_loki(self, record: logging.LogRecord) -> dict:
        timestamp_ns = str(int(record.created * 1e9))

        message = {
            "message": record.getMessage(),
            "logger": record.name,
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Agregar extras(request_id, user_id, etc.)
        if hasattr(record, "request_id"):
            message["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            message["user_id"] = record.user_id
        if hasattr(record, "path"):
            message["path"] = record.path
        if hasattr(record, "method"):
            message["method"] = record.method
        if hasattr(record, "status_code"):
            message["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            message["duration_ms"] = record.duration_ms

        if record.exc_info:
            message["exception"] = (
                self.formatter.formatException(record.exc_info)
                if self.formatter
                else str(record.exc_info)
            )

        return {
            "labels": {
                "app": self.app_name,
                "env": self.environment,
                "level": record.levelname,
                "logger": record.name,
                "module": record.module,
                "function": record.funcName.lower(),
            },
            "timestamp": timestamp_ns,
            "message": json.dumps(message),
        }

    def _sender_loop(self) -> None:
        buffer = []
        last_flush = time.time()

        while not self._shutdown.is_set():
            try:
                try:
                    entry = self._queue.get(timeout=1.0)
                    buffer.append(entry)
                except queue.Empty:
                    pass

                should_flush = len(buffer) >= self.batch_size or (
                    buffer and time.time() - last_flush >= self.flush_interval
                )

                if should_flush and buffer:
                    self._send_batch(buffer)
                    buffer = []
                    last_flush = time.time()
            except Exception as e:
                import sys

                print(f"LokiHandler error: {e}", file=sys.stderr)

        if buffer:
            self._send_batch(buffer)

    def _send_batch(self, entries: list) -> None:
        streams = {}
        for entry in entries:
            label_key = json.dumps(entry["labels"], sort_keys=True)
            if label_key not in streams:
                streams[label_key] = {"stream": entry["labels"], "values": []}
            streams[label_key]["values"].append([entry["timestamp"], entry["message"]])

        payload = {"streams": list(streams.values())}

        try:
            with httpx.Client(timeout=1.0) as client:
                kwargs: dict[str, Any] = {
                    "json": payload,
                    "headers": {"Content-Type": "application/json"},
                }
                if self.auth:
                    kwargs["auth"] = self.auth
                response = client.post(self.url, **kwargs)
                response.raise_for_status()
        except Exception as e:
            import sys

            print(f"Fail to send batch to Loki: {e}", file=sys.stderr)

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self._format_for_loki(record)
            self._queue.put(log_entry)
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        self._queue.join()

    def close(self) -> None:
        self._shutdown.set()
        self._sender_thread.join(timeout=1.0)
        super().close()
