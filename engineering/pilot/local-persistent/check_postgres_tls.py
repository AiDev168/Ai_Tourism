"""Private local-pilot DB identity probe; credentials arrive only via process env."""

from __future__ import annotations

import os

import psycopg


def main() -> None:
    with psycopg.connect(
        host=os.environ["DATABASE_HOST"],
        port=int(os.environ["DATABASE_PORT"]),
        dbname=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
        connect_timeout=3,
        application_name="rahgard-local-pilot-tls-check",
    ) as connection:
        actual = connection.execute("SELECT current_database(), current_user").fetchone()
    expected = (os.environ["DATABASE_NAME"], "ai_tourism_app")
    if actual != expected:
        raise RuntimeError("Local pilot TLS probe connected to an unexpected database role.")
    # PGSSLMODE=verify-full is enforced by libpq before the query can succeed.
    print("LOCAL_PILOT_VERIFY_FULL_TLS_OK")


if __name__ == "__main__":
    main()
