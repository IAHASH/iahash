"""Utility helpers for locating runtime directories.

This module centralises how the application discovers runtime paths so
that tests can isolate key material without depending on the repository
layout. The directory can be overridden with the ``IAHASH_KEYS_DIR``
environment variable; otherwise ``./keys`` is used.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_keys_dir() -> Path:
    """Return the directory that holds the Ed25519 keypair."""
    return Path(os.getenv("IAHASH_KEYS_DIR", "keys"))


def private_key_path() -> Path:
    return get_keys_dir() / "iah_sk.pem"


def public_key_path() -> Path:
    return get_keys_dir() / "iah_pk.pem"
