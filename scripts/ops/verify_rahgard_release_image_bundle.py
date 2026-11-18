#!/usr/bin/env python3
"""Create and verify a secret-free Rahgard Docker image handoff bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_SHA = "d5d9847373b20087a8a866449c6550d306f45b63"
IMAGE_PREFIXES = ("rahgard-api:", "rahgard-web:")
FORBIDDEN_SUFFIXES = (".pem", ".p12", ".pfx", ".dump", ".dump.enc", ".sqlite", ".sqlite3", ".db")
SECRET_ENV = re.compile(r"(?:PASSWORD|SECRET|TOKEN|API_KEY)", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def docker_inspect(reference: str) -> dict[str, Any]:
    result = subprocess.run(
        ["docker", "image", "inspect", reference],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, list) or len(parsed) != 1:
        raise ValueError(f"docker inspect did not return one image for {reference}")
    return parsed[0]


def image_record(reference: str) -> dict[str, Any]:
    image = docker_inspect(reference)
    config = image.get("Config") or {}
    env = config.get("Env") or []
    secret_env = [value.split("=", 1)[0] for value in env if SECRET_ENV.search(value.split("=", 1)[0])]
    if secret_env:
        raise ValueError(f"Image has secret-named environment configuration: {secret_env}")
    labels = config.get("Labels") or {}
    if reference.startswith(IMAGE_PREFIXES):
        if labels.get("org.opencontainers.image.revision") != EXPECTED_SHA:
            raise ValueError(f"Image revision label mismatch for {reference}")
        if image.get("Os") != "linux" or image.get("Architecture") != "amd64":
            raise ValueError(f"Image is not linux/amd64: {reference}")
    record = {
        "tag": reference,
        "image_id": image.get("Id"),
        "os": image.get("Os"),
        "architecture": image.get("Architecture"),
        "repo_digests": sorted(image.get("RepoDigests") or []),
        "entrypoint": config.get("Entrypoint"),
        "command": config.get("Cmd"),
        "labels": labels,
    }
    if not isinstance(record["image_id"], str) or not record["image_id"].startswith("sha256:"):
        raise ValueError(f"Image ID missing for {reference}")
    return record


def assert_safe_member(name: str, *, is_directory: bool = False) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe image archive member: {name}")
    lower_parts = [part.lower() for part in path.parts]
    # Official base OS layers can contain the empty standard /var/backups
    # directory. Permit only this exact directory entry, never files below
    # it or any application/secret backup paths.
    if is_directory and lower_parts == ["var", "backups"]:
        return
    basename = lower_parts[-1] if lower_parts else ""
    if any(part == "secrets" or part == "backups" for part in lower_parts):
        raise ValueError(f"Sensitive path is present in image archive: {name}")
    # Public CA certificates installed by an official OS base image are not
    # application private keys. Allow only PEMs in the standard CA trust store.
    public_ca_pem = (
        basename.endswith(".pem") and (
            lower_parts == ["etc", "ssl", "cert.pem"]  # Alpine trust bundle symlink.
            or (len(lower_parts) == 4 and lower_parts[:3] == ["etc", "ssl", "certs"])
        )
    )
    if basename == ".env" or basename.startswith(".env.") or (
        basename.endswith(FORBIDDEN_SUFFIXES) and not public_ca_pem
    ):
        raise ValueError(f"Sensitive file is present in image archive: {name}")
    if "/run/secrets/" in f"/{'/'.join(lower_parts)}/":
        raise ValueError(f"Runtime-secret path is present in image archive: {name}")


def inspect_docker_save_archive(path: Path, expected_tags: set[str]) -> None:
    with tarfile.open(path, "r:") as archive:
        try:
            manifest_member = archive.getmember("manifest.json")
        except KeyError as error:
            raise ValueError("Docker archive has no manifest.json") from error
        manifest_file = archive.extractfile(manifest_member)
        if manifest_file is None:
            raise ValueError("Docker archive manifest cannot be read")
        records = json.load(manifest_file)
        observed_tags: set[str] = set()
        for record in records:
            observed_tags.update(record.get("RepoTags") or [])
            config_name = record["Config"]
            config_member = archive.extractfile(config_name)
            if config_member is None:
                raise ValueError("Image config is missing from Docker archive")
            config_bytes = config_member.read()
            config_id = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
            digest = config_id.removeprefix("sha256:")
            # Docker archive manifests use either legacy <sha256>.json names or
            # content-addressed blobs/sha256/<sha256> names. Validate both the
            # exact path shape and the actual config bytes; never trust a name
            # without hashing the underlying content.
            legacy_config_path = digest + ".json"
            content_addressed_path = f"blobs/sha256/{digest}"
            if config_name not in (legacy_config_path, content_addressed_path):
                raise ValueError("Image config digest does not match its Docker archive filename")
            config = json.loads(config_bytes)
            env = ((config.get("config") or {}).get("Env") or [])
            secret_env = [value.split("=", 1)[0] for value in env if SECRET_ENV.search(value.split("=", 1)[0])]
            if secret_env:
                raise ValueError(f"Secret-named runtime variables found in image config: {secret_env}")
            labels = (config.get("config") or {}).get("Labels") or {}
            for tag in record.get("RepoTags") or []:
                if tag.startswith(IMAGE_PREFIXES) and labels.get("org.opencontainers.image.revision") != EXPECTED_SHA:
                    raise ValueError(f"Image archive revision label mismatch for {tag}")
            for layer_name in record.get("Layers") or []:
                layer = archive.extractfile(layer_name)
                if layer is None:
                    raise ValueError(f"Image layer is missing: {layer_name}")
                with tarfile.open(fileobj=layer, mode="r|*") as layer_archive:
                    for member in layer_archive:
                        assert_safe_member(member.name, is_directory=member.isdir())
        if observed_tags != expected_tags:
            raise ValueError(f"Docker archive tags differ: expected {sorted(expected_tags)}, got {sorted(observed_tags)}")


def create_manifest(args: argparse.Namespace) -> None:
    if args.source_sha != EXPECTED_SHA:
        raise ValueError("Unexpected immutable source SHA")
    image_tags = args.image_tags
    expected_tags = {f"rahgard-api:{EXPECTED_SHA}", f"rahgard-web:{EXPECTED_SHA}"}
    if set(image_tags) != expected_tags:
        raise ValueError("Exactly the prepared API and Web image tags are required")
    inspect_docker_save_archive(Path(args.image_archive), expected_tags)
    images = {"api" if tag.startswith("rahgard-api:") else "web": image_record(tag) for tag in image_tags}
    bases = {
        "python": image_record(args.api_base),
        "node": image_record(args.node_base),
        "nginx": image_record(args.nginx_base),
    }
    for name, base in bases.items():
        if not base["repo_digests"]:
            raise ValueError(f"Pinned {name} base has no immutable RepoDigest")
    api = images["api"]
    web = images["web"]
    if api["entrypoint"] != ["/usr/local/bin/rahgard-entrypoint"]:
        raise ValueError("API entrypoint differs from the reviewed contract")
    if api["command"] != ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]:
        raise ValueError("API command differs from the reviewed contract")
    if web["command"] != ["nginx", "-g", "daemon off;"]:
        raise ValueError("Web command differs from the reviewed contract")
    source_archive = Path(args.source_archive)
    image_archive = Path(args.image_archive)
    source_sha256 = sha256_file(source_archive)
    image_sha256 = sha256_file(image_archive)
    manifest = {
        "schema_version": 1,
        "source": {
            "repository": "AiDev168/Ai_Tourism",
            "git_sha": args.source_sha,
            "git_archive": source_archive.name,
            "git_archive_sha256": source_sha256,
            "git_archive_bytes": source_archive.stat().st_size,
        },
        "platform": "linux/amd64",
        "base_images": bases,
        "application_images": images,
        "docker_archive": {
            "file": image_archive.name,
            "sha256": image_sha256,
            "bytes": image_archive.stat().st_size,
        },
        "build": {
            "build_command": "docker buildx build --platform linux/amd64 --pull=false --load",
            "dockerfile_api_sha256": sha256_file(Path(args.source_dir) / "deploy/staging/Dockerfile.api"),
            "uv_lock_sha256": sha256_file(Path(args.source_dir) / "uv.lock"),
            "dockerfile_web_sha256": sha256_file(Path(args.source_dir) / "deploy/staging/Dockerfile.web"),
            "package_lock_sha256": sha256_file(Path(args.source_dir) / "frontend/package-lock.json"),
            "runtime_secrets_or_credentials_passed": False,
            "docker_build_args": [],
        },
        "secret_scan": {
            "docker_save_manifest_and_layers": "pass",
            "secret_files_or_secret_named_environment": "none found",
        },
        "created_by": "scripts/ops/build_rahgard_release_images.sh",
    }
    Path(args.output_manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify(args: argparse.Namespace) -> None:
    if args.source_sha != EXPECTED_SHA:
        raise ValueError("Unexpected immutable source SHA")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    image_archive = Path(args.image_archive)
    if manifest.get("schema_version") != 1 or manifest.get("source", {}).get("git_sha") != EXPECTED_SHA:
        raise ValueError("Manifest schema or source SHA does not match the approved release")
    if manifest.get("platform") != "linux/amd64":
        raise ValueError("Manifest platform is not linux/amd64")
    source_record = manifest["source"]
    if not re.fullmatch(r"[0-9a-f]{64}", source_record.get("git_archive_sha256", "")):
        raise ValueError("Manifest source archive checksum is missing or invalid")
    if args.source_archive:
        source = Path(args.source_archive)
        if source.name != source_record.get("git_archive") or sha256_file(source) != source_record["git_archive_sha256"]:
            raise ValueError(f"Source archive checksum or filename mismatch: {source.name}")
    if image_archive.name != manifest["docker_archive"]["file"] or sha256_file(image_archive) != manifest["docker_archive"]["sha256"]:
        raise ValueError(f"Image archive checksum or filename mismatch: {image_archive.name}")
    tags = {record["tag"] for record in manifest["application_images"].values()}
    expected_tags = {f"rahgard-api:{EXPECTED_SHA}", f"rahgard-web:{EXPECTED_SHA}"}
    if tags != expected_tags:
        raise ValueError("Manifest does not identify the exact API/Web release tags")
    inspect_docker_save_archive(image_archive, expected_tags)
    if args.check_loaded_images:
        for name, record in manifest["application_images"].items():
            actual = image_record(record["tag"])
            for key in ("image_id", "os", "architecture", "entrypoint", "command"):
                if actual[key] != record[key]:
                    raise ValueError(f"Loaded {name} image {key} differs from the signed handoff manifest")
            if actual["os"] != "linux" or actual["architecture"] != "amd64":
                raise ValueError(f"Loaded {name} image is not linux/amd64")
            if actual["labels"].get("org.opencontainers.image.revision") != EXPECTED_SHA:
                raise ValueError(f"Loaded {name} image source revision label mismatch")
    print(f"IMAGE_BUNDLE_PASS source={EXPECTED_SHA} platform=linux/amd64 api_web_tags=exact checksums=pass secret_scan=pass")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    for option in ("source-sha", "source-archive", "image-archive", "output-manifest", "api-base", "node-base", "nginx-base", "source-dir"):
        create.add_argument(f"--{option}", required=True)
    create.add_argument("--image-tags", nargs=2, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--source-sha", required=True)
    verify_parser.add_argument("--source-archive")
    verify_parser.add_argument("--image-archive", required=True)
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.add_argument("--check-loaded-images", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        create_manifest(args)
    else:
        verify(args)


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, json.JSONDecodeError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f"IMAGE_BUNDLE_FAIL: {error}", file=__import__("sys").stderr)
        raise SystemExit(1)
