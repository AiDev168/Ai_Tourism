#!/usr/bin/env python3
"""Verify exact Rahgard API/Web identities inside a Docker-save archive."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile


def verify(image_archive: Path, identities_path: Path, source_sha: str) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("invalid_source_sha")
    identities: dict[str, str] = {}
    lines = identities_path.read_text(encoding="ascii").splitlines()
    db_tag = "rahgard-postgres:17-postgis36-vector087"
    expected_tags = {f"rahgard-api:{source_sha}", f"rahgard-web:{source_sha}", db_tag}
    for line in lines:
        parts = line.split("|")
        if (len(parts) != 5 or parts[0] not in expected_tags or parts[0] in identities
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", parts[1])
                or parts[2:4] != ["linux", "amd64"]
                or (parts[4] != source_sha if parts[0] != db_tag else parts[4] != "external-db-image")):
            raise ValueError("invalid_image_identity_record")
        identities[parts[0]] = parts[1]
    if set(identities) != expected_tags:
        raise ValueError("image_identity_set_mismatch")

    with tarfile.open(image_archive, "r:") as archive:
        members = archive.getmembers()
        files: dict[str, tarfile.TarInfo] = {}
        for member in members:
            name = member.name
            path = PurePosixPath(name)
            if (not name or "\\" in name or name.startswith("/") or str(path) != name or ".." in path.parts
                    or not member.isfile() or name in files):
                raise ValueError("unsafe_or_duplicate_docker_archive_member")
            files[name] = member
        manifest_member = files.get("manifest.json")
        if manifest_member is None:
            raise ValueError("docker_save_manifest_missing")
        stream = archive.extractfile(manifest_member)
        if stream is None:
            raise ValueError("docker_save_manifest_unreadable")
        manifest = json.load(stream)
        if not isinstance(manifest, list) or len(manifest) != 3:
            raise ValueError("docker_save_image_count_mismatch")

        observed: dict[str, str] = {}
        referenced_files = {"manifest.json"}
        for image in manifest:
            if not isinstance(image, dict) or not isinstance(image.get("RepoTags"), list):
                raise ValueError("docker_save_record_invalid")
            tags = image["RepoTags"]
            if len(tags) != 1 or tags[0] not in expected_tags or tags[0] in observed:
                raise ValueError("docker_save_tag_mismatch")
            config_path = image.get("Config")
            if not isinstance(config_path, str) or config_path not in files:
                raise ValueError("docker_save_config_missing")
            referenced_files.add(config_path)
            layers = image.get("Layers")
            if not isinstance(layers, list) or any(not isinstance(layer, str) or layer not in files for layer in layers):
                raise ValueError("docker_save_layer_missing")
            referenced_files.update(layers)
            config_stream = archive.extractfile(files[config_path])
            if config_stream is None:
                raise ValueError("docker_save_config_unreadable")
            config_bytes = config_stream.read()
            image_id = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
            config = json.loads(config_bytes)
            labels = (config.get("config") or {}).get("Labels") or {}
            if (image_id != identities[tags[0]] or config.get("os") != "linux"
                    or config.get("architecture") != "amd64"
                    or (tags[0] != db_tag and labels.get("org.opencontainers.image.revision") != source_sha)):
                raise ValueError("docker_image_config_identity_mismatch")
            observed[tags[0]] = image_id
        if observed != identities:
            raise ValueError("docker_save_image_identity_set_mismatch")
        if set(files) - referenced_files not in (set(), {"repositories"}):
            raise ValueError("docker_save_contains_unreferenced_files")
    return identities


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image_archive", type=Path)
    parser.add_argument("identities", type=Path)
    parser.add_argument("source_sha")
    args = parser.parse_args()
    try:
        verify(args.image_archive, args.identities, args.source_sha)
    except (OSError, ValueError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"PORTABLE_IMAGE_VALIDATION_FAILED: {exc}")
        return 1
    print(f"PASS: verified API/Web plus PostgreSQL linux/amd64 image identities for {args.source_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
