"""Secret field redaction for OKF concept content.

Detects and redacts sensitive values in DocType field names, Link options,
and any string value that matches a known secret pattern.

This module has NO Frappe dependency — it's pure Python.
"""

from __future__ import annotations

import re
from typing import Any


# Field name keywords that indicate a secret value.
# Matched case-insensitively against whole tokens (word boundary on `_`, `-`, space).
SECRET_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "api_secret",
    "apikey",
    "apisecret",
    "oauth",
    "access_token",
    "refresh_token",
    "private_key",
    "client_secret",
    "session_key",
    "encryption_key",
    "ssh_key",
    "webhook_secret",
    "signing_key",
)

# Compiled regex: matches any keyword at word boundary, case-insensitive.
# Word boundary = start/end of string OR non-alphanumeric.
_SECRET_NAME_RE = re.compile(
    r"(?:^|[^a-z0-9])(" + "|".join(re.escape(k) for k in SECRET_KEYWORDS) + r")(?:$|[^a-z0-9])",
    re.IGNORECASE,
)

# Patterns that look like leaked secrets in string values.
SECRET_VALUE_PATTERNS = [
    # AWS access key
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # GitHub PAT (classic)
    re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
    # OpenAI API key
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    # Anthropic API key
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    # Generic Bearer tokens
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b"),
    # PEM private key block
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    # JWT (three base64url segments)
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]

REDACTED_PLACEHOLDER = "***REDACTED***"


def is_secret_field(name: str) -> bool:
    """Return True if a field/option name looks like it stores a secret.

    >>> is_secret_field("password")
    True
    >>> is_secret_field("api_key")
    True
    >>> is_secret_field("email")
    False
    >>> is_secret_field("my_password_field")
    True
    >>> is_secret_field("Password")
    True
    """
    if not isinstance(name, str):
        return False
    return bool(_SECRET_NAME_RE.search(name))


def redact_value(value: Any) -> Any:
    """Redact a value if it matches a known secret pattern.

    Returns the original value if it doesn't look like a secret, or the
    REDACTED_PLACEHOLDER if it does. For dicts/lists, recursively redacts
    string values (does not redact keys).
    """
    if isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                return REDACTED_PLACEHOLDER
        return value
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        redacted = [redact_value(v) for v in value]
        return type(value)(redacted) if isinstance(value, tuple) else redacted
    return value


def redact_field_definition(fieldname: str, fieldtype: str, options: Any = None) -> dict:
    """Return a safe representation of a Frappe field definition.

    Always redacts the value of any field whose name looks like a secret.
    For Password-type fields, redacts unconditionally.
    """
    is_secret = is_secret_field(fieldname) or (fieldtype or "").lower() == "password"
    result: dict[str, Any] = {
        "fieldname": fieldname,
        "fieldtype": fieldtype,
        "options": options,
    }
    if is_secret:
        result["options"] = REDACTED_PLACEHOLDER
        result["_redacted"] = True
    return result
