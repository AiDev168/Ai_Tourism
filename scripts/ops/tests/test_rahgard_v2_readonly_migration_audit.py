from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ops import execute_rahgard_v2_live_migrations as audit


SHA = "36625ecf269c2a3d5590528257d32af2b6f47dd0"
VOLUME = "rahgard_staging_pgdata"
OWNER = "ai_tourism_owner"
TAIL = [
    "0022_traveler_company_requests|e6b7db49abc0ff76c2620b2cc8d5dded0f4255f8533efd20bd5b402a0ba57eda",
    "0023_partner_trip_responses|deef8c5016f26aa646b9ff22346fad4ade3c6780ff447f701aa9e8a8e28571ac",
]


class ReadOnlyMigrationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        current = self.root / "current"
        current.mkdir()
        (current / "RELEASE_COMMIT").write_text(audit.LEGACY_CURRENT_SHA + "\n", encoding="ascii")
        release = self.root / "releases" / SHA
        release.mkdir(parents=True)
        (release / "RELEASE_COMMIT").write_text(SHA + "\n", encoding="ascii")
        state = self.root / "state"
        state.mkdir()
        (state / "database-marker").write_text("a" * 48 + "\n", encoding="ascii")
        self.ledger = [f"prior_{i:04d}|{'b' * 64}" for i in range(1, 21)] + TAIL
        self.ledger_sha = hashlib.sha256(("\n".join(self.ledger) + "\n").encode()).hexdigest()
        env_lines = [
            "RAHGARD_PUBLIC_HOST=hinaa.ir", f"RAHGARD_RELEASE_SHA={SHA}",
            "RAHGARD_WEB_BIND_PORT=18081", "RAHGARD_COMPOSE_PROJECT=rahgard-staging",
            f"RAHGARD_PG_VOLUME={VOLUME}", "RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED=true",
            "RAHGARD_BUILD_IMAGES=false", "PRIVATE_TEST_SECRET=not-logged",
        ]
        env = self.root / ".env.v2"
        env.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        env.chmod(0o600)
        self.digest_patcher = patch.object(audit, "EXPECTED_LEDGER_SHA256", self.ledger_sha)
        self.digest_patcher.start()
        self.addCleanup(self.digest_patcher.stop)
        self.mode_patcher = patch.object(audit.stat, "S_IMODE", return_value=0o600)
        self.mode_patcher.start()
        self.addCleanup(self.mode_patcher.stop)
        self.readonly_calls: list[str] = []

    def tearDown(self) -> None:
        self.temp.cleanup()

    def setup_probes(self, *, api_sha: str = SHA, volume: str = VOLUME, ledger: list[str] | None = None) -> None:
        selected_ledger = ledger or self.ledger

        def inspect(name: str):
            if name == audit.DATABASE_CONTAINER:
                return {"State": {"Running": True, "Health": {"Status": "healthy"}},
                        "Config": {"Image": audit.DATABASE_IMAGE}, "Image": audit.EXPECTED_IMAGE_IDS["database"],
                        "Mounts": [{"Destination": "/var/lib/postgresql/data", "Type": "volume", "Name": volume}]}
            service = "api" if name == audit.API_CONTAINER else "web"
            return {"State": {"Running": True, "Health": {"Status": "healthy"}},
                    "Config": {"Image": f"rahgard-{service}:{api_sha}"},
                    "Image": (audit.EXPECTED_IMAGE_IDS[service] if api_sha == SHA else "sha256:" + "0" * 64)}

        def query(sql: str):
            self.readonly_calls.append(sql)
            self.assertTrue(sql.startswith("BEGIN READ ONLY;"))
            self.assertIn("COMMIT;", sql)
            marker = "a" * 48
            return [
                f"identity|{audit.DATABASE}|{OWNER}|170006|{OWNER}",
                "marker|1" if f"marker_value='{marker}'" in sql else "marker|0",
                *["ledger|" + row for row in selected_ledger],
            ]

        self.inspect_patcher = patch.object(audit, "inspect_json", side_effect=inspect)
        self.query_patcher = patch.object(audit, "readonly_query", side_effect=query)
        self.inspect_patcher.start()
        self.query_patcher.start()
        self.addCleanup(self.inspect_patcher.stop)
        self.addCleanup(self.query_patcher.stop)

    def test_live_0023_is_explicitly_already_applied_and_no_ddl(self) -> None:
        self.setup_probes()
        result = audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256=self.ledger_sha,
                              expected_volume=VOLUME, expected_owner=OWNER)
        self.assertEqual(result["status"], "ALREADY_APPLIED_NO_DDL")
        self.assertEqual(result["migration_count"], 22)
        self.assertFalse(result["ddl_executed"])
        self.assertEqual(len(self.readonly_calls), 1)
        self.assertFalse(any("ALTER " in sql or "CREATE " in sql or "DROP " in sql for sql in self.readonly_calls))

    def test_incomplete_or_unexpected_ledger_fails_closed(self) -> None:
        self.setup_probes(ledger=self.ledger[:-1])
        with self.assertRaisesRegex(audit.SafetyError, "ledger count"):
            audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256=self.ledger_sha,
                         expected_volume=VOLUME, expected_owner=OWNER)

    def test_runtime_sha_mismatch_fails_closed(self) -> None:
        self.setup_probes(api_sha="5e2664fb51e18f52549aa37a8b5793e12ace09b2")
        with self.assertRaisesRegex(audit.SafetyError, "immutable release"):
            audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256=self.ledger_sha,
                         expected_volume=VOLUME, expected_owner=OWNER)

    def test_volume_mismatch_fails_closed(self) -> None:
        self.setup_probes(volume="unexpected_volume")
        with self.assertRaisesRegex(audit.SafetyError, "persistent volume"):
            audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256=self.ledger_sha,
                         expected_volume=VOLUME, expected_owner=OWNER)

    def test_wrong_requested_owner_fails_before_database_access(self) -> None:
        self.setup_probes()
        with self.assertRaisesRegex(audit.SafetyError, "owner or protected volume"):
            audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256=self.ledger_sha,
                         expected_volume=VOLUME, expected_owner="postgres")
        self.assertEqual(self.readonly_calls, [])

    def test_wrong_live_ledger_attestation_fails_before_database_access(self) -> None:
        self.setup_probes()
        with self.assertRaisesRegex(audit.SafetyError, "independently captured live PG17 ledger"):
            audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256="0" * 64,
                         expected_volume=VOLUME, expected_owner=OWNER)
        self.assertEqual(self.readonly_calls, [])

    def test_broad_runtime_config_permissions_fail_closed(self) -> None:
        self.setup_probes()
        with patch.object(audit.stat, "S_IMODE", return_value=0o644):
            with self.assertRaisesRegex(audit.SafetyError, "permissions must be exactly 0600"):
                audit.verify(root=self.root, expected_release_sha=SHA, expected_ledger_sha256=self.ledger_sha,
                             expected_volume=VOLUME, expected_owner=OWNER)


if __name__ == "__main__":
    unittest.main()
