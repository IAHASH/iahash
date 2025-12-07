from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iahash.paths import get_keys_dir


@pytest.fixture
def temp_keys(tmp_path, monkeypatch) -> Path:
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(key_dir))
    monkeypatch.setenv("IAHASH_KEY_DIR", str(key_dir))

    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key()

    (key_dir / "issuer_ed25519.private").write_bytes(
        sk.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    (key_dir / "issuer_ed25519.pub").write_bytes(
        pk.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    assert get_keys_dir() == key_dir
    return key_dir
