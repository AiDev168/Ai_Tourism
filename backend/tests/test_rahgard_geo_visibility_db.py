"""Opt-in REAL PostgreSQL 17 acceptance of the geo-only catalogue path.

This test creates QA-only approvals in an already marker-verified, disposable
database. It must NEVER be run against a persistent/shared PostgreSQL server.
It does not represent owner approval for public destination publication.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.rows import dict_row

from scripts.rahgard_geo_visibility import (
    APPROVE,
    POINTS,
    apply_geo_review,
    template,
)

@pytest.mark.skipif(
    os.getenv("AUTH_INTEGRATION_TESTS") != "1"
    or os.getenv("RAHGARD_RUN_GEO_QA") != "1",
    reason="requires explicit opt-in and disposable marker-validated PG17",
)
def test_four_real_canonical_geo_identities_flow_into_app_read_view():
    packet = template()
    packet.update({
        "reviewer": "QA_ONLY_disposable_postgresql",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "approval_reference": "QA_ONLY_NOT_PUBLICATION_AUTHORIZATION",
    })
    for record in packet["records"]:
        record["decision"] = APPROVE

    # The operator helper checks exact database name, app-independent owner
    # identity, version 17, SHA of migration 0012 and random safety marker.
    report = apply_geo_review(packet, explicitly_authorized=True)
    assert report["status"] == "isolated_geo_catalogue_published"
    assert report["visible_approved"] == 4

    # Normal app-role SELECT; no test-only monkeypatch, identity substitution
    # or in-memory coordinate projection is used.
    with psycopg.connect(
        host=os.environ["AUTH_TEST_DATABASE_HOST"],
        port=int(os.environ["AUTH_TEST_DATABASE_PORT"]),
        dbname=os.environ["AUTH_TEST_DATABASE_NAME"],
        user=os.environ["AUTH_TEST_DATABASE_USER"],
        password=os.environ["AUTH_TEST_DATABASE_PASSWORD"],
        connect_timeout=3,
        row_factory=dict_row,
    ) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        rows = connection.execute(
            """SELECT destination_key, canonical_name, latitude, longitude,
                      coordinate_role, city_name, province_name
               FROM knowledge.production_destinations
               WHERE destination_key=ANY(%s::TEXT[])""",
            (list(POINTS),),
        ).fetchall()
        sources = connection.execute(
            """SELECT d.destination_key, COUNT(*) AS source_count
               FROM knowledge.production_destinations d
               JOIN knowledge.production_destination_sources ds
                 ON ds.destination_id=d.destination_id
               WHERE d.destination_key=ANY(%s::TEXT[])
               GROUP BY d.destination_key""",
            (list(POINTS),),
        ).fetchall()

    assert len(rows) == 4
    for row in rows:
        expected = POINTS[row["destination_key"]]
        assert row["canonical_name"] == expected["canonical_name"]
        assert row["coordinate_role"] == expected["coordinate_role"]
        assert abs(float(row["latitude"]) - expected["latitude"]) < 1e-7
        assert abs(float(row["longitude"]) - expected["longitude"]) < 1e-7
        assert row["province_name"] == "فارس"
        assert row["city_name"] == expected["city_name"]
    assert len(sources) == 4
    assert all(row["source_count"] >= 1 for row in sources)
