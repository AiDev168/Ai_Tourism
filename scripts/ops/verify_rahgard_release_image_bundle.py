#!/usr/bin/env python3
"""Create and verify a secret-free Rahgard Docker image handoff bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

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


def image_record(
    reference: str,
    *,
    expected_source_sha: str | None = None,
    include_runtime_details: bool = False,
) -> dict[str, Any]:
    image = docker_inspect(reference)
    config = image.get("Config") or {}
    env = config.get("Env") or []
    secret_env = [value.split("=", 1)[0] for value in env if SECRET_ENV.search(value.split("=", 1)[0])]
    if secret_env:
        raise ValueError(f"Image has secret-named environment configuration: {secret_env}")
    labels = config.get("Labels") or {}
    if reference.startswith(IMAGE_PREFIXES):
        if expected_source_sha is None or not re.fullmatch(r"[0-9a-f]{40}", expected_source_sha):
            raise ValueError(f"Expected immutable source SHA is required for {reference}")
        if reference.rsplit(":", 1)[-1] != expected_source_sha:
            raise ValueError(f"Image tag does not identify expected source for {reference}")
        if labels.get("org.opencontainers.image.revision") != expected_source_sha:
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
    if include_runtime_details:
        record["config"] = config
        record["rootfs_layers"] = ((image.get("RootFS") or {}).get("Layers") or [])
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
            lower_parts in (
                ["etc", "ssl", "cert.pem"],
                ["etc", "ssl1.1", "cert.pem"],
                ["usr", "lib", "ssl", "cert.pem"],
                ["app", ".venv", "lib", "python3.13", "site-packages", "certifi", "cacert.pem"],
                ["usr", "local", "lib", "python3.13", "site-packages", "pip", "_vendor", "certifi", "cacert.pem"],
            )
            or (len(lower_parts) == 4 and lower_parts[:3] in (["etc", "ssl", "certs"], ["usr", "lib", "ssl"]))
        )
    )
    if basename == ".env" or basename.startswith(".env.") or (
        basename.endswith(FORBIDDEN_SUFFIXES) and not public_ca_pem
    ):
        raise ValueError(f"Sensitive file is present in image archive: {name}")
    if "/run/secrets/" in f"/{'/'.join(lower_parts)}/":
        raise ValueError(f"Runtime-secret path is present in image archive: {name}")


def inspect_docker_save_archive(
    path: Path,
    expected_tags: set[str],
    expected_source_sha: str,
) -> dict[str, dict[str, Any]]:
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
        violations: set[str] = set()
        images: dict[str, dict[str, Any]] = {}
        for record in records:
            record_tags = record.get("RepoTags") or []
            observed_tags.update(record_tags)
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
            diff_ids = (config.get("rootfs") or {}).get("diff_ids") or []
            if not isinstance(diff_ids, list) or any(
                not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value)
                for value in diff_ids
            ):
                raise ValueError("Image rootfs diff IDs are missing or malformed")
            if len(record.get("Layers") or []) != len(diff_ids):
                raise ValueError("Image layer list does not match rootfs diff IDs")
            env = ((config.get("config") or {}).get("Env") or [])
            secret_env = [value.split("=", 1)[0] for value in env if SECRET_ENV.search(value.split("=", 1)[0])]
            if secret_env:
                raise ValueError(f"Secret-named runtime variables found in image config: {secret_env}")
            labels = (config.get("config") or {}).get("Labels") or {}
            for tag in record.get("RepoTags") or []:
                if tag.startswith(IMAGE_PREFIXES) and labels.get("org.opencontainers.image.revision") != expected_source_sha:
                    raise ValueError(f"Image archive revision label mismatch for {tag}")
            for index, layer_name in enumerate(record.get("Layers") or []):
                layer_digest = hashlib.sha256()
                layer_content = archive.extractfile(layer_name)
                if layer_content is None:
                    raise ValueError(f"Image layer is missing: {layer_name}")
                for block in iter(lambda: layer_content.read(1024 * 1024), b""):
                    layer_digest.update(block)
                if diff_ids[index] != "sha256:" + layer_digest.hexdigest():
                    raise ValueError("Image layer content digest does not match its rootfs DiffID")
                layer = archive.extractfile(layer_name)
                if layer is None:
                    raise ValueError(f"Image layer is missing: {layer_name}")
                with tarfile.open(fileobj=layer, mode="r|*") as layer_archive:
                    for member in layer_archive:
                        try:
                            assert_safe_member(member.name, is_directory=member.isdir())
                        except ValueError as error:
                            violations.add(str(error))
            image_data = {
                "config_digest": config_id,
                "diff_ids": diff_ids,
                "config": config.get("config") or {},
            }
            for tag in record_tags:
                if tag in images:
                    raise ValueError(f"Duplicate image tag in Docker archive: {tag}")
                images[tag] = image_data
        if violations:
            ordered = sorted(violations)
            raise ValueError(
                f"Docker archive blocked {len(ordered)} suspicious paths; "
                + "; ".join(ordered[:35])
            )
        if observed_tags != expected_tags:
            raise ValueError(f"Docker archive tags differ: expected {sorted(expected_tags)}, got {sorted(observed_tags)}")
        return images


def validate_loaded_image_identity(
    expected: dict[str, Any],
    actual: dict[str, Any],
    archived: dict[str, Any],
    roundtrip: dict[str, Any] | None = None,
) -> str:
    """Validate a loaded image across Docker's legacy and containerd stores.

    Docker Engine 29's containerd image store can expose its manifest digest as
    ``docker image inspect .Id`` while a Docker-save archive identifies the
    exact image configuration by its SHA-256. When those IDs differ, accept the
    load only if exporting the *loaded tag* recreates the same config digest
    and rootfs diff IDs as the independently verified handoff archive.
    """
    for key in ("os", "architecture", "entrypoint", "command", "labels"):
        if actual.get(key) != expected.get(key):
            raise ValueError(f"Loaded image {key} differs from the handoff manifest")
    # `docker image inspect` returns Engine-normalized Config JSON. With the
    # containerd image store, fields can be expanded/defaulted differently
    # from the original Docker-save config even when the loaded image is
    # byte-for-byte identical. Do not compare those two JSON representations.
    # For a differing Engine image ID, the caller requires a docker-save
    # roundtrip and compares its config digest below; that is the exact,
    # content-addressed configuration identity check. Entrypoint, command,
    # labels, platform, and rootfs are independently checked above/below.
    if actual.get("rootfs_layers") != archived.get("diff_ids"):
        raise ValueError("Loaded image rootfs differs from the handoff archive")
    if actual.get("image_id") == expected.get("image_id"):
        return "config-id"
    if not roundtrip:
        raise ValueError("Loaded image ID uses a different representation and no export check was provided")
    if roundtrip.get("config_digest") != expected.get("image_id"):
        raise ValueError("Loaded image export config digest differs from the handoff manifest")
    if roundtrip.get("diff_ids") != archived.get("diff_ids"):
        raise ValueError("Loaded image export rootfs differs from the handoff archive")
    return "containerd-export-equivalent"


def create_manifest(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        raise ValueError("Source must be a full immutable 40-character commit SHA")
    image_tags = args.image_tags
    expected_tags = {f"rahgard-api:{args.source_sha}", f"rahgard-web:{args.source_sha}"}
    if set(image_tags) != expected_tags:
        raise ValueError("Exactly the prepared API and Web image tags are required")
    inspect_docker_save_archive(Path(args.image_archive), expected_tags, args.source_sha)
    images = {
        "api" if tag.startswith("rahgard-api:") else "web": image_record(tag, expected_source_sha=args.source_sha)
        for tag in image_tags
    }
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
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        raise ValueError("Source must be a full immutable 40-character commit SHA")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    image_archive = Path(args.image_archive)
    if manifest.get("schema_version") != 1 or manifest.get("source", {}).get("git_sha") != args.source_sha:
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
    expected_tags = {f"rahgard-api:{args.source_sha}", f"rahgard-web:{args.source_sha}"}
    if tags != expected_tags:
        raise ValueError("Manifest does not identify the exact API/Web release tags")
    archived_images = inspect_docker_save_archive(image_archive, expected_tags, args.source_sha)
    if args.check_loaded_images:
        loaded_records: dict[str, dict[str, Any]] = {}
        mismatched_ids: list[str] = []
        for name, record in manifest["application_images"].items():
            actual = image_record(
                record["tag"], expected_source_sha=args.source_sha, include_runtime_details=True
            )
            tag = record["tag"]
            archived = archived_images.get(tag)
            if archived is None:
                raise ValueError(f"Loaded {name} image tag is absent from the verified handoff archive")
            if actual["image_id"] != record["image_id"]:
                mismatched_ids.append(tag)
            loaded_records[tag] = actual

        roundtrip_images: dict[str, dict[str, Any]] = {}
        if mismatched_ids:
            # Docker 29's containerd store may surface a manifest/index digest
            # as .Id. Export the loaded tags and verify the config bytes and
            # uncompressed layer identities against the original artifact.
            with tempfile.TemporaryDirectory(prefix="rahgard-loaded-image-verify-") as temp_dir:
                roundtrip_path = Path(temp_dir) / "loaded-images.tar"
                subprocess.run(
                    ["docker", "image", "save", "--output", str(roundtrip_path), *sorted(expected_tags)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                roundtrip_images = inspect_docker_save_archive(roundtrip_path, expected_tags, args.source_sha)

        identity_methods = []
        for name, record in manifest["application_images"].items():
            tag = record["tag"]
            identity_methods.append(
                f"{name}:{validate_loaded_image_identity(record, loaded_records[tag], archived_images[tag], roundtrip_images.get(tag))}"
            )
        loaded_ids = ",".join(
            f"{name}={loaded_records[record['tag']]['image_id']}"
            for name, record in sorted(manifest["application_images"].items())
        )
        print(f"LOADED_IMAGE_IDENTITY_PASS ids={loaded_ids} verification={','.join(identity_methods)}")
    print(f"IMAGE_BUNDLE_PASS source={args.source_sha} platform=linux/amd64 api_web_tags=exact checksums=pass secret_scan=pass")


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
