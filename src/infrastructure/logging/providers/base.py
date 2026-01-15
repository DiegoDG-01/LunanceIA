from abc import ABC, abstractmethod
import logging


class BaseLogHandler(logging.Handler, ABC):
    # Abstract base class for log handlers

    @abstractmethod
    def emit(self, record: logging.LogRecord) -> None:
        # Process the log record
        pass

    @abstractmethod
    def flush(self, record: logging.LogRecord) -> None:
        # Force the log record
        pass

    @abstractmethod
    def close(self, record: logging.LogRecord) -> None:
        # Close the handler and free resources
        pass
