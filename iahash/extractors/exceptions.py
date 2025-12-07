"""Common exceptions for extractor modules."""

from __future__ import annotations

__all__ = ["ExtractorError", "UnreachableSource", "UnsupportedProvider"]


class ExtractorError(Exception):
    """Base class for extractor-related errors."""


class UnreachableSource(ExtractorError):
    """Raised when the shared conversation cannot be downloaded."""


class UnsupportedProvider(ExtractorError):
    """Raised when the given URL does not match a supported provider."""

