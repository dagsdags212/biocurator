import functools
import logging
import sys
from typing import Any


class _SensitiveFilter(logging.Filter):
    _SENSITIVE = {"password", "token", "key", "secret"}

    def filter(self, record: logging.LogRecord) -> bool:
        if any(s in record.getMessage().lower() for s in self._SENSITIVE):
            record.msg = "[SENSITIVE DATA REDACTED]"
            record.args = ()
        return True


class PerformanceLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._timers: dict[str, float] = {}

    def start_timer(self, operation: str) -> None:
        import time
        self._timers[operation] = time.time()
        self._logger.debug(f"Started: {operation}")

    def end_timer(self, operation: str, **kwargs: Any) -> None:
        import time
        if operation not in self._timers:
            return
        duration = time.time() - self._timers.pop(operation)
        self._logger.debug(f"Finished: {operation} ({duration:.3f}s) {kwargs}")


def get_logger(name: str) -> logging.Logger:
    if not name.startswith("biocurator"):
        name = "biocurator.main" if name == "__main__" else f"biocurator.{name.split('.')[-1]}"
    return logging.getLogger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    return PerformanceLogger(get_logger(name))


def log_function_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        perf = get_performance_logger(func.__module__)
        op = f"{func.__module__}.{func.__name__}"
        logger.debug(f"Calling {func.__name__}")
        perf.start_timer(op)
        try:
            result = func(*args, **kwargs)
            perf.end_timer(op, status="success")
            return result
        except Exception as exc:
            perf.end_timer(op, status="error", error=str(exc))
            logger.error(f"{func.__name__} failed: {exc}")
            raise
    return wrapper


def log_config(config: dict[str, Any], logger_name: str = "biocurator.config") -> None:
    logger = get_logger(logger_name)
    for key, value in config.items():
        if isinstance(value, dict):
            logger.info(f"  {key}:")
            for sub_key, sub_value in value.items():
                logger.info(f"    {sub_key}: {sub_value}")
        else:
            logger.info(f"  {key}: {value}")


def enable_verbose_logging(console=None) -> None:
    """Attach an INFO-level handler to the biocurator root logger.

    Pass a rich.console.Console to coordinate with Rich live displays.
    Safe to call multiple times — a second handler is not added.
    """
    root = logging.getLogger("biocurator")
    if any(getattr(h, "_biocurator_verbose", False) for h in root.handlers):
        return

    if console is not None:
        from rich.logging import RichHandler
        handler = RichHandler(
            console=console,
            show_path=False,
            markup=False,
            highlighter=None,
            log_time_format="%Y-%m-%d %H:%M:%S",
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s  %(levelname)-8s  %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    handler.setLevel(logging.INFO)
    handler.addFilter(_SensitiveFilter())
    handler._biocurator_verbose = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(logging.INFO)
