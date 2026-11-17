"""Secrets redaction and telemetry truncation utility.

Per AGENTS.md Hard Rule 6:
Never print, log or commit secrets. Credentials come from environment
variables. Redact before sending any text to an LLM.
"""

import re


class Redactor:
    """Strips router credentials, tokens, and secrets from text before sending to LLMs."""

    # Patterns matching sensitive configuration directives
    _PATTERNS = [
        # username <name> [privilege <num>] (secret|password) [<type>] <secret>
        (
            re.compile(
                r"(username\s+\S+(?:\s+privilege\s+\d+)?\s+(?:secret|password)(?:\s+\d+)?\s+)\S+",
                re.IGNORECASE,
            ),
            r"\1[REDACTED]",
        ),
        # enable (secret|password) [<type>] <secret>
        (
            re.compile(
                r"(enable\s+(?:secret|password)(?:\s+\d+)?\s+)\S+",
                re.IGNORECASE,
            ),
            r"\1[REDACTED]",
        ),
        # key-string <key>
        (
            re.compile(r"(key-string\s+)\S+", re.IGNORECASE),
            r"\1[REDACTED]",
        ),
        # snmp-server community <string>
        (
            re.compile(r"(snmp-server\s+community\s+)\S+", re.IGNORECASE),
            r"\1[REDACTED]",
        ),
        # Bearer tokens
        (
            re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE),
            r"\1[REDACTED]",
        ),
        # Common API keys (OpenAI sk-..., Google Gemini AIzaSy..., etc.)
        (
            re.compile(r"(?:sk-[A-Za-z0-9_\-]{20,}|AIzaSy[A-Za-z0-9_\-]{33})"),
            "[REDACTED]",
        ),
        # Generic key/secret assignments: API_KEY=xyz, password: xyz
        (
            re.compile(
                r"((?:api[_-]?key|password|secret|token)\s*[:=]\s*)\S+",
                re.IGNORECASE,
            ),
            r"\1[REDACTED]",
        ),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        """Strip all credentials and secrets from text."""
        if not text:
            return ""

        result = text
        for pattern, replacement in cls._PATTERNS:
            result = pattern.sub(replacement, result)

        return result

    @classmethod
    def truncate(cls, text: str, max_chars: int = 4000) -> str:
        """Truncate text to a maximum character budget with a clear marker."""
        if not text or len(text) <= max_chars:
            return text

        budget = max(0, max_chars - 15)
        return text[:budget] + "\n[TRUNCATED]"
