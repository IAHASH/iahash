"""Exercise the actual startup key block in subprocesses with isolated paths."""

import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEY_ENV = (
    "IAHASH_KEY_DIR",
    "IAHASH_KEYS_DIR",
    "IAHASH_PRIVATE_KEY_FILE",
    "IAHASH_PUBLIC_KEY_FILE",
    "IAHASH_ALLOW_KEY_INITIALIZATION",
)


def run_key_startup(key_dir, *, prelude="", **overrides):
    script = (PROJECT_ROOT / "start.sh").read_text(encoding="utf-8")
    block = re.search(r"python3 - <<'PY'\n(.*?)\nPY", script, re.DOTALL)
    assert block is not None, "Startup key validation block is missing"
    env = os.environ.copy()
    for name in KEY_ENV:
        env.pop(name, None)
    env["IAHASH_KEY_DIR"] = str(key_dir)
    env.update(overrides)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT), env.get("PYTHONPATH", "")]
    )
    # Also support isolated/embedded interpreters that ignore PYTHONPATH.
    bootstrap = "import sys\nsys.path[:0] = " + repr(
        [str(PROJECT_ROOT), *[entry for entry in sys.path if entry]]
    ) + "\n"
    return subprocess.run(
        [sys.executable, "-c", bootstrap + prelude + "\n" + block.group(1)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def private_bytes(key):
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def public_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def test_new_identity_requires_explicit_initialization(tmp_path):
    key_dir = tmp_path / "keys"
    result = run_key_startup(key_dir)
    assert result.returncode != 0
    assert "IAHASH_ALLOW_KEY_INITIALIZATION=1 required" in result.stderr
    assert not key_dir.exists()


def test_explicit_initialization_and_restarts_keep_identity(tmp_path):
    key_dir = tmp_path / "keys"
    result = run_key_startup(key_dir, IAHASH_ALLOW_KEY_INITIALIZATION="1")
    assert result.returncode == 0, result.stderr
    private_path = key_dir / "issuer_ed25519.private"
    public_path = key_dir / "issuer_ed25519.pub"
    original_private = private_path.read_bytes()
    original_public = public_path.read_bytes()
    key = serialization.load_pem_private_key(original_private, password=None)
    assert isinstance(key, Ed25519PrivateKey)
    assert original_public == public_bytes(key)
    if os.name == "posix":
        assert private_path.stat().st_mode & 0o777 == 0o600
        assert public_path.stat().st_mode & 0o777 == 0o644

    for _ in range(3):
        result = run_key_startup(key_dir)
        assert result.returncode == 0, result.stderr
        assert private_path.read_bytes() == original_private
        assert public_path.read_bytes() == original_public


def test_missing_public_key_recovers_from_existing_private(tmp_path):
    key = Ed25519PrivateKey.generate()
    private_path = tmp_path / "issuer_ed25519.private"
    original = private_bytes(key)
    private_path.write_bytes(original)
    result = run_key_startup(tmp_path)
    assert result.returncode == 0, result.stderr
    assert private_path.read_bytes() == original
    assert (tmp_path / "issuer_ed25519.pub").read_bytes() == public_bytes(key)


def test_missing_private_key_never_replaces_existing_public(tmp_path):
    public_path = tmp_path / "issuer_ed25519.pub"
    original = public_bytes(Ed25519PrivateKey.generate())
    public_path.write_bytes(original)
    result = run_key_startup(tmp_path, IAHASH_ALLOW_KEY_INITIALIZATION="1")
    assert result.returncode != 0
    assert "Private key missing" in result.stderr
    assert public_path.read_bytes() == original
    assert not (tmp_path / "issuer_ed25519.private").exists()


def test_mismatched_keys_are_preserved(tmp_path):
    private_path = tmp_path / "issuer_ed25519.private"
    public_path = tmp_path / "issuer_ed25519.pub"
    original_private = private_bytes(Ed25519PrivateKey.generate())
    original_public = public_bytes(Ed25519PrivateKey.generate())
    private_path.write_bytes(original_private)
    public_path.write_bytes(original_public)
    result = run_key_startup(tmp_path, IAHASH_ALLOW_KEY_INITIALIZATION="1")
    assert result.returncode != 0
    assert "public/private keys mismatch" in result.stderr
    assert private_path.read_bytes() == original_private
    assert public_path.read_bytes() == original_public


@pytest.mark.parametrize("contents", [b"", b"corrupted private key"])
def test_corrupt_private_key_is_preserved(tmp_path, contents):
    private_path = tmp_path / "issuer_ed25519.private"
    private_path.write_bytes(contents)
    result = run_key_startup(tmp_path, IAHASH_ALLOW_KEY_INITIALIZATION="1")
    assert result.returncode != 0
    assert private_path.read_bytes() == contents
    assert not (tmp_path / "issuer_ed25519.pub").exists()


def test_non_ed25519_private_key_is_preserved(tmp_path):
    private_path = tmp_path / "issuer_ed25519.private"
    original = private_bytes(ec.generate_private_key(ec.SECP256R1()))
    private_path.write_bytes(original)
    result = run_key_startup(tmp_path)
    assert result.returncode != 0
    assert "not Ed25519" in result.stderr
    assert private_path.read_bytes() == original
    assert not (tmp_path / "issuer_ed25519.pub").exists()


@pytest.mark.parametrize("directory_env", ["IAHASH_KEY_DIR", "IAHASH_KEYS_DIR"])
def test_startup_respects_existing_key_directory_overrides(tmp_path, directory_env):
    selected_dir = tmp_path / "selected"
    overrides = {
        "IAHASH_KEY_DIR": "",  # Allow the legacy plural setting to take effect.
        directory_env: str(selected_dir),
        "IAHASH_ALLOW_KEY_INITIALIZATION": "1",
    }
    result = run_key_startup(tmp_path / "unused", **overrides)
    assert result.returncode == 0, result.stderr
    assert (selected_dir / "issuer_ed25519.private").exists()
    assert (selected_dir / "issuer_ed25519.pub").exists()
    assert not (tmp_path / "unused").exists()


def test_startup_respects_independent_key_file_overrides(tmp_path):
    private_path = tmp_path / "private" / "issuer.pem"
    public_path = tmp_path / "public" / "issuer.pem"
    result = run_key_startup(
        tmp_path / "unused",
        IAHASH_ALLOW_KEY_INITIALIZATION="1",
        IAHASH_PRIVATE_KEY_FILE=str(private_path),
        IAHASH_PUBLIC_KEY_FILE=str(public_path),
    )
    assert result.returncode == 0, result.stderr
    original_private = private_path.read_bytes()
    original_public = public_path.read_bytes()
    result = run_key_startup(
        tmp_path / "unused",
        IAHASH_PRIVATE_KEY_FILE=str(private_path),
        IAHASH_PUBLIC_KEY_FILE=str(public_path),
    )
    assert result.returncode == 0, result.stderr
    assert private_path.read_bytes() == original_private
    assert public_path.read_bytes() == original_public
    assert not (tmp_path / "unused").exists()


def test_concurrent_private_key_creation_is_never_overwritten(tmp_path):
    # Deterministically introduce another writer after the existence check, at
    # key generation. This reproduces the old write_bytes overwrite window.
    prelude = '''
from pathlib import Path
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
original_generate = Ed25519PrivateKey.generate
def generate_with_competing_writer():
    target = Path(os.environ["IAHASH_KEY_DIR"]) / "issuer_ed25519.private"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"concurrent private identity: preserve me")
    return original_generate()
Ed25519PrivateKey.generate = staticmethod(generate_with_competing_writer)
'''
    result = run_key_startup(
        tmp_path, prelude=prelude, IAHASH_ALLOW_KEY_INITIALIZATION="1"
    )
    assert result.returncode != 0
    assert "FileExistsError" in result.stderr
    assert (tmp_path / "issuer_ed25519.private").read_bytes() == (
        b"concurrent private identity: preserve me"
    )
    assert not (tmp_path / "issuer_ed25519.pub").exists()


def test_private_key_is_created_restrictively_before_writing(tmp_path):
    prelude = '''
import os
original_open = os.open
os.umask(0o022)
def checked_open(path, flags, mode=0o777, **kwargs):
    if str(path).endswith("issuer_ed25519.private"):
        assert mode == 0o600
        assert flags & os.O_EXCL
        fd = original_open(path, flags, mode, **kwargs)
        if os.name == "posix":
            assert os.fstat(fd).st_mode & 0o777 == 0o600
        print("Private key created with restrictive mode before content is written")
        return fd
    return original_open(path, flags, mode, **kwargs)
os.open = checked_open
'''
    result = run_key_startup(
        tmp_path, prelude=prelude, IAHASH_ALLOW_KEY_INITIALIZATION="1"
    )
    assert result.returncode == 0, result.stderr
    assert "restrictive mode before content is written" in result.stdout


def test_concurrent_public_key_recovery_is_never_overwritten(tmp_path):
    private_path = tmp_path / "issuer_ed25519.private"
    original_private = private_bytes(Ed25519PrivateKey.generate())
    private_path.write_bytes(original_private)
    # Simulate a writer immediately after the public-path check reports absence,
    # before the exclusive open. Only one check should control recovery.
    prelude = '''
from pathlib import Path
import os
target = Path(os.environ["IAHASH_KEY_DIR"]) / "issuer_ed25519.pub"
original_exists = Path.exists
def exists_with_competing_writer(path):
    if path == target:
        target.write_bytes(b"concurrent public identity: preserve me")
        return False
    return original_exists(path)
Path.exists = exists_with_competing_writer
'''
    result = run_key_startup(tmp_path, prelude=prelude)
    assert result.returncode != 0
    assert "FileExistsError" in result.stderr
    assert private_path.read_bytes() == original_private
    assert (tmp_path / "issuer_ed25519.pub").read_bytes() == (
        b"concurrent public identity: preserve me"
    )
