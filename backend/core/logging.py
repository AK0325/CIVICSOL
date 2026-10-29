"""
CIVICSOL - Structured Logging with Sensitive Data Masking
Ensures passwords, tokens, OTPs, and authorization credentials are never leaked in log output.
"""

import logging
import re
import sys

SENSITIVE_PATTERNS = [
    re.compile(r'(?i)(password|passwd|pwd)[\'"]?\s*[:=]\s*[\'"]?([^\s\'",]+)'),
    re.compile(r'(?i)(token|bearer|jwt|access_token|secret)[\'"]?\s*[:=]\s*[\'"]?([^\s\'",]+)'),
    re.compile(r'(?i)(otp|code|pin)[\'"]?\s*[:=]\s*[\'"]?([0-9]{4,8})'),
    re.compile(r'(?i)authorization:\s*bearer\s+([^\s]+)'),
]


class SanitizedLogFilter(logging.Filter):
    """Filter that replaces sensitive token/password substrings with [REDACTED]."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern in SENSITIVE_PATTERNS:
                msg = pattern.sub(r'\1: [REDACTED]', msg)
            record.msg = msg
        return True


def get_logger(name: str = "civicsol") -> logging.Logger:
    """Return a configured logger with sensitive data sanitization."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SanitizedLogFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger("civicsol")
