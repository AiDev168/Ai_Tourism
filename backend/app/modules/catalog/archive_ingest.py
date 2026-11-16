"""Bounded archive-to-review-queue ingestion. Never writes canonical destinations."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Iterator, Mapping
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.modules.identity.auth_service import AuthenticatedUser
from scripts.rahgard_archive_preflight import UnsafeArchive, inspect

_ALIASES = {
    "name": ("name", "name_fa", "canonical_name", "title", "poi_name", "نام", "نام مکان"),
    "province": ("province", "province_name", "استان"),
    "city": ("city", "city_name", "county", "شهر", "شهرستان"),
    "record_key": (
        "destination_key",
        "record_key",
        "external_id",
        "poi_id",
        "feature_id",
        "place_id",
        "destination_id",
        "id",
    ),
    "latitude": ("latitude", "lat", "y"),
    "longitude": ("longitude", "lon", "lng", "x"),
    "coordinate_role": ("coordinate_role", "coordinate_type", "location_role"),
    "destination_type": ("destination_type", "type", "category", "kind"),
}


def _key(row: Mapping[str, Any], names: tuple[str, ...]) -> str | None:
    folded = {str(k).strip().casefold(): v for k, v in row.items()}
    for name in names:
        value = folded.get(name.casefold())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _walk_csv(data: bytes, prefix: str = "", depth: int = 0) -> Iterator[tuple[str, bytes]]:
    if depth > 3:
        raise UnsafeArchive("nested ZIP depth exceeded")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or any(x in {"", ".", ".."} for x in name.split("/")):
                raise UnsafeArchive("unsafe archive member path")
            body = archive.read(info)
            path = f"{prefix}!{name}" if prefix else name
            if name.casefold().endswith(".zip"):
                yield from _walk_csv(body, path, depth + 1)
            elif name.casefold().endswith(".csv"):
                yield path, body


def stage_archive(data: bytes, user: AuthenticatedUser, settings: Settings) -> dict[str, Any]:
    """Inspect and stage candidate rows transactionally; requires DB catalogue grant/RLS."""
    manifest = inspect(data)
    archive_hash = hashlib.sha256(data).hexdigest()
    batch_key = f"upload:{archive_hash}"
    staged = 0
    conflicts = 0
    try:
        with (
            psycopg.connect(
                host=settings.database_host,
                port=settings.database_port,
                dbname=settings.database_name,
                user=settings.database_user,
                password=settings.database_password.get_secret_value(),
                connect_timeout=settings.database_connect_timeout_seconds,
                application_name="rahgard-catalogue-archive-stage",
                row_factory=dict_row,
            ) as conn,
            conn.cursor() as cur,
        ):
            cur.execute("SELECT set_config('app.actor_id', %s, true)", (str(user.user_id),))
            cur.execute(
                "SELECT identity.has_catalogue_review_capability(%s,'candidate_review') AS allowed",
                (user.user_id,),
            )
            if not cur.fetchone()["allowed"]:
                raise PermissionError("catalogue review capability required")
            cur.execute(
                """INSERT INTO operations.dataset_import_batches
                (batch_key,data_class,record_counts,source_checksum,notes)
                VALUES (%s,'user_supplied_unverified','{}'::jsonb,%s,'Archive candidate staging; publication prohibited')
                ON CONFLICT (batch_key) DO NOTHING
                RETURNING dataset_import_batch_id,source_checksum,data_class""",
                (batch_key, archive_hash),
            )
            batch = cur.fetchone()
            if batch is None:
                cur.execute(
                    "SELECT dataset_import_batch_id,source_checksum,data_class FROM operations.dataset_import_batches WHERE batch_key=%s",
                    (batch_key,),
                )
                batch = cur.fetchone()
            if (
                batch is None
                or batch["source_checksum"].strip() != archive_hash
                or batch["data_class"] != "user_supplied_unverified"
            ):
                raise ValueError("existing archive batch identity conflicts with this delivery")
            batch_id = batch["dataset_import_batch_id"]
            for path, body in _walk_csv(data):
                digest = hashlib.sha256(body).hexdigest()
                text = body.decode("utf-8-sig", errors="strict")
                reader = csv.DictReader(io.StringIO(text, newline=""))
                if not reader.fieldnames:
                    continue
                signature = hashlib.sha256("\0".join(reader.fieldnames).encode()).hexdigest()
                rows = list(reader)
                cur.execute(
                    """INSERT INTO operations.dataset_import_files
                    (dataset_import_batch_id,relative_path,file_sha256,byte_size,format,schema_signature,row_count,accepted_count,import_status,parsed_at)
                    VALUES (%s,%s,%s,%s,'csv',%s,%s,%s,'review_ready',now())
                    ON CONFLICT (dataset_import_batch_id,relative_path,file_sha256) DO UPDATE SET row_count=EXCLUDED.row_count
                    RETURNING file_id""",
                    (batch_id, path, digest, len(body), signature, len(rows), len(rows)),
                )
                file_id = cur.fetchone()["file_id"]
                for index, row in enumerate(rows, start=2):
                    raw = dict(row)
                    row_hash = hashlib.sha256(
                        json.dumps(
                            raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest()
                    record_key = (
                        _key(raw, _ALIASES["record_key"]) or f"line:{index}:{row_hash[:20]}"
                    )
                    name = _key(raw, _ALIASES["name"])
                    province, city = _key(raw, _ALIASES["province"]), _key(raw, _ALIASES["city"])
                    lat, lon = _key(raw, _ALIASES["latitude"]), _key(raw, _ALIASES["longitude"])
                    latitude = float(lat) if lat and re.fullmatch(r"-?\d+(?:\.\d+)?", lat) else None
                    longitude = (
                        float(lon) if lon and re.fullmatch(r"-?\d+(?:\.\d+)?", lon) else None
                    )
                    if (latitude is None) != (longitude is None) or (
                        latitude is not None
                        and not (-90 <= latitude <= 90 and -180 <= longitude <= 180)
                    ):
                        latitude = longitude = None
                    cur.execute(
                        """INSERT INTO knowledge.destination_candidates
                        (dataset_import_batch_id,file_id,source_file_sha256,source_record_key,row_sha256,raw_record,raw_name,raw_province,raw_city,raw_coordinate_role,proposed_destination_key,proposed_name_fa,proposed_destination_type,proposed_latitude,proposed_longitude)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (source_file_sha256,source_record_key) DO NOTHING
                        RETURNING candidate_id""",
                        (
                            batch_id,
                            file_id,
                            digest,
                            record_key,
                            row_hash,
                            Jsonb(raw),
                            name,
                            province,
                            city,
                            _key(raw, _ALIASES["coordinate_role"]),
                            _key(raw, _ALIASES["record_key"]),
                            name,
                            _key(raw, _ALIASES["destination_type"]),
                            latitude,
                            longitude,
                        ),
                    )
                    if cur.fetchone():
                        staged += 1
                    else:
                        cur.execute(
                            """SELECT row_sha256 FROM knowledge.destination_candidates
                            WHERE source_file_sha256=%s AND source_record_key=%s""",
                            (digest, record_key),
                        )
                        existing = cur.fetchone()
                        if existing and existing["row_sha256"] != row_hash:
                            conflicts += 1
            if conflicts:
                raise ValueError("archive contains conflicting repeated source identities")
    except (psycopg.Error, OSError, UnicodeError, ValueError, UnsafeArchive):
        raise
    return {
        "batch_key": batch_key,
        "archive_sha256": archive_hash,
        "members": manifest["member_count"],
        "csv_files": manifest["csv_file_count"],
        "rows_staged": staged,
        "conflicts": conflicts,
        "publication_approved": False,
    }
