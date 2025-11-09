"""Logger Class"""

import logging
import sys

import coloredlogs


class Logger:
    """Create logger object."""

    def __init__(self):
        """Initialize the logger with colored output."""
        self.logger = logging.getLogger(__name__)
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
            stream=sys.stdout,
            fmt="%(asctime)s - %(levelname)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M",
            level=logging.DEBUG,
            level_styles=level_styles,
            field_styles=field_styles,
        )
        
        self.supress_external_logs()

    def _set_level(self, level):
        """
        Set logging level.

        Args:
            - level (int): Logging level to set.
        """
        self.logger.setLevel(level)

    def info(self, mssg):
        """
        Print info message.

        Args:
            - mssg (str): Message to log.
        """
        self._set_level(logging.INFO)
        self.logger.info(mssg)

    def warning(self, mssg):
        """
        Print warning message.

        Args:
            - mssg (str): Message to log.
        """
        self._set_level(logging.WARNING)
        self.logger.warning(mssg)

    def error(self, mssg):
        """
        Print error message.

        Args:
            - mssg (str): Message to log.
        """
        self._set_level(logging.ERROR)
        self.logger.error(mssg)

    def supress_external_logs(self):
        """Supress verbosity logs."""
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('chromadb').setLevel(logging.WARNING)
        logging.getLogger('llama_index').setLevel(logging.WARNING)
