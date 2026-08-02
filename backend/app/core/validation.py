"""Input validation helpers shared across API routes and the frontend facade."""

from __future__ import annotations

import re

from app.core.exceptions import InvalidRequestError

#: GitHub usernames are 1-39 characters of letters, digits, or single hyphens
#: (no leading/trailing hyphen, no consecutive hyphens).
_GITHUB_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


def validate_github_username(username: str) -> str:
    """Validate ``username`` against GitHub's rules, returning it unchanged.

    Raises :class:`app.core.exceptions.ValidationError` on invalid input.
    """
    value = (username or "").strip()
    if not _GITHUB_USERNAME_RE.fullmatch(value):
        raise InvalidRequestError(
            "github_username must be 1-39 characters of letters, digits, or "
            "single hyphens (no leading/trailing/consecutive hyphens)."
        )
    return value