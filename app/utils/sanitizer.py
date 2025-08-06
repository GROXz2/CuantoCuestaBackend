import re
from html import escape

SAFE_PATTERN = re.compile(r'[^\w\s-]', re.UNICODE)

def sanitize_text(value: str) -> str:
    """Remove potentially dangerous characters and escape HTML."""
    if value is None:
        return ""
    sanitized = SAFE_PATTERN.sub('', value)
    return escape(sanitized.strip())
