"""Offline operator management for the server-side AI provider vault keyring.

Run only while the API is stopped. The tool never prints key material or
secret values. Back up the encrypted vault directory and keyring together via
the approved encrypted backup workflow before rotation or pruning.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import secrets

from app.modules.provider_admin.server_vault import AesGcmSecretVault
from app.modules.provider_admin.vault import VaultUnavailable


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--vault-dir", type=Path, required=True)
    root.add_argument("--key-file", type=Path, required=True)
    actions = root.add_subparsers(dest="action", required=True)
    actions.add_parser("verify", help="Decrypt-verify stored entries; report key-version counts")
    actions.add_parser("rotate", help="Add a new active key while retaining previous versions")
    actions.add_parser("reencrypt", help="Re-encrypt all entries with the active key")
    prune = actions.add_parser("prune", help="Remove an unused inactive key version")
    prune.add_argument("--key-id", required=True)
    return root


def run(args: argparse.Namespace) -> str:
    vault = AesGcmSecretVault(args.vault_dir, args.key_file)
    if args.action == "verify":
        usage = vault.key_usage()
        return "VERIFIED " + " ".join(f"{key_id}={count}" for key_id, count in sorted(usage.items()))
    if args.action == "rotate":
        _active, keys = vault._keyring()
        if len(keys) >= 8:
            raise VaultUnavailable
        key_id = "k" + secrets.token_hex(6)
        vault.rotate_key(key_id)
        return f"ROTATED active_key_id={key_id} previous_versions_retained={len(keys)}"
    if args.action == "reencrypt":
        changed = vault.reencrypt_all()
        usage = vault.key_usage()
        return f"REENCRYPTED entries={sum(usage.values())} changed={changed} active_key_entries={usage.get(vault._keyring()[0], 0)}"
    if args.action == "prune":
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", args.key_id):
            raise VaultUnavailable
        vault.prune_key(args.key_id)
        return f"PRUNED key_id={args.key_id}"
    raise VaultUnavailable


def main() -> int:
    args = parser().parse_args()
    try:
        print(run(args))
    except (OSError, VaultUnavailable):
        print("BLOCKED code=vault_keyring_or_ciphertext_unavailable")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
