from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_web_runtime_image_normalizes_copied_public_file_and_directory_modes() -> None:
    dockerfile = (ROOT / "deploy/staging/Dockerfile.web").read_text(encoding="utf-8")

    assert "find /usr/share/nginx/html -type d -exec chmod 0755 {} +" in dockerfile
    assert "find /usr/share/nginx/html -type f -exec chmod 0644 {} +" in dockerfile
    assert "rahgard-static-before.sha256" in dockerfile
    assert "rahgard-static-after.sha256" in dockerfile
    assert "cmp -s /tmp/rahgard-static-before.sha256 /tmp/rahgard-static-after.sha256" in dockerfile
    assert "test -r /usr/share/nginx/html/manifest.webmanifest" in dockerfile
    assert "test -r /usr/share/nginx/html/sw.js" in dockerfile


def test_web_pwa_gate_checks_unprivileged_nginx_read_and_all_essential_responses() -> None:
    gate = (ROOT / "scripts/ops/test_rahgard_web_image_pwa.sh").read_text(encoding="utf-8")

    assert "--user nginx" in gate
    assert "user[[:space:]]+nginx;" in gate
    assert "manifest.webmanifest" in gate
    assert "sw.js" in gate
    assert "hashed JS and CSS assets" in gate
    assert "wrong content type" in gate
    assert "missing_asset=404" in gate
    assert "--network none" in gate
    assert "--add-host api:127.0.0.1" in gate
    assert "PortBindings" not in gate


def test_live_release_gate_checks_pwa_before_marker_or_symlink_switch() -> None:
    deploy = (ROOT / "deploy/staging/deploy.sh").read_text(encoding="utf-8")

    pwa_check = deploy.index("test_rahgard_web_image_pwa.sh")
    marker_change = deploy.index("set_release_sha \"$sha\"", pwa_check)
    symlink_switch = deploy.index('mv -Tf "$next" "$root/current"', pwa_check)
    rollback_trap = deploy.index("trap rollback EXIT", pwa_check)
    assert pwa_check < marker_change < symlink_switch < rollback_trap
    assert "Release is missing the mandatory PWA image acceptance gate" in deploy


def test_current_schema_rehearsal_never_applies_migrations() -> None:
    rehearsal = (ROOT / "deploy/staging/rehearse-20-20.sh").read_text(encoding="utf-8")

    assert "expected_migrations=20" in rehearsal
    assert "migrations_applied=0" in rehearsal
    assert "INSERT INTO system.schema_migrations" not in rehearsal
    assert "0018_national_catalogue_ingestion" in rehearsal
    assert "0021_postgis_security_definer_publication" in rehearsal
    assert 'crlf_hash=$(python3 - "$migration_file"' in rehearsal
    assert "20-entry restore has wrong migration content checksum:" in rehearsal
    assert 'not h.get("Mounts",[])' in rehearsal
    assert 'all(m["Type"]=="tmpfs" for m in c.get("Mounts",[]))' in rehearsal
    assert '"/var/lib/postgresql/data" in h["Tmpfs"]' in rehearsal
    assert 'bash "$release_dir/scripts/ops/test_rahgard_web_image_pwa.sh"' in rehearsal


def test_hosted_build_is_parameterized_and_artifact_uses_exact_source_sha() -> None:
    builder = (ROOT / "scripts/ops/build_rahgard_release_images.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/rahgard-release-image-build.yml").read_text(encoding="utf-8")

    assert "readonly expected_sha" not in builder
    assert '[[ "$release_sha" =~ ^[0-9a-f]{40}$ ]]' in builder
    assert "${{ inputs.source_sha }}" in workflow
    assert "rahgard-release-images-${{ inputs.source_sha }}-linux-amd64" in workflow
