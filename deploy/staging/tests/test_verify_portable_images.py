from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "verify-portable-images.py"
SPEC = importlib.util.spec_from_file_location("verify_portable_images", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
verify = MODULE.verify


SHA = "a" * 40


def create_bundle(root: Path, *, bad_revision: bool = False) -> tuple[Path, Path]:
    configs = []
    identities = []
    for kind, tag in (("api", f"rahgard-api:{SHA}"), ("web", f"rahgard-web:{SHA}"),
                      ("postgres", "rahgard-postgres:17-postgis36-vector087")):
        config = json.dumps({
            "architecture": "amd64", "os": "linux",
            "config": {"Labels": ({"org.opencontainers.image.revision": "b" * 40 if bad_revision else SHA,
                                     "org.opencontainers.image.title": kind}
                                     if kind != "postgres" else {})},
        }, separators=(",", ":")).encode()
        config_name = hashlib.sha256(config).hexdigest() + ".json"
        configs.append((tag, config_name, config))
        revision = "external-db-image" if kind == "postgres" else SHA
        identities.append(f"{tag}|sha256:{hashlib.sha256(config).hexdigest()}|linux|amd64|{revision}")
    archive_path = root / "images.tar"
    with tarfile.open(archive_path, "w") as archive:
        manifest = []
        for tag, config_name, config in configs:
            import io
            info = tarfile.TarInfo(config_name)
            info.size = len(config)
            archive.addfile(info, io.BytesIO(config))
            manifest.append({"Config": config_name, "RepoTags": [tag], "Layers": []})
        payload = json.dumps(manifest).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(payload)
        archive.addfile(info, __import__("io").BytesIO(payload))
    identities_path = root / "identities.tsv"
    identities_path.write_text("\n".join(identities) + "\n", encoding="ascii")
    return archive_path, identities_path


class PortableImageBundleTests(unittest.TestCase):
    def test_accepts_exact_api_and_web_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            image, identities = create_bundle(Path(directory))
            self.assertEqual(len(verify(image, identities, SHA)), 3)

    def test_rejects_image_from_other_source_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            image, identities = create_bundle(Path(directory), bad_revision=True)
            with self.assertRaisesRegex(ValueError, "identity_mismatch"):
                verify(image, identities, SHA)

    def test_rejects_symlink_or_special_archive_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            image, identities = create_bundle(Path(directory))
            with tarfile.open(image, "a") as archive:
                info = tarfile.TarInfo("escape")
                info.type = tarfile.SYMTYPE
                info.linkname = "../outside"
                archive.addfile(info)
            with self.assertRaisesRegex(ValueError, "unsafe_or_duplicate"):
                verify(image, identities, SHA)


if __name__ == "__main__":
    unittest.main()
