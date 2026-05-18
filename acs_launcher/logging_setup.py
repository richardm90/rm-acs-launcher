import logging
import os
import re
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.expanduser("~/.local/state/rm-acs-launcher")
LOG_FILE = os.path.join(LOG_DIR, "launcher.log")

_LOGGER_NAME = "acs_launcher"
_handler = None

# Regexes that mask the *value* of common password-bearing flags, regardless
# of which launch_cmd template a user has configured. Belt-and-braces over
# the per-launch secret list so a custom template can't leak a password
# through the log even if we forget to register it.
_FLAG_PATTERNS = [
    re.compile(r"(?i)(/password=)[^\s]*"),
    re.compile(r"(?i)(--password[=\s])[^\s]*"),
    re.compile(r"(?i)(-p\s+)[^\s]+"),
    re.compile(r"(?i)(/pwd=)[^\s]*"),
]


class _SecretRedactingFilter(logging.Filter):
    """Replace per-launch secrets and password-flag values in every record."""

    def __init__(self):
        super().__init__()
        self._secrets = set()

    def add_secret(self, secret):
        if secret:
            self._secrets.add(secret)

    def clear_secrets(self):
        self._secrets.clear()

    def _scrub(self, text):
        if not isinstance(text, str):
            return text
        for s in self._secrets:
            if s:
                text = text.replace(s, "***")
        for pat in _FLAG_PATTERNS:
            text = pat.sub(r"\1***", text)
        return text

    def filter(self, record):
        # Resolve %-format args up-front so the scrubbed message is what
        # ends up on disk; otherwise a secret in record.args could slip past.
        if record.args:
            try:
                record.msg = record.getMessage()
                record.args = ()
            except Exception:
                pass
        record.msg = self._scrub(record.msg)
        return True


_filter = _SecretRedactingFilter()


def get_logger():
    return logging.getLogger(_LOGGER_NAME)


def add_secret(secret):
    _filter.add_secret(secret)


def clear_secrets():
    _filter.clear_secrets()


def configure(enabled):
    """Install or remove the rotating file handler based on `enabled`.

    Safe to call repeatedly — used both at startup and when the user
    toggles the Preferences checkbox.
    """
    global _handler
    logger = logging.getLogger(_LOGGER_NAME)
    logger.propagate = False

    if enabled:
        if _handler is not None:
            return
        os.makedirs(LOG_DIR, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handler.addFilter(_filter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        _handler = handler
    else:
        if _handler is not None:
            logger.removeHandler(_handler)
            _handler.close()
            _handler = None
        logger.setLevel(logging.CRITICAL + 1)
