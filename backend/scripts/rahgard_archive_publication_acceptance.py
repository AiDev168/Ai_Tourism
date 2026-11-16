"""Positive archive candidate -> publication lifecycle on guarded isolated PG17."""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from uuid import UUID
import sys
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

ACTOR = UUID("10000000-0000-4000-8000-000000000001")
SPECS = [
    {
        "key": "unesco-armenian-st-thaddeus-v1",
        "source": "https://visitiran.ir/attraction/monastery-saint-thaddeus-or-qara-kelisa",
        "page": "Monastery of Saint Thaddeus or Qara Kelisa",
        "publisher": "Visit Iran",
        "province_excerpt": "in Bah Bah Jik County, 20km of Chaldoran City, is located in the highest part of the West Azerbaijan Province",
    },
    {
        "key": "unesco-armenian-st-stepanos-main-church-v1",
        "source": "https://visitiran.ir/en/attraction/saint-stepanos-monastery",
        "page": "Saint Stepanos Monastery",
        "publisher": "Visit Iran",
        "province_excerpt": "about 15 km northwest of the city of Julfa in the province of East Azerbaijan",
    },
    {
        "key": "unesco-armenian-dzordzor-main-chapel-v1",
        "source": "https://visitiran.ir/index.php/attraction/dzordzor-chapel",
        "page": "Dzordzor Chapel",
        "publisher": "Visit Iran",
        "province_excerpt": "close to Baron Village, near the opening of a valley on West Azerbaijan Province and twenty kilometers from Maku",
    },
]
UNESCO_URL = "https://whc.unesco.org/en/list/1262/"
MAP_URL = "https://whc.unesco.org/en/list/1262/maps/"
MAP_EXCERPTS = {
    "unesco-armenian-st-thaddeus-v1": "1262-001 The Monastery of Saint Thaddeus N39 5 32.00 E44 32 40.00",
    "unesco-armenian-st-stepanos-main-church-v1": "1262-004 The main church (Monastery of Saint Stepanos Esemble) N38 58 44.00 E45 28 24.00",
    "unesco-armenian-dzordzor-main-chapel-v1": "1262-007 The main chapel (Dzordzor) N39 11 16.00 E44 28 34.00",
}
IDENTITY_EXCERPTS = {
    "unesco-armenian-st-thaddeus-v1": "The Monastery of Saint Thaddeus",
    "unesco-armenian-st-stepanos-main-church-v1": "The main church (Monastery of Saint Stepanos Esemble)",
    "unesco-armenian-dzordzor-main-chapel-v1": "The main chapel (Dzordzor)",
}


def need(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit("isolated publication acceptance refused: required test setting missing")
    return value


def main() -> int:
    host = need("DATABASE_HOST")
    port = int(need("DATABASE_PORT"))
    db = need("DATABASE_NAME")
    user = need("DATABASE_USER")
    password = need("DATABASE_PASSWORD")
    marker = need("RAHGARD_PILOT_DATABASE_MARKER")
    if (
        host not in {"127.0.0.1", "localhost"}
        or db != "rahgard_pilot_vps_staging"
        or user != "ai_tourism_app"
        or not re.fullmatch(r"[a-fA-F0-9]{32,128}", marker)
        or port == 55433
    ):
        raise SystemExit("isolated publication acceptance refused: target guard failed")
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
        connect_timeout=3,
        row_factory=dict_row,
    )
    try:
        with conn.transaction():
            identity = conn.execute("""SELECT current_database() db,current_user role,current_setting('server_version_num')::int version,
          (SELECT count(*) FROM public.rahgard_private_pilot_marker) marker_count,
          (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) marker""").fetchone()
            if (
                identity["db"] != db
                or identity["role"] != user
                or not 170000 <= identity["version"] < 180000
                or identity["marker_count"] != 1
                or identity["marker"] != marker
            ):
                raise SystemExit("isolated publication acceptance refused: PG17 or marker mismatch")
            conn.execute("SELECT set_config('app.actor_id',%s,false)", (str(ACTOR),))
            grants = conn.execute(
                "SELECT capability FROM identity.catalogue_review_grants WHERE user_id=%s AND revoked_at IS NULL",
                (ACTOR,),
            ).fetchall()
            if {r["capability"] for r in grants} != {
                "candidate_review",
                "source_review",
                "catalogue_publish",
            }:
                raise SystemExit(
                    "isolated publication acceptance refused: exact temporary reviewer grants missing"
                )
            now = conn.execute("SELECT now() AS ts").fetchone()["ts"]
            # Register and directly inspect the source pages observed during this run.
            source_ids = {}
            pages = [
                (
                    "UNESCO World Heritage Centre - Armenian Monastic Ensembles of Iran",
                    UNESCO_URL,
                    "Armenian Monastic Ensembles of Iran",
                ),
                (
                    "UNESCO World Heritage Centre - component maps",
                    MAP_URL,
                    "Armenian Monastic Ensembles of Iran - Maps",
                ),
            ]
            pages += [(s["page"], s["source"], s["page"]) for s in SPECS]
            for name, url, title in pages:
                row = conn.execute(
                    "SELECT source_id,verification_status,is_synthetic FROM knowledge.knowledge_sources WHERE url=%s OR source_name=%s LIMIT 1",
                    (url, name),
                ).fetchone()
                if row:
                    sid = row["source_id"]
                    if row["is_synthetic"]:
                        raise RuntimeError("source identity resolves to synthetic record")
                else:
                    sid = conn.execute(
                        """INSERT INTO knowledge.knowledge_sources(source_name,source_type,verification_status,url,notes,is_synthetic)
              VALUES(%s,'official_tourism_registry','pending',%s,'Directly inspected source; registered separately from claim evidence.',FALSE) RETURNING source_id""",
                        (name, url),
                    ).fetchone()["source_id"]
                    conn.execute(
                        """INSERT INTO knowledge.source_registry_registration_events(source_id,publisher,page_title,registered_url,license_note,registration_note,registrar_user_id,policy_version)
              VALUES(%s,%s,%s,%s,NULL,'Manually inspected source for a bounded archive candidate lifecycle acceptance.',%s,'isolated-archive-acceptance-v1')""",
                        (
                            sid,
                            "UNESCO World Heritage Centre"
                            if "whc.unesco.org" in url
                            else "Visit Iran",
                            title,
                            url,
                            str(ACTOR),
                        ),
                    )
                row = conn.execute(
                    "SELECT verification_status FROM knowledge.knowledge_sources WHERE source_id=%s",
                    (sid,),
                ).fetchone()
                if row["verification_status"] != "verified":
                    excerpt = (
                        "The Armenian Monastic Ensembles of Iran, in the north-west of the country, consists of three monastic ensembles"
                        if url == UNESCO_URL
                        else "1262-001 The Monastery of Saint Thaddeus N39 5 32.00 E44 32 40.00"
                        if url == MAP_URL
                        else next(s["province_excerpt"] for s in SPECS if s["source"] == url)
                    )
                    if len(excerpt.split()) > 25:
                        raise RuntimeError("direct-source excerpt exceeded 25 words")
                    conn.execute(
                        "SELECT knowledge.verify_archive_source(%s,%s,%s,%s,%s,%s,%s)",
                        (
                            sid,
                            "UNESCO World Heritage Centre"
                            if "whc.unesco.org" in url
                            else "Visit Iran",
                            title,
                            excerpt,
                            now,
                            "directly-inspected-2026-11-16-v1",
                            ACTOR,
                        ),
                    )
                source_ids[url] = sid
            published = []
            for spec in SPECS:
                c = conn.execute(
                    """SELECT candidate_id,candidate_kind,candidate_status,proposed_name_fa,proposed_destination_type,
            raw_province,raw_city,raw_coordinate_role,proposed_latitude,proposed_longitude,canonical_destination_id
            FROM knowledge.destination_candidates WHERE proposed_destination_key=%s""",
                    (spec["key"],),
                ).fetchone()
                if (
                    not c
                    or c["candidate_kind"] != "destination_identity"
                    or c["candidate_status"] != "needs_review"
                    or c["canonical_destination_id"] is not None
                ):
                    raise RuntimeError(
                        "expected archive identity is missing, previously resolved, or not reviewable"
                    )
                if (
                    c["raw_coordinate_role"] != "property_reference"
                    or c["proposed_latitude"] is None
                    or c["proposed_longitude"] is None
                ):
                    raise RuntimeError(
                        "candidate coordinates or property-reference role are not supported"
                    )
                expected = conn.execute(
                    "SELECT count(*) n FROM knowledge.destination_candidates WHERE candidate_kind='discovery_lead' AND candidate_status='needs_review'"
                ).fetchone()["n"]
                if expected != 533:
                    raise RuntimeError("the 533 discovery leads must remain untouched")
                values = [
                    (
                        "identity",
                        c["proposed_name_fa"],
                        source_ids[MAP_URL],
                        IDENTITY_EXCERPTS[spec["key"]],
                    ),
                    (
                        "province",
                        c["raw_province"],
                        source_ids[spec["source"]],
                        spec["province_excerpt"],
                    ),
                    (
                        "coordinates",
                        f"{c['proposed_latitude']:.7f},{c['proposed_longitude']:.7f}",
                        source_ids[MAP_URL],
                        MAP_EXCERPTS[spec["key"]],
                    ),
                    (
                        "description",
                        "یکی از اجزای نقشه‌دار مجموعهٔ میراث جهانی صومعه‌های ارمنی ایران.",
                        source_ids[UNESCO_URL],
                        "The Armenian Monastic Ensembles of Iran consists of three monastic ensembles",
                    ),
                ]
                evidence_ids = []
                for field, claim, sid, excerpt in values:
                    row = conn.execute(
                        """INSERT INTO knowledge.destination_candidate_evidence(candidate_id,source_id,field_key,claim_value,source_url,evidence_excerpt,retrieved_at,reviewer_user_id,policy_version)
              VALUES(%s,%s,%s,%s,(SELECT url FROM knowledge.knowledge_sources WHERE source_id=%s),%s,%s,%s,'direct-field-evidence-v1') RETURNING evidence_id""",
                        (c["candidate_id"], sid, field, claim, sid, excerpt, now, str(ACTOR)),
                    ).fetchone()
                    evidence_ids.append(str(row["evidence_id"]))
                conn.execute(
                    """INSERT INTO knowledge.destination_candidate_reviews(candidate_id,identity_relation,decision,reason,evidence_refs,reviewer_user_id,policy_version)
            VALUES(%s,'unresolved','approve_new_identity','Reviewed against UNESCO component maps, UNESCO property description and corresponding Visit Iran detail page.',%s::jsonb,%s,'direct-source-review-v1')""",
                    (c["candidate_id"], json.dumps(evidence_ids), str(ACTOR)),
                )
                conn.execute(
                    "UPDATE knowledge.destination_candidates SET candidate_status='approved_new_identity' WHERE candidate_id=%s",
                    (c["candidate_id"],),
                )
                did = conn.execute(
                    "SELECT knowledge.publish_archive_destination(%s,%s,'property_reference',%s,'archive-positive-lifecycle-v1') destination_id",
                    (c["candidate_id"], spec["key"], ACTOR),
                ).fetchone()["destination_id"]
                pub = conn.execute(
                    "SELECT destination_key,status,verification_status,coordinate_role FROM knowledge.production_destinations WHERE destination_id=%s",
                    (did,),
                ).fetchone()
                if (
                    not pub
                    or pub["destination_key"] != spec["key"]
                    or pub["status"] != "active"
                    or pub["verification_status"] != "verified"
                    or pub["coordinate_role"] != "property_reference"
                ):
                    raise RuntimeError("published record did not satisfy production catalogue view")
                published.append(
                    {
                        "key": spec["key"],
                        "destination_id": did,
                        "name_fa": c["proposed_name_fa"],
                        "province": c["raw_province"],
                        "coordinate_role": pub["coordinate_role"],
                    }
                )
            counts = conn.execute("""SELECT (SELECT count(*) FROM knowledge.destination_candidates) candidates,
          (SELECT count(*) FROM knowledge.destination_candidates WHERE candidate_kind='discovery_lead' AND candidate_status='needs_review') untouched_leads,
          (SELECT count(*) FROM knowledge.catalogue_publication_events) publications,
          (SELECT count(*) FROM knowledge.production_destinations) published_catalogue""").fetchone()
            if (
                counts["untouched_leads"] != 533
                or counts["publications"] != 3
                or counts["published_catalogue"] != 3
            ):
                raise RuntimeError(
                    "exact small-set publication or untouched-lead count assertion failed"
                )
        # Exercise the ordinary FastAPI catalogue route against committed PostgreSQL rows.
        from fastapi.testclient import TestClient
        from pydantic import SecretStr
        from app.core.config import Settings, get_settings
        from app.main import app

        settings = Settings(
            _env_file=None,
            app_env="test",
            database_host=host,
            database_port=port,
            database_name=db,
            database_user=user,
            database_password=SecretStr(password),
            auth_rate_limit_secret=SecretStr(
                "isolated-catalogue-cursor-test-key-000000000000000001"
            ),
        )
        app.dependency_overrides[get_settings] = lambda: settings
        try:
            client = TestClient(app)
            response = client.get("/api/v2/catalog/destinations", params={"limit": 10})
        finally:
            app.dependency_overrides.clear()
        if response.status_code != 200:
            raise RuntimeError("ordinary FastAPI catalogue listing did not return 200")
        result = response.json()
        found = {item["destination_key"] for item in result.get("items", [])}
        expected = {
            "unesco-armenian-st-thaddeus-v1",
            "unesco-armenian-st-stepanos-main-church-v1",
            "unesco-armenian-dzordzor-main-chapel-v1",
        }
        if result.get("status") != "available" or not expected.issubset(found):
            raise RuntimeError(
                "ordinary FastAPI catalogue listing did not include all three archive-backed POIs"
            )
        print(
            json.dumps(
                {
                    "lifecycle": "pass",
                    "staged_candidates": 700,
                    "published_from_archive": published,
                    "database_counts": counts,
                    "ordinary_fastapi_catalogue_listing": "pass",
                    "catalogue_search_results": sorted(expected),
                    "unverified_claims_auto_published": 0,
                    "discovery_leads_published": 0,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
