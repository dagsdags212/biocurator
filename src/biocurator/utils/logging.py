"""
BioCurator Centralized Logging System
====================================

This module provides a centralized logging configuration for the entire BioCurator project.
It ensures consistent log formatting, levels, and output across all components.

Features:
- Consistent log formatting across all modules
- Configurable log levels and destinations
- File rotation with size and time limits
- Colored console output for development
- JSON structured logging option for production
- Performance logging for analysis modules
- Network request logging for database operations
- Separate loggers for different components

Usage:
    from biocurator.utils.logging import get_logger

    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.error("This is an error message")


© Jan Emmanuel Samson (2026-)
"""

import logging
import logging.handlers
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
import traceback

try:
    import colorlog

    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class BioCuratorLoggerConfig:
    """Configuration class for BioCurator logging system."""

    # Default configuration
    DEFAULT_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "level": "INFO",
        "console_output": True,
        "file_output": True,
        "file_path": "biocurator.log",
        "max_file_size": 10 * 1024 * 1024,  # 10 MB
        "backup_count": 5,
        "use_colors": True,
        "json_format": False,
        "include_performance": True,
        "include_network": True,
        "separate_error_file": True,
        "log_format": "[{asctime}] {name:<20} | {levelname:<8} | {message}",
        "date_format": "%Y-%m-%d %H:%M:%S",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize logger configuration.

        Parameters
        ----------
        config : dict, optional
            Configuration dictionary to override defaults
        """
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        # Ensure log directory exists
        log_path = Path(self.config["file_path"])
        log_path.parent.mkdir(parents=True, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add custom fields if present
        if hasattr(record, "custom_fields"):
            log_entry.update(record.custom_fields)

        return json.dumps(log_entry, default=str)


class BioCuratorLogFilter(logging.Filter):
    """Custom log filter for BioCurator-specific logging."""

    def __init__(self, component: Optional[str] = None):
        """Initialize filter.

        Parameters
        ----------
        component : str, optional
            Component name to filter by
        """
        super().__init__()
        self.component = component

    def filter(self, record):
        """Filter log records based on component."""
        # Add BioCurator context
        record.project = "BioCurator"

        # Add component if specified
        if self.component:
            record.component = self.component

        # Filter sensitive information
        message = record.getMessage()
        if any(
            sensitive in message.lower()
            for sensitive in ["password", "token", "key", "secret"]
        ):
            record.msg = "[SENSITIVE DATA REDACTED]"
            record.args = ()

        return True


class PerformanceLogger:
    """Logger for performance metrics."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._start_times = {}

    def start_timer(self, operation: str):
        """Start timing an operation."""
        import time

        self._start_times[operation] = time.time()
        self.logger.debug(f"Started operation: {operation}")

    def end_timer(self, operation: str, **kwargs):
        """End timing an operation and log the duration."""
        import time

        if operation in self._start_times:
            duration = time.time() - self._start_times[operation]
            extra_fields = {"operation": operation, "duration_seconds": duration}
            extra_fields.update(kwargs)

            # Create custom record with performance data
            record = self.logger.makeRecord(
                self.logger.name,
                logging.INFO,
                "",
                0,
                f"Operation completed: {operation} ({duration:.3f}s)",
                (),
                None,
            )
            record.custom_fields = extra_fields
            self.logger.handle(record)

            del self._start_times[operation]


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Set up centralized logging for BioCurator.

    Parameters
    ----------
    config : dict, optional
        Logging configuration dictionary
    """
    logger_config = BioCuratorLoggerConfig(config)
    cfg = logger_config.config

    # Clear existing handlers
    root_logger = logging.getLogger("biocurator")
    root_logger.handlers.clear()

    # Set root level
    root_logger.setLevel(getattr(logging, cfg["level"].upper()))

    # Create formatters
    if cfg["json_format"]:
        formatter = JSONFormatter()
    else:
        if cfg["use_colors"] and COLORLOG_AVAILABLE and cfg["console_output"]:
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s[%(asctime)s] %(name)-20s | %(levelname)-8s | %(message)s",
                datefmt=cfg["date_format"],
                reset=True,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            )
        else:
            formatter = logging.Formatter(
                cfg["log_format"].format(
                    asctime="{asctime}",
                    name="{name}",
                    levelname="{levelname}",
                    message="{message}",
                ),
                datefmt=cfg["date_format"],
                style="{",
            )

    # Console handler
    if cfg["console_output"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(BioCuratorLogFilter())

        # Only show INFO and above on console unless debug mode
        console_level = logging.DEBUG if cfg["level"] == "DEBUG" else logging.INFO
        console_handler.setLevel(console_level)

        root_logger.addHandler(console_handler)

    # File handler with rotation
    if cfg["file_output"]:
        file_formatter = logging.Formatter(
            cfg["log_format"].format(
                asctime="{asctime}",
                name="{name}",
                levelname="{levelname}",
                message="{message}",
            ),
            datefmt=cfg["date_format"],
            style="{",
        )

        file_handler = logging.handlers.RotatingFileHandler(
            cfg["file_path"],
            maxBytes=cfg["max_file_size"],
            backupCount=cfg["backup_count"],
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(BioCuratorLogFilter())
        root_logger.addHandler(file_handler)

        # Separate error file
        if cfg["separate_error_file"]:
            error_file = Path(cfg["file_path"]).with_suffix(".error.log")
            error_handler = logging.handlers.RotatingFileHandler(
                error_file,
                maxBytes=cfg["max_file_size"],
                backupCount=cfg["backup_count"],
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            error_handler.addFilter(BioCuratorLogFilter())
            root_logger.addHandler(error_handler)

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False

    # Set up specific component loggers
    setup_component_loggers(cfg)


def setup_component_loggers(config: Dict[str, Any]) -> None:
    """Set up loggers for specific BioCurator components."""

    # Database operation logger
    db_logger = logging.getLogger("biocurator.database")
    if config["include_network"]:
        db_logger.setLevel(logging.DEBUG)
        db_logger.addFilter(BioCuratorLogFilter("database"))

    # Analysis logger
    analysis_logger = logging.getLogger("biocurator.analysis")
    if config["include_performance"]:
        analysis_logger.setLevel(logging.DEBUG)
        analysis_logger.addFilter(BioCuratorLogFilter("analysis"))

    # CLI logger
    cli_logger = logging.getLogger("biocurator.cli")
    cli_logger.setLevel(logging.INFO)
    cli_logger.addFilter(BioCuratorLogFilter("cli"))

    # Core logger
    core_logger = logging.getLogger("biocurator.core")
    core_logger.setLevel(logging.INFO)
    core_logger.addFilter(BioCuratorLogFilter("core"))

    # Utils logger
    utils_logger = logging.getLogger("biocurator.utils")
    utils_logger.setLevel(logging.WARNING)  # Less verbose for utilities
    utils_logger.addFilter(BioCuratorLogFilter("utils"))


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Parameters
    ----------
    name : str
        Logger name, typically __name__ from the calling module

    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    # Ensure name starts with biocurator
    if not name.startswith("biocurator"):
        if name == "__main__":
            name = "biocurator.main"
        else:
            # Extract module name from full path
            parts = name.split(".")
            if len(parts) > 1:
                name = f"biocurator.{parts[-1]}"
            else:
                name = f"biocurator.{name}"

    return logging.getLogger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    """Get a performance logger for timing operations.

    Parameters
    ----------
    name : str
        Logger name

    Returns
    -------
    PerformanceLogger
        Performance logger instance
    """
    logger = get_logger(name)
    return PerformanceLogger(logger)


def log_function_call(func):
    """Decorator to log function calls with parameters and execution time."""

    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        perf_logger = get_performance_logger(func.__module__)

        # Log function entry
        args_str = ", ".join(
            [str(arg)[:100] for arg in args[:3]]
        )  # First 3 args, truncated
        kwargs_str = ", ".join(
            [f"{k}={str(v)[:50]}" for k, v in list(kwargs.items())[:3]]
        )

        logger.debug(
            f"Calling {func.__name__}({args_str}{', ' + kwargs_str if kwargs_str else ''})"
        )

        # Time the execution
        operation_name = f"{func.__module__}.{func.__name__}"
        perf_logger.start_timer(operation_name)

        try:
            result = func(*args, **kwargs)
            perf_logger.end_timer(operation_name, status="success")
            logger.debug(f"Function {func.__name__} completed successfully")
            return result
        except Exception as e:
            perf_logger.end_timer(operation_name, status="error", error=str(e))
            logger.error(f"Function {func.__name__} failed: {e}")
            raise

    return wrapper


def log_network_request(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    response_time: Optional[float] = None,
    error: Optional[str] = None,
):
    """Log network requests for database operations.

    Parameters
    ----------
    method : str
        HTTP method (GET, POST, etc.)
    url : str
        Request URL
    status_code : int, optional
        HTTP status code
    response_time : float, optional
        Response time in seconds
    error : str, optional
        Error message if request failed
    """
    logger = get_logger("biocurator.database.network")

    # Create custom record
    if error:
        logger.error(f"Network request failed: {method} {url} - {error}")
    else:
        log_msg = f"Network request: {method} {url}"
        if status_code:
            log_msg += f" [{status_code}]"
        if response_time:
            log_msg += f" ({response_time:.3f}s)"

        logger.info(log_msg)


def configure_logging_from_config(config_dict: Dict[str, Any]):
    """Configure logging from a configuration dictionary.

    Parameters
    ----------
    config_dict : dict
        Configuration dictionary that may contain logging settings
    """
    logging_config = config_dict.get("logging", {})

    # Map common configuration keys
    biocurator_config = {}

    if "level" in logging_config:
        biocurator_config["level"] = logging_config["level"].upper()

    if "log_file" in logging_config:
        biocurator_config["file_path"] = logging_config["log_file"]

    if "console" in logging_config:
        biocurator_config["console_output"] = logging_config["console"]

    if "file_output" in logging_config:
        biocurator_config["file_output"] = logging_config["file_output"]

    if "max_size" in logging_config:
        biocurator_config["max_file_size"] = logging_config["max_size"]

    if "format" in logging_config:
        biocurator_config["log_format"] = logging_config["format"]

    setup_logging(biocurator_config)


def get_log_level_from_env() -> str:
    """Get log level from environment variable."""
    return os.environ.get("BIOCURATOR_LOG_LEVEL", "INFO").upper()


def initialize_logging(
    config: Optional[Dict[str, Any]] = None, env_override: bool = True
) -> None:
    """Initialize the BioCurator logging system.

    This is the main entry point for setting up logging. Should be called
    once at the start of the application.

    Parameters
    ----------
    config : dict, optional
        Logging configuration dictionary
    env_override : bool, default True
        Whether to allow environment variable overrides
    """
    # Start with provided config or defaults
    logging_config = config or {}

    # Override with environment variables if requested
    if env_override:
        env_level = get_log_level_from_env()
        if env_level:
            logging_config["level"] = env_level

    # Set up logging
    setup_logging(logging_config)

    # Log initialization
    logger = get_logger("biocurator.logging")
    logger.info("BioCurator logging system initialized")
    logger.debug(f"Logging configuration: {logging_config}")


# Pre-configured logging setups for different environments
def setup_development_logging():
    """Set up logging optimized for development."""
    config = {
        "level": "DEBUG",
        "console_output": True,
        "file_output": True,
        "use_colors": True,
        "file_path": "biocurator_dev.log",
        "include_performance": True,
        "include_network": True,
    }
    setup_logging(config)


def setup_production_logging():
    """Set up logging optimized for production."""
    config = {
        "level": "INFO",
        "console_output": False,
        "file_output": True,
        "use_colors": False,
        "json_format": True,
        "file_path": "/var/log/biocurator/biocurator.log",
        "max_file_size": 50 * 1024 * 1024,  # 50 MB
        "backup_count": 10,
        "separate_error_file": True,
        "include_performance": True,
        "include_network": True,
    }
    setup_logging(config)


def setup_testing_logging():
    """Set up logging for testing environment."""
    config = {
        "level": "WARNING",
        "console_output": False,
        "file_output": False,  # No file output during tests
        "use_colors": False,
    }
    setup_logging(config)


# Context manager for temporary log level changes
class LogLevelContext:
    """Context manager for temporarily changing log level."""

    def __init__(self, logger_name: str, level: Union[str, int]):
        self.logger = get_logger(logger_name)
        self.level = (
            level if isinstance(level, int) else getattr(logging, level.upper())
        )
        self.original_level = None

    def __enter__(self):
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.original_level)


# Convenience functions for common logging operations
def log_config(config_dict: Dict[str, Any], logger_name: str = "biocurator.config"):
    """Log configuration dictionary in a readable format."""
    logger = get_logger(logger_name)
    logger.info("Configuration loaded:")
    for key, value in config_dict.items():
        if isinstance(value, dict):
            logger.info(f"  {key}:")
            for sub_key, sub_value in value.items():
                logger.info(f"    {sub_key}: {sub_value}")
        else:
            logger.info(f"  {key}: {value}")


def log_system_info(logger_name: str = "biocurator.system"):
    """Log system information for debugging."""
    import platform
    import psutil

    logger = get_logger(logger_name)
    logger.info(f"System: {platform.system()} {platform.release()}")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"CPU cores: {psutil.cpu_count()}")
    logger.info(f"Memory: {psutil.virtual_memory().total // (1024**3)} GB")


# Initialize with defaults when module is imported
_logging_initialized = False


def ensure_logging_initialized():
    """Ensure logging is initialized with defaults."""
    global _logging_initialized
    if not _logging_initialized:
        initialize_logging()
        _logging_initialized = True


def enable_verbose_logging() -> None:
    """Attach an INFO-level stdout handler to the biocurator root logger.

    Format: ``YYYY-MM-DD HH:MM:SS  LEVEL     message``

    Safe to call multiple times — duplicate handlers are not added.
    """
    root = logging.getLogger("biocurator")

    if any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
        for h in root.handlers
    ):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(BioCuratorLogFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
