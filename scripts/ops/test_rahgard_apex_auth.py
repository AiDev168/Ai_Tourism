"""Test exact apex HTTPS staging auth using isolated API/Web and restored PG17."""

import hashlib
import json
import re
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

CLIENT = r'''
import http.client, json, os, re, socket, ssl, sys
mode, legacy_password, token = sys.argv[1:]
apex = "https://hinaa.ir"
legacy = "https://rahgard.hinaa.ir"
ctx = ssl.create_default_context(cafile="/tmp/fixture.crt")
tag = os.environ["FIXTURE_LABEL"]
legacy_email = f"v2-{tag}-legacy@example.test"
legacy_payload = {"email": legacy_email, "password": legacy_password}

def exchange(path, body=None, origin=apex, cookie=None, csrf=None, scheme="https"):
    headers = {"Origin": origin}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    if scheme == "https":
        conn = http.client.HTTPSConnection("hinaa.ir", context=ctx, timeout=10)
        conn._create_connection = lambda *_args, **_kwargs: socket.create_connection(("127.0.0.1",443), timeout=10)
    else:
        conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=10)
        headers.update({"Host": origin.removeprefix("https://"), "X-Forwarded-Proto": "https"})
    conn.request("GET" if body is None else "POST", path, json.dumps(body) if body is not None else None, headers)
    response = conn.getresponse()
    raw = response.read()
    content_type = response.getheader("Content-Type", "")
    result = (response.status, response.getheader("Set-Cookie", ""),
              json.loads(raw) if raw and "application/json" in content_type else raw)
    conn.close()
    return result

def password(length):
    return "ژ" * length

def status(action, payload, **kwargs):
    return exchange("/api/v1/auth/staging/" + action, payload, **kwargs)[0]

if mode == "legacy":
    assert status("login", legacy_payload, origin=apex, scheme="http") == 401, "legacy_apex_login"
    assert status("register", legacy_payload, origin=apex, scheme="http") == 401, "legacy_apex_register"
    assert status("register", legacy_payload, origin=legacy, scheme="http") == 200, "legacy_fixture_create"
    old_short = status("register", {"email": f"v2-{tag}-old-short@example.test", "password": password(8)},
                       origin=legacy, scheme="http")
    assert old_short == 422, "legacy_8_char_policy"
    old_fifteen = status("register", {"email": f"v2-{tag}-old-short@example.test", "password": password(15)},
                        origin=legacy, scheme="http")
    assert old_fifteen == 422, "legacy_15_char_policy"
    print(json.dumps({"legacy_apex_login":401, "legacy_apex_register":401,
                      "legacy_8_char_registration":old_short, "legacy_15_char_registration":old_fifteen,
                      "legacy_16_char_registration":200}))
else:
    root_status, _, html = exchange("/")
    assert root_status == 200 and isinstance(html, bytes), "apex_root"
    # HTML paths are relative to this exact HTTPS origin.
    assets = re.findall(rb'["\'](/assets/[A-Za-z0-9_-]+\.(?:js|css))["\']', html)
    assert len(assets) >= 2, "apex_hashed_assets"
    assert all(exchange(asset.decode())[0] == 200 for asset in assets), "apex_static_assets"
    assert exchange("/manifest.webmanifest")[0] == exchange("/sw.js")[0] == 200, "apex_pwa_routes"
    assert exchange("/assets/absent-release-fixture.js")[0] == 404, "apex_missing_asset"
    methods = exchange("/api/v1/auth/method")[2]
    assert methods["otp_delivery"] == "unavailable" and "staging_invite" in methods["methods"]
    assert methods["staging_email_signup"] is (mode == "signup")
    accepted, cookie, reply = exchange("/api/v1/auth/staging/login", legacy_payload)
    assert accepted == 200, "legacy_credential_on_candidate"
    assert cookie.startswith("__Host-rahgard_session="), "host_prefix"
    lower = cookie.lower()
    assert "secure" in lower and "httponly" in lower and "path=/" in lower and "domain=" not in lower, "cookie_attributes"
    csrf = reply["csrf_token"]
    cookie = cookie.split(";",1)[0]
    assert exchange("/api/v1/auth/me", cookie=cookie)[0] == 200, "authenticated_me"
    assert status("login", legacy_payload, origin=legacy) == 401, "candidate_legacy_origin"
    assert exchange("/api/v1/auth/logout", {}, cookie=cookie)[0] == 403, "missing_csrf"
    assert exchange("/api/v1/auth/logout", {}, cookie=cookie, csrf=csrf)[0] == 204, "valid_csrf"
    assert exchange("/api/v1/auth/me", cookie=cookie)[0] == 401, "logout_revokes"
    results = {"email_signup": methods["staging_email_signup"], "otp_delivery": methods["otp_delivery"],
               "existing_legacy_credential": "pass", "secure_host_only_cookie": "pass",
               "csrf_and_logout": "pass", "apex_root_and_pwa_assets": "pass"}
    if mode == "invite":
        payload = {"email": f"v2-{tag}-invite@example.test", "password": password(8)}
        assert status("register", payload) == 401, "invite_only_registration_disabled"
        assert status("redeem", {**payload, "invite_code": token}) == 200, "invited_eight_chars"
        assert status("login", payload) == 200, "invited_credential_login"
        results.update({"uninvited_registration": 401, "invited_8_char_registration": 200})
    else:
        results["registration_boundary_status"] = {}
        for length, expected in ((7,422),(8,200),(24,200),(25,200),(256,200),(257,422)):
            payload = {"email": f"v2-{tag}-{length}@example.test", "password": password(length)}
            assert status("register", payload) == expected, f"candidate_password_boundary_{length}"
            if expected == 200:
                assert status("login", payload) == 200, f"candidate_password_login_{length}"
            results["registration_boundary_status"][length] = expected
        results["supplementary_unicode_boundary_status"] = {}
        for length, expected in ((7,422),(8,200),(256,200),(257,422)):
            payload = {"email": f"v2-{tag}-unicode-{length}@example.test", "password": chr(0x1F33F) * length}
            assert status("register", payload) == expected, f"candidate_unicode_boundary_{length}"
            if expected == 200:
                assert status("login", payload) == 200, f"candidate_unicode_login_{length}"
            results["supplementary_unicode_boundary_status"][length] = expected
    print(json.dumps(results))
'''


def test_apex_auth(db: str, legacy_image: str, api_image: str, web_image: str, openssl: str) -> dict:
    from rehearse_rahgard_v2_migrations import DATABASE, require, run, sql

    state = json.loads(run("docker", "inspect", db))[0]
    label = (state["Config"].get("Labels") or {}).get("rahgard.v2.restore", "")
    host_config = state["HostConfig"]
    require(
        re.fullmatch(r"[0-9a-f]{20}", label) is not None
        and state["Name"] == f"/rahgard-v2-restore-{label}"
        and host_config["NetworkMode"] == "none"
        and not host_config["PortBindings"] and not host_config.get("Binds") and not host_config.get("Mounts")
        and "/var/lib/postgresql/data" in host_config["Tmpfs"],
        "Refusing fixture creation outside an isolated Rahgard restore container",
    )
    tag = secrets.token_hex(6)
    password = secrets.token_hex(8)
    invitation = secrets.token_urlsafe(36)
    invite_digest = hashlib.sha256(invitation.encode()).hexdigest()
    sql(
        db,
        "INSERT INTO identity.staging_invites(token_digest, created_at, expires_at)"
        f" VALUES (decode('{invite_digest}', 'hex'), now(), now()+interval '1 hour');",
    )
    owned = []

    def start(image: str, role: str, *args: str) -> str:
        image_id = run("docker", "image", "inspect", "-f", "{{.Id}}", image).decode().strip()
        name = run(
            "docker", "run", "-d", "--network", f"container:{db}", "--name", f"rahgard-apex-{role}-{tag}",
            "--label", f"rahgard.apex.auth-test={tag}", "--entrypoint", args[0], *args[1:], image_id,
            *(("-c", "sleep 240") if role == "web"
              else ("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")),
        ).decode().strip()
        owned.append(name)
        return name

    def stop(container: str) -> None:
        actual = json.loads(run("docker", "inspect", container))[0]
        require(actual["Config"]["Labels"].get("rahgard.apex.auth-test") == tag, "Fixture cleanup identity mismatch")
        run("docker", "rm", "-f", container)
        owned.remove(container)

    common = {
        "APP_ENV": "staging", "LOG_LEVEL": "WARNING", "DATABASE_HOST": "127.0.0.1", "DATABASE_PORT": "5432",
        "DATABASE_NAME": DATABASE, "DATABASE_USER": "ai_tourism_app", "DATABASE_PASSWORD": tag,
        "AUTH_ENABLED": "true", "AUTH_LOCAL_OWNER_ENABLED": "false", "STAGING_AUTH_ENABLED": "true",
        "AUTH_COOKIE_SECURE": "true", "AUTH_SMS_ADAPTER": "disabled",
        "INTERNAL_CHAT_ENABLED": "false", "TOURISM_RAG_ENABLED": "false", "AI_PROVIDER_ADMIN_ENABLED": "false",
        "AUTH_SESSION_IDLE_SECONDS": "1800", "AUTH_SESSION_ABSOLUTE_SECONDS": "43200",
        "STAGING_EMAIL_SIGNUP_IP_LIMIT": "20", "STAGING_EMAIL_SIGNUP_ACCOUNT_LIMIT": "50",
        "AUTH_TRUSTED_PROXY_CIDRS": "127.0.0.1/32",
        "FIXTURE_LABEL": tag,
    }
    common.update({key: secrets.token_hex(32) for key in (
        "AUTH_OTP_HMAC_SECRET", "AUTH_CSRF_SECRET", "AUTH_RATE_LIMIT_SECRET",
    )})
    results = {}
    try:
        with tempfile.TemporaryDirectory(prefix="rahgard-v2-apex-cert-") as tmp:
            root = Path(tmp)
            key, cert = root / "fixture.key", root / "fixture.crt"
            run(
                openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=hinaa.ir",
                "-addext", "subjectAltName=DNS:hinaa.ir", "-keyout", str(key), "-out", str(cert),
            )
            conf = root / "apex.conf"
            template = (Path(__file__).resolve().parents[2] / "deploy/staging/nginx-apex-v2.conf.template").read_text()
            conf.write_text(template.replace("63202", "443").replace("18081", "8080")
                            .replace("/etc/letsencrypt/live/hinaa.ir/fullchain.pem", "/tmp/fixture.crt")
                            .replace("/etc/letsencrypt/live/hinaa.ir/privkey.pem", "/tmp/fixture.key"), encoding="utf-8")
            web = start(web_image, "web", "/bin/sh")
            # Docker's isolated container has no dependency DNS. Its test-only
            # upstream alias is in the DB container's shared hosts file.
            for path in (key, cert, conf):
                run("docker", "cp", str(path), f"{web}:/tmp/{path.name}")
            run("docker", "exec", web, "sh", "-ec", "cp /tmp/apex.conf /etc/nginx/conf.d/apex.conf; nginx -t; nginx")
            for mode, host, image, signup in (
                ("legacy", "rahgard.hinaa.ir", legacy_image, True),
                ("invite", "hinaa.ir", api_image, False),
                ("signup", "hinaa.ir", api_image, True),
            ):
                env = {**common, "STAGING_PUBLIC_HOST": host, "AUTH_ALLOWED_ORIGINS": "https://" + host,
                       "STAGING_EMAIL_SIGNUP_ENABLED": str(signup).lower(), "AUTH_RATE_LIMIT_SECRET": secrets.token_hex(32)}
                flags = [item for key_name, value in env.items() for item in ("-e", f"{key_name}={value}")]
                api = start(image, mode, "python", *flags)
                probe = ("import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)")
                for _ in range(24):
                    try:
                        run("docker", "exec", api, "python", "-c", probe)
                    except RuntimeError:
                        time.sleep(0.5)
                    else:
                        break
                else:
                    raise RuntimeError(f"Isolated API failed readiness for {mode}")
                run("docker", "cp", str(cert), f"{api}:/tmp/fixture.crt")
                checked = subprocess.run(
                    ["docker", "exec", api, "python", "-I", "-c", CLIENT, mode, password, invitation],
                    capture_output=True, timeout=50, check=False,
                )
                if checked.returncode:
                    # Traceback messages are fixed assertion labels. Suppress
                    # provider/HTTP response bodies and all request values.
                    last = checked.stderr.decode(errors="replace").splitlines()[-1:]
                    reason = last[0].split(": ", 1)[-1] if last and last[0].startswith("AssertionError: ") else "transport"
                    raise RuntimeError(f"Isolated apex auth fixture failed in {mode}: {reason}")
                results[mode] = json.loads(checked.stdout)
                stop(api)
        return results
    finally:
        for item in reversed(owned.copy()):
            stop(item)
