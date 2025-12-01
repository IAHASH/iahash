from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEYS_DIR = Path("keys")
KEYS_DIR.mkdir(exist_ok=True)

sk = Ed25519PrivateKey.generate()
pk = sk.public_key()

with (KEYS_DIR / "iah_sk.pem").open("wb") as f:
    f.write(
        sk.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

with (KEYS_DIR / "iah_pk.pem").open("wb") as f:
    f.write(
        pk.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

print("Keys generated in ./keys (private + public).")
print("Remember: DO NOT commit iah_sk.pem to Git.")
