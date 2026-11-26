from pathlib import Path

import pytest

from scripts.ops.prepare_rahgard_restore_web_config import prepare


def test_restore_web_config_rewrites_only_the_compose_api_upstream(tmp_path: Path) -> None:
    source = tmp_path / "nginx.conf"
    target = tmp_path / "restore.conf"
    source.write_text(
        "server {\n location ^~ /api/ {\n"
        "  proxy_pass http://api:8000;\n }\n}\n",
        encoding="utf-8",
    )

    prepare(source, target)

    assert "proxy_pass http://127.0.0.1:8000;" in target.read_text(encoding="utf-8")
    assert "proxy_pass http://api:8000;" not in target.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "content",
    [
        "server { location /api/ { proxy_pass http://api:8000; proxy_pass http://other; } }",
        "server { location /api/ { proxy_pass http://unexpected:8000; } }",
        "server { location /api/ { proxy_pass http://api:8000; }\n"
        "location /other/ { proxy_pass http://api:8000; } }",
    ],
)
def test_restore_web_config_fails_closed_on_proxy_drift(tmp_path: Path, content: str) -> None:
    source = tmp_path / "nginx.conf"
    target = tmp_path / "restore.conf"
    source.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="web_proxy_upstream_contract_mismatch"):
        prepare(source, target)

    assert not target.exists()


def test_restore_web_config_does_not_overwrite_existing_target(tmp_path: Path) -> None:
    source = tmp_path / "nginx.conf"
    target = tmp_path / "restore.conf"
    source.write_text("location / {\n proxy_pass http://api:8000;\n}\n", encoding="utf-8")
    target.write_text("preserve", encoding="utf-8")

    with pytest.raises(ValueError, match="web_config_destination_exists"):
        prepare(source, target)

    assert target.read_text(encoding="utf-8") == "preserve"
