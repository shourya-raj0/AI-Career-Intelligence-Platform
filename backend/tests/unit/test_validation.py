"""Tests for input validation helpers."""

from __future__ import annotations

import pytest

from app.core.exceptions import InvalidRequestError
from app.core.validation import validate_github_username


@pytest.mark.parametrize(
    "username",
    [
        "octocat",
        "torvalds",
        "user-name",
        "a",
        "a" * 39,
        "Mixed-Case-123",
    ],
)
def test_valid_usernames_returned_unchanged(username: str) -> None:
    assert validate_github_username(username) == username


@pytest.mark.parametrize(
    "username",
    [
        "",
        "   ",
        "-leading",
        "trailing-",
        "double--hyphen",
        "bad name",
        "spaces here",
        "under_score",
        "a" * 40,
        "@user",
        "user.name",
    ],
)
def test_invalid_usernames_raise(username: str) -> None:
    with pytest.raises(InvalidRequestError):
        validate_github_username(username)


def test_whitespace_is_stripped() -> None:
    assert validate_github_username("  octocat  ") == "octocat"