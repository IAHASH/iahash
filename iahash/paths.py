"""Path helpers for IA-HASH deployment."""

from __future__ import annotations

import os
from pathlib import Path


def get_keys_dir() -> Path:
    """Return the directory containing issuer keys.

    Falls back to ``/data/keys`` when the ``IAHASH_KEYS_DIR`` environment
    variable is not defined.
    """

    env_value = os.getenv("IAHASH_KEYS_DIR")
    if env_value:
        return Path(env_value)
    return Path("/data/keys")

