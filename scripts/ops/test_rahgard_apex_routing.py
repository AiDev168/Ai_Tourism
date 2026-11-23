"""Exercise shared-listener apex and legacy routing in isolated Docker."""

import argparse
import json
import secrets
import subprocess
import tempfile
from pathlib import Path

from rehearse_rahgard_v2_migrations import require, run

CLIENT = r"""
import socket, ssl
ctx = ssl.create_default_context(cafile="/tmp/route-test.crt")
def request(sni, host, path):
    with ctx.wrap_socket(socket.create_connection(("127.0.0.1",63202), timeout=5), server_hostname=sni) as conn:
        conn.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n").encode())
        data = b""
        while chunk := conn.recv(4096):
            data += chunk
        return data
apex = request("hinaa.ir", "hinaa.ir", "/")
assert b"200 OK" in apex and b"apex-backend" in apex
assert b"legacy-backend" in request("rahgard.hinaa.ir", "rahgard.hinaa.ir", "/")
assert b" 421 " in request("rahgard.hinaa.ir", "hinaa.ir", "/")
for path in ("/admin", "/api/v1/admin/profiles", "/api/v1/auth/local-owner", "/api/v1/auth/otp"):
    assert b" 404 " in request("hinaa.ir", "hinaa.ir", path)
"""


def fixture_command(*args: str) -> None:
    result = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Isolated fixture command failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("web_image")
    parser.add_argument("api_image")
    parser.add_argument("--openssl", default="openssl")
    args = parser.parse_args()
    label = secrets.token_hex(8)
    owned = []
    try:
        # Resolve both local images to IDs, so this rehearsal never pulls an image.
        web, api = [run("docker", "image", "inspect", "-f", "{{.Id}}", i).decode().strip()
                    for i in (args.web_image, args.api_image)]
        name = f"rahgard-apex-probe-{label}"
        owned.append(run(
            "docker", "run", "-d", "--network", "none", "--name", name, "--label", f"rahgard.apex.test={label}",
            "--entrypoint", "/bin/sh", web, "-c", "sleep 300",
        ).decode().strip())
        with tempfile.TemporaryDirectory(prefix="rahgard-apex-fixture-") as temp:
            directory = Path(temp)
            cert, key = directory / "tls.crt", directory / "tls.key"
            run(
                args.openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-subj", "/CN=hinaa.ir", "-addext", "subjectAltName=DNS:hinaa.ir,DNS:rahgard.hinaa.ir",
                "-keyout", str(key), "-out", str(cert),
            )
            apex = (Path(__file__).resolve().parents[2] / "deploy/staging/nginx-apex-v2.conf.template").read_text()
            apex = apex.replace("/etc/letsencrypt/live/hinaa.ir/fullchain.pem", "/tmp/tls.crt")
            apex = apex.replace("/etc/letsencrypt/live/hinaa.ir/privkey.pem", "/tmp/tls.key")
            conf = directory / "nginx.conf"
            conf.write_text("""
pid /tmp/nginx.pid;
error_log /tmp/nginx.log;
events {}
http {
    access_log off;
    server {
        listen 63202 ssl default_server;
        server_name rahgard.hinaa.ir;
        ssl_certificate /tmp/tls.crt;
        ssl_certificate_key /tmp/tls.key;
        location / { proxy_pass http://127.0.0.1:18080; }
    }
    server { listen 127.0.0.1:18080; return 200 "legacy-backend"; }
    server { listen 127.0.0.1:18081; return 200 "apex-backend"; }
""" + apex + "\n}\n", encoding="utf-8")
            for path in (cert, key, conf):
                run("docker", "cp", str(path), f"{name}:/tmp/{path.name}")
            fixture_command("docker", "exec", name, "nginx", "-t", "-c", "/tmp/nginx.conf")
            fixture_command("docker", "exec", name, "nginx", "-c", "/tmp/nginx.conf")

            client = f"rahgard-apex-client-{label}"
            owned.append(run(
                "docker", "run", "-d", "--network", f"container:{owned[0]}", "--name", client,
                "--label", f"rahgard.apex.test={label}", "--entrypoint", "/bin/sh", api, "-c", "sleep 300",
            ).decode().strip())
            run("docker", "cp", str(cert), f"{client}:/tmp/route-test.crt")
            fixture_command("docker", "exec", client, "python", "-I", "-c", CLIENT)
            print("APEX_ROUTE_PASS isolated_tls=verified apex=200 legacy=200 mismatched_sni=421 admin_otp=404")
    finally:
        for container in reversed(owned):
            state = json.loads(run("docker", "inspect", container))[0]
            require(state["Config"]["Labels"].get("rahgard.apex.test") == label, "Route cleanup identity mismatch")
            run("docker", "rm", "-f", container)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"BLOCKED: {error}") from None
