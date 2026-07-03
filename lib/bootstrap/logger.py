__version__ = "2.0.0"

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from lib.bootstrap.appenv import AppEnv
from typing import Optional


class Logger:
    """
    Class for handling application logging using Python stdlib logging module.
    Writes to both a rotating log file and the console (configurable).

    Log file is automatically created in <app_home>/log/ folder.
    File rotation is triggered when file size exceeds max_bytes (default: 5MB),
    keeping up to backup_count previous files.
    """
    alias = "log"

    def __init__(
        self,
        app_home: str,
        app_name: str,
        verbose: bool = True,
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 3,
    ):
        """
        Constructor.

        Args:
            app_home (str): Parent location for this app.
            app_name (str): Application name.
            verbose (bool): If True, log messages are also printed to console. Defaults to True.
            max_bytes (int): Max log file size in bytes before rotation. Defaults to 5MB.
            backup_count (int): Number of rotated backup files to keep. Defaults to 3.
        """
        self._application_home = app_home
        self._application_name = app_name
        self._verbose = verbose

        self._log_folder = Path(app_home) / "log"
        self._log_file = self._log_folder / f"{app_name}_{AppEnv.get_current_date()}.log"

        self._logger = self._setup_logger(max_bytes, backup_count)

    #######################################
    ##### PUBLIC FONCTIONS & METHODES #####
    #######################################

    @property
    def log_folder(self) -> str:
        """Return log folder path."""
        return str(self._log_folder)

    @property
    def log_file(self) -> str:
        """Return current log file path."""
        return str(self._log_file)

    def log(self, message: str) -> None:
        """
        Output a message in log file without prefix.

        Args:
            message (str): Message to output.

        Example:
            epy.log.log("Simple message, no prefix")
        """
        self._no_prefix_logger.info(message)

    def info(self, message: str) -> None:
        """
        Output a message with 'INFO' prefix.

        Args:
            message (str): Message to output.

        Example:
            epy.log.info("Application started")
        """
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """
        Output a message with 'WARNING' prefix.

        Args:
            message (str): Message to output.

        Example:
            epy.log.warning("Config file not found, using defaults")
        """
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """
        Output a message with 'ERROR' prefix.

        Args:
            message (str): Message to output.

        Example:
            epy.log.error("Failed to connect to database")
        """
        self._logger.error(message)

    def debug(self, message: str) -> None:
        """
        Output a debug message (only visible when log level is DEBUG).

        Args:
            message (str): Message to output.

        Example:
            epy.log.debug("Variable x = 42")
        """
        self._logger.debug(message)

    def set_level(self, level: str) -> None:
        """
        Change the log level at runtime.

        Args:
            level (str): Log level. Accepted values: 'DEBUG', 'INFO', 'WARNING', 'ERROR'.

        Example:
            epy.log.set_level("DEBUG")
        """
        numeric = getattr(logging, level.upper(), None)
        if numeric is None:
            raise ValueError(f"Invalid log level: '{level}'. Use DEBUG, INFO, WARNING or ERROR.")
        self._logger.setLevel(numeric)

    ######################################
    ##### PRIVATE METHOD & FUNCTIONS #####
    ######################################

    def _setup_logger(self, max_bytes: int, backup_count: int) -> logging.Logger:
        """
        Build and configure the internal stdlib logger with a file handler
        (rotating) and an optional console handler.

        Args:
            max_bytes (int): Max file size before rotation.
            backup_count (int): Number of backup files to keep.

        Returns:
            logging.Logger: Configured logger instance.
        """
        self._log_folder.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger(self._application_name)
        logger.setLevel(logging.DEBUG)

        # Avoid adding duplicate handlers if Logger is re-instantiated
        if logger.handlers:
            logger.handlers.clear()

        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Rotating file handler
        file_handler = RotatingFileHandler(
            filename=self._log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler (optional)
        if self._verbose:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Dedicated sub-logger for log() — no level prefix
        no_prefix_formatter = logging.Formatter(
            fmt="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        self._no_prefix_logger = logging.getLogger(f"{self._application_name}.raw")
        self._no_prefix_logger.setLevel(logging.DEBUG)
        self._no_prefix_logger.propagate = False

        if self._no_prefix_logger.handlers:
            self._no_prefix_logger.handlers.clear()

        no_prefix_file_handler = RotatingFileHandler(
            filename=self._log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        no_prefix_file_handler.setLevel(logging.DEBUG)
        no_prefix_file_handler.setFormatter(no_prefix_formatter)
        self._no_prefix_logger.addHandler(no_prefix_file_handler)

        if self._verbose:
            no_prefix_console_handler = logging.StreamHandler()
            no_prefix_console_handler.setLevel(logging.DEBUG)
            no_prefix_console_handler.setFormatter(no_prefix_formatter)
            self._no_prefix_logger.addHandler(no_prefix_console_handler)

        return logger