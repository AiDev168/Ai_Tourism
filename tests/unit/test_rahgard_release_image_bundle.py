from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tarfile
from argparse import Namespace
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "verify_rahgard_release_image_bundle.py"
SPEC = importlib.util.spec_from_file_location("rahgard_image_bundle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
TEST_SHA = "a" * 40


def _add_file(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    item = tarfile.TarInfo(name)
    item.size = len(data)
    archive.addfile(item, io.BytesIO(data))


def _make_docker_archive(path: Path, *, secret_file: bool = False, layer_digest_mismatch: bool = False) -> set[str]:
    tags = {
        f"rahgard-api:{TEST_SHA}",
        f"rahgard-web:{TEST_SHA}",
    }
    records = []
    with tarfile.open(path, "w") as outer:
        for index, tag in enumerate(sorted(tags)):
            labels = {"org.opencontainers.image.revision": TEST_SHA}
            layer_buffer = io.BytesIO()
            with tarfile.open(fileobj=layer_buffer, mode="w") as layer:
                _add_file(layer, ".env" if secret_file and index == 0 else "app/marker.txt", b"test-only")
            layer_bytes = layer_buffer.getvalue()
            config = {
                "config": {"Env": ["PATH=/usr/bin"], "Labels": labels},
                "rootfs": {"type": "layers", "diff_ids": ["sha256:" + hashlib.sha256(layer_bytes).hexdigest()]},
            }
            config_bytes = json.dumps(config, separators=(",", ":")).encode()
            config_name = hashlib.sha256(config_bytes).hexdigest() + ".json"
            _add_file(outer, config_name, config_bytes)
            layer_name = f"{index}/layer.tar"
            _add_file(outer, layer_name, layer_bytes + (b"changed" if layer_digest_mismatch else b""))
            records.append({"Config": config_name, "RepoTags": [tag], "Layers": [layer_name]})
        _add_file(outer, "manifest.json", json.dumps(records).encode())
    return tags


def _fixture_bundle(tmp_path: Path, *, secret_file: bool = False) -> tuple[Path, Path, Path, set[str]]:
    source = tmp_path / f"rahgard-source-{TEST_SHA}.tar"
    source.write_bytes(b"immutable git archive test fixture")
    images = tmp_path / "rahgard-images-linux-amd64.tar"
    tags = _make_docker_archive(images, secret_file=secret_file)
    manifest_path = tmp_path / "release-manifest.json"
    manifest = {
        "schema_version": 1,
        "source": {
            "git_sha": TEST_SHA,
            "git_archive": source.name,
            "git_archive_sha256": MODULE.sha256_file(source),
        },
        "platform": "linux/amd64",
        "application_images": {str(i): {"tag": tag} for i, tag in enumerate(sorted(tags))},
        "docker_archive": {
            "file": images.name,
            "sha256": MODULE.sha256_file(images),
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return source, images, manifest_path, tags


def _verify_args(source: Path, images: Path, manifest: Path) -> Namespace:
    return Namespace(
        source_sha=TEST_SHA,
        source_archive=str(source),
        image_archive=str(images),
        manifest=str(manifest),
        check_loaded_images=False,
    )


def test_valid_exact_source_and_two_image_bundle_passes(tmp_path: Path) -> None:
    source, images, manifest, tags = _fixture_bundle(tmp_path)
    MODULE.verify(_verify_args(source, images, manifest))
    assert len(tags) == 2


def test_bundle_verifier_accepts_arbitrary_full_immutable_source_sha(tmp_path: Path) -> None:
    source, images, manifest, _ = _fixture_bundle(tmp_path)
    assert json.loads(manifest.read_text(encoding="utf-8"))["source"]["git_sha"] == TEST_SHA
    MODULE.verify(_verify_args(source, images, manifest))


def test_bundle_verifier_rejects_non_full_source_sha(tmp_path: Path) -> None:
    source, images, manifest, _ = _fixture_bundle(tmp_path)
    args = _verify_args(source, images, manifest)
    args.source_sha = TEST_SHA[:-1]
    with pytest.raises(ValueError, match="full immutable"):
        MODULE.verify(args)


def test_image_archive_with_secret_file_is_rejected(tmp_path: Path) -> None:
    source, images, manifest, _ = _fixture_bundle(tmp_path, secret_file=True)
    with pytest.raises(ValueError, match="Sensitive file"):
        MODULE.verify(_verify_args(source, images, manifest))


def test_layer_content_must_match_configured_rootfs_diff_id(tmp_path: Path) -> None:
    source = tmp_path / f"rahgard-source-{TEST_SHA}.tar"
    source.write_bytes(b"immutable git archive test fixture")
    images = tmp_path / "rahgard-images-linux-amd64.tar"
    tags = _make_docker_archive(images, layer_digest_mismatch=True)
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": {
                    "git_sha": TEST_SHA,
                    "git_archive": source.name,
                    "git_archive_sha256": MODULE.sha256_file(source),
                },
                "platform": "linux/amd64",
                "application_images": {str(i): {"tag": tag} for i, tag in enumerate(sorted(tags))},
                "docker_archive": {"file": images.name, "sha256": MODULE.sha256_file(images)},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="layer content digest"):
        MODULE.verify(_verify_args(source, images, manifest_path))


def test_tampered_source_archive_is_rejected(tmp_path: Path) -> None:
    source, images, manifest, _ = _fixture_bundle(tmp_path)
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum or filename mismatch"):
        MODULE.verify(_verify_args(source, images, manifest))


def test_wrong_archived_release_tags_are_rejected(tmp_path: Path) -> None:
    source, images, manifest, _ = _fixture_bundle(tmp_path)
    with tarfile.open(images, "r:") as archive:
        records = json.load(archive.extractfile("manifest.json"))
    records[0]["RepoTags"] = ["rahgard-api:wrong"]
    with tarfile.open(images, "w") as archive:
        for name, data in ((records[0]["Config"], b"{}"),):
            _add_file(archive, name, data)
        _add_file(archive, "manifest.json", json.dumps(records).encode())
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["docker_archive"]["sha256"] = MODULE.sha256_file(images)
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    with pytest.raises((ValueError, KeyError, tarfile.TarError)):
        MODULE.verify(_verify_args(source, images, manifest))


def test_containerd_manifest_id_alias_requires_exact_exported_config_and_layers() -> None:
    config_id = "sha256:" + "a" * 64
    diff_ids = ["sha256:" + "b" * 64]
    expected = {
        "image_id": config_id,
        "os": "linux",
        "architecture": "amd64",
        "entrypoint": ["/entrypoint"],
        "command": ["app"],
        "labels": {"org.opencontainers.image.revision": TEST_SHA},
    }
    actual = {
        **expected,
        "image_id": "sha256:" + "c" * 64,
        "rootfs_layers": diff_ids,
    }
    archived = {"config_digest": config_id, "diff_ids": diff_ids}

    assert MODULE.validate_loaded_image_identity(expected, actual, archived, archived) == "containerd-export-equivalent"


def test_containerd_manifest_id_alias_rejects_changed_exported_config() -> None:
    expected = {
        "image_id": "sha256:" + "a" * 64,
        "os": "linux",
        "architecture": "amd64",
        "entrypoint": ["/entrypoint"],
        "command": ["app"],
        "labels": {"org.opencontainers.image.revision": TEST_SHA},
    }
    actual = {**expected, "image_id": "sha256:" + "c" * 64, "rootfs_layers": ["sha256:" + "b" * 64]}
    archived = {"config_digest": expected["image_id"], "diff_ids": ["sha256:" + "b" * 64]}
    changed_roundtrip = {**archived, "config_digest": "sha256:" + "d" * 64}

    with pytest.raises(ValueError, match="export config digest"):
        MODULE.validate_loaded_image_identity(expected, actual, archived, changed_roundtrip)


def test_loaded_image_must_retain_handoff_rootfs() -> None:
    expected = {
        "image_id": "sha256:" + "a" * 64,
        "os": "linux",
        "architecture": "amd64",
        "entrypoint": ["/entrypoint"],
        "command": ["app"],
        "labels": {"org.opencontainers.image.revision": TEST_SHA},
    }
    actual = {**expected, "rootfs_layers": ["sha256:" + "c" * 64]}
    archived = {"config_digest": expected["image_id"], "diff_ids": ["sha256:" + "b" * 64]}

    with pytest.raises(ValueError, match="rootfs differs"):
        MODULE.validate_loaded_image_identity(expected, actual, archived)


def test_runtime_identity_details_do_not_expand_public_manifest_records(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        MODULE,
        "docker_inspect",
        lambda _reference: {
            "Id": "sha256:" + "a" * 64,
            "Os": "linux",
            "Architecture": "amd64",
            "Config": {"Env": ["PATH=/usr/bin"], "Entrypoint": ["/entrypoint"], "Cmd": ["app"], "Labels": {}},
            "RootFS": {"Layers": ["sha256:" + "b" * 64]},
        },
    )

    manifest_record = MODULE.image_record("example/base:tag")
    runtime_record = MODULE.image_record("example/base:tag", include_runtime_details=True)

    assert "config" not in manifest_record
    assert "rootfs_layers" not in manifest_record
    assert runtime_record["config"]["Cmd"] == ["app"]
    assert runtime_record["rootfs_layers"] == ["sha256:" + "b" * 64]
