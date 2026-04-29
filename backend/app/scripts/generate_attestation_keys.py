"""F30 - Generate an Ed25519 keypair for attestation signing.

Usage::

    python -m app.scripts.generate_attestation_keys

Prints the seed (32 bytes hex) on stdout. Copy the line that begins with
``ATTESTATION_PRIVATE_KEY_HEX=`` into your ``.env`` file. The public key is
derived at runtime from the seed via :func:`crypto.load_keypair`; it is also
echoed here for convenience.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    seed = os.urandom(32)
    private = Ed25519PrivateKey.from_private_bytes(seed)
    public = private.public_key()
    print(f"ATTESTATION_PRIVATE_KEY_HEX={seed.hex()}")
    print(f"# public key (hex): {public.public_bytes_raw().hex()}")


if __name__ == "__main__":
    main()
