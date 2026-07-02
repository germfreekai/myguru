"""Logger Class"""

import logging
import sys

import coloredlogs


class Logger:
    """Create logger object."""

    _LOGGER_NAME = "myguru"

    def __init__(self):
        """Initialize the logger with colored output on stderr."""
        self.logger = logging.getLogger(self._LOGGER_NAME)

        if self.logger.handlers:
            return

        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        level_styles = {
            "debug": {"color": "blue"},
            "info": {"color": "green"},
            "warning": {"color": "yellow"},
            "error": {"color": "red"},
            "critical": {"color": "red", "bold": True},
        }

        field_styles = {
            "asctime": {"color": "cyan"},
            "message": {"color": "white"},
        }

        coloredlogs.install(
            logger=self.logger,
            stream=sys.stderr,
            fmt="%(asctime)s - %(levelname)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M",
            level=logging.DEBUG,
            level_styles=level_styles,
            field_styles=field_styles,
        )

        self._suppress_external_logs()

    @staticmethod
    def set_quiet():
        """Suppress INFO-level output. Warnings and errors remain visible."""
        logging.getLogger(Logger._LOGGER_NAME).setLevel(logging.WARNING)

    def info(self, mssg):
        """
        Print info message.

        Args:
            - mssg (str): Message to log.
        """
        self.logger.info(mssg)

    def warning(self, mssg):
        """
        Print warning message.

        Args:
            - mssg (str): Message to log.
        """
        self.logger.warning(mssg)

    def error(self, mssg):
        """
        Print error message.

        Args:
            - mssg (str): Message to log.
        """
        self.logger.error(mssg)

    def _suppress_external_logs(self):
        """Suppress verbose logs from third-party libraries."""
        for name in ("httpcore", "httpx", "urllib3", "chromadb", "llama_index"):
            logging.getLogger(name).setLevel(logging.WARNING)
