import logging
from abc import ABC, abstractmethod


class BaseLogHandler(logging.Handler, ABC):
    # Abstract base class for log handlers

    @abstractmethod
    def emit(self, record: logging.LogRecord) -> None:
        # Process the log record
        pass

    @abstractmethod
    def flush(self) -> None:
        # Force flush buffered records
        pass

    @abstractmethod
    def close(self) -> None:
        # Close the handler and free resources
        pass
