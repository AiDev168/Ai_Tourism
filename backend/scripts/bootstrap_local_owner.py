"""Create or recover the sole localhost pilot owner without storing plaintext.

Credentials are read interactively and the command is usable only with the
separate, least-privilege bootstrap DB role on the guarded local pilot DB.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
import sys
from getpass import getpass
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
MIGRATION_013 = ROOT / "engineering" / "pilot" / "sql" / "013_private_pilot_geo_audit.sql"
MIGRATION_014 = ROOT / "engineering" / "pilot" / "sql" / "014_local_owner_login.sql"
sys.path.insert(0, str(BACKEND))
from app.modules.auth.local_owner import create_credential  # noqa: E402

DB_NAME = re.compile(r"^rahgard_pilot_[a-z0-9_]{3,40}$")
MARKER = re.compile(r"^[a-fA-F0-9]{32,128}$")
LOGIN = re.compile(r"^[a-z][a-z0-9._-]{2,39}$")
ROLE = "rahgard_pilot_owner_bootstrap"


class BootstrapBlocked(Exception):
    pass


def _target() -> tuple[str, int, str, str, str]:
    host = os.environ.get("RAHGARD_PILOT_PGHOST", "")
    name = os.environ.get("RAHGARD_PILOT_DATABASE", "")
    marker = os.environ.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    password = os.environ.get("RAHGARD_PILOT_OWNER_BOOTSTRAP_PASSWORD", "")
    try:
        port = int(os.environ.get("RAHGARD_PILOT_PGPORT", ""))
    except ValueError:
        raise BootstrapBlocked("pilot database port is invalid") from None
    if (host not in {"127.0.0.1", "::1"} or not DB_NAME.fullmatch(name)
            or not 1024 <= port <= 65535 or port == 55433 or not MARKER.fullmatch(marker)
            or not password or password != password.strip() or "\n" in password or "\r" in password):
        raise BootstrapBlocked("local pilot database guard is incomplete")
    return host, port, name, marker, password


def _connect() -> tuple[psycopg.Connection[Any], str]:
    host, port, name, marker, password = _target()
    # The identity SELECT below must not open an implicit outer transaction.
    # Otherwise the following connection.transaction() is only a SAVEPOINT:
    # closing the connection rolls back the newly created owner even though
    # the CLI prints success. With autocommit=True the explicit transaction()
    # used for create/reset is the top-level atomic COMMIT boundary.
    connection = psycopg.connect(host=host, port=port, dbname=name, user=ROLE, password=password,
                                 connect_timeout=3, row_factory=dict_row, autocommit=True,
                                 options="-c statement_timeout=10000 -c lock_timeout=3000",
                                 application_name="rahgard-local-owner-bootstrap")
    try:
        state = connection.execute(
            """SELECT current_database() AS name, current_user AS role,
                      current_setting('server_version_num')::integer AS version,
                      (SELECT count(*) FROM public.rahgard_private_pilot_marker) AS marker_count,
                      (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) AS marker,
                      (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0013_private_pilot_geo_audit') AS m13,
                      (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login') AS m14"""
        ).fetchone()
        if (state["name"] != name or state["role"] != ROLE or not 170000 <= state["version"] < 180000
                or state["marker_count"] != 1 or not hmac.compare_digest(state["marker"], marker)
                or str(state["m13"]).strip() != hashlib.sha256(MIGRATION_013.read_bytes()).hexdigest()
                or str(state["m14"]).strip() != hashlib.sha256(MIGRATION_014.read_bytes()).hexdigest()):
            raise BootstrapBlocked("local pilot identity or migration ledger mismatch")
        return connection, marker
    except Exception:
        connection.close()
        raise


def _credential(password: str, owner_id) -> tuple[bytes, bytes, int]:
    material = create_credential(owner_id, password)
    import base64
    salt = base64.urlsafe_b64decode(material.salt_b64 + "=" * (-len(material.salt_b64) % 4))
    verifier = base64.urlsafe_b64decode(material.verifier_b64 + "=" * (-len(material.verifier_b64) % 4))
    return salt, verifier, material.iterations


def _read_password() -> str:
    first = getpass("Local Rahgard owner password (16-256 chars): ")
    second = getpass("Confirm local owner password: ")
    if not hmac.compare_digest(first.encode("utf-8"), second.encode("utf-8")):
        raise BootstrapBlocked("password confirmation did not match")
    return first


def create_owner(login_name: str, password: str) -> None:
    if not LOGIN.fullmatch(login_name):
        raise BootstrapBlocked("owner login name is invalid")
    owner_id = uuid4()
    salt, verifier, iterations = _credential(password, owner_id)
    connection, _ = _connect()
    try:
        with connection.transaction():
            count = connection.execute("SELECT count(*) AS n FROM identity.local_owner_credentials").fetchone()["n"]
            if count != 0:
                raise BootstrapBlocked("local owner is already bootstrapped; use confirmed recovery")
            connection.execute(
                """INSERT INTO identity.users(user_id,auth_subject,display_name)
                   VALUES (%s,'local_owner','Rahgard Owner')""", (owner_id,)
            )
            connection.execute(
                """INSERT INTO identity.local_owner_credentials
                   (owner_id,login_name,salt,verifier,iterations) VALUES (%s,%s,%s,%s,%s)""",
                (owner_id,login_name,salt,verifier,iterations),
            )
        # A success message is permitted only after the explicit transaction
        # has committed and the restricted bootstrap role can read it back.
        saved = connection.execute(
            "SELECT owner_id FROM identity.local_owner_credentials WHERE login_name=%s",
            (login_name,),
        ).fetchone()
        if saved is None or saved["owner_id"] != owner_id:
            raise BootstrapBlocked("local owner credential was not durably committed")
    finally:
        connection.close()


def reset_owner(login_name: str, password: str) -> None:
    if not LOGIN.fullmatch(login_name):
        raise BootstrapBlocked("owner login name is invalid")
    connection, _ = _connect()
    try:
        with connection.transaction():
            row = connection.execute(
                "SELECT owner_id FROM identity.local_owner_credentials WHERE login_name=%s",
                (login_name,),
            ).fetchone()
            if row is None:
                raise BootstrapBlocked("local owner credential does not exist")
            # Match the application session issuer's advisory lock. A reset
            # cannot race a login using the previous password verifier.
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ("rahgard:local-owner-credential:" + str(row["owner_id"]),),
            )
            salt, verifier, iterations = _credential(password, row["owner_id"])
            connection.execute(
                """UPDATE identity.local_owner_credentials
                   SET salt=%s,verifier=%s,iterations=%s WHERE owner_id=%s""",
                (salt,verifier,iterations,row["owner_id"]),
            )
            connection.execute(
                """UPDATE identity.web_sessions SET revoked_at=now(),revoked_reason='owner_password_reset'
                   WHERE user_id=%s AND revoked_at IS NULL""", (row["owner_id"],)
            )
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create-owner", action="store_true")
    action.add_argument("--confirm-password-reset", action="store_true")
    parser.add_argument("--login-name", default="owner")
    args = parser.parse_args()
    try:
        password = _read_password()
        if args.create_owner:
            create_owner(args.login_name, password)
            print("Local owner account created. Password material stored as a one-way verifier.")
        else:
            reset_owner(args.login_name, password)
            print("Local owner password replaced; prior sessions revoked.")
        return 0
    except (BootstrapBlocked, psycopg.Error, OSError, ValueError):
        print("BLOCKED: local owner account was not changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
