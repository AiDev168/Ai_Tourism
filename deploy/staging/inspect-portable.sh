#!/usr/bin/env bash
# Authenticates and safely extracts into a new private directory only.
set -Eeuo pipefail
umask 077
bundle="${1:-}"
passphrase_file="${2:-}"
hmac_key_file="${3:-}"
destination="${4:-}"
[[ -f "$bundle" && ! -L "$bundle" && -f "$bundle.hmac" && ! -L "$bundle.hmac" \
   && -f "$bundle.sha256" && ! -L "$bundle.sha256" \
   && -f "$passphrase_file" && ! -L "$passphrase_file" && -s "$passphrase_file" \
   && -f "$hmac_key_file" && ! -L "$hmac_key_file" && -s "$hmac_key_file" \
   && -n "$destination" ]] || {
  echo 'Usage: inspect-portable.sh <bundle.tar.enc> <passphrase-file> <independent-hmac-key-file> <new-private-directory>' >&2
  exit 2
}
bundle=$(realpath -e -- "$bundle")
passphrase_file=$(realpath -e -- "$passphrase_file")
hmac_key_file=$(realpath -e -- "$hmac_key_file")
parent=$(realpath -e -- "$(dirname -- "$destination")")
leaf=$(basename -- "$destination")
[[ "$leaf" != . && "$leaf" != / && "$leaf" != *$'\n'* ]] || { echo 'Invalid destination name.' >&2; exit 2; }
destination="$parent/$leaf"
[[ ! -e "$destination" ]] || { echo 'Destination already exists; refusing to overwrite.' >&2; exit 2; }
[[ $(wc -c < "$hmac_key_file") -ge 32 ]] || { echo 'HMAC key must contain at least 32 random bytes.' >&2; exit 2; }

# Verify the trusted keyed MAC before decrypting any bytes. The SHA sidecar is
# retained only as a transfer-corruption check, never as authenticity proof.
(
  cd -- "$(dirname -- "$bundle")"
  sha256sum --check -- "$(basename -- "$bundle").sha256"
)
python3 - "$hmac_key_file" "$bundle" "$bundle.hmac" <<'PY'
import hashlib, hmac, os, re, sys
key_path, bundle_path, mac_path = sys.argv[1:]
with open(key_path, "rb") as f:
    key = f.read()
with open(mac_path, "r", encoding="ascii") as f:
    line = f.read(257)
if len(line) > 256:
    raise SystemExit("HMAC sidecar is too large.")
m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)\n", line)
if not m or m.group(2) != os.path.basename(bundle_path):
    raise SystemExit("Invalid HMAC sidecar format/name.")
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(bundle_path, "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        mac.update(block)
if not hmac.compare_digest(mac.hexdigest(), m.group(1)):
    raise SystemExit("Portable bundle authentication failed; refusing decryption.")
PY

work=$(mktemp -d "$parent/.rahgard-inspect.XXXXXX")
chmod 0700 "$work"
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT
mkdir -m 0700 "$work/extracted"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -pass file:"$passphrase_file" -in "$bundle" -out "$work/payload.tar"
python3 - "$work/payload.tar" "$work/extracted" <<'PY'
import hashlib, os, re, sys, tarfile
archive_path, root = sys.argv[1:]
allowed_secrets = {
    "pg_owner_password", "app_db_password", "geo_authorizer_password",
    "geo_publisher_password", "auth_otp_hmac_secret", "auth_csrf_secret",
    "auth_rate_limit_secret", "internal_chat_token", "sms_ir_production_api_key",
    "platform_admin_mfa_encryption_key_hex", "platform_admin_recovery_pepper",
}

def safe_name(name):
    if not name or "\\" in name or "\x00" in name or name.startswith("/"):
        return False
    parts = name.rstrip("/").split("/")
    return bool(parts) and all(p not in ("", ".", "..") for p in parts)

def allowed(name, is_dir):
    n = name.rstrip("/")
    if n in {"private", "private/secrets", "private/state", "private/provider-keyring", "release"}:
        return is_dir
    if n in {"MANIFEST.sha256", "database.dump", "database.migration-ledger.tsv", "database.critical-counts.tsv", "runtime-images.tar", "runtime-image-identities.tsv", "private/host.env", "private/state/WRITE_FREEZE", "private/state/platform-mfa-status", "private/state/provider-admin-status", "private/provider-vault.tar", "private/provider-keyring/ai_provider_vault_keyring.json", "release/RELEASE_COMMIT"}:
        return not is_dir
    if n.startswith("private/secrets/"):
        return not is_dir and n.removeprefix("private/secrets/") in allowed_secrets
    if n.startswith("private/state/") or n.startswith("release/"):
        return not is_dir or is_dir
    return False

with tarfile.open(archive_path, mode="r:") as tf:
    members = tf.getmembers()
    seen = set()
    regular = {}
    dirs = set()
    for m in members:
        raw_name = m.name
        if not safe_name(raw_name):
            raise SystemExit("Unsafe, duplicate, or non-canonical archive member path.")
        if m.isdir():
            name = raw_name.rstrip("/")
        else:
            if raw_name.endswith("/"):
                raise SystemExit("Regular file has a directory-form archive path.")
            name = raw_name
        if not name or name in seen:
            raise SystemExit("Unsafe, duplicate, or non-canonical archive member path.")
        seen.add(name)
        is_dir = m.isdir()
        if not (is_dir or m.isreg()) or m.issym() or m.islnk() or m.mode & 0o6000:
            raise SystemExit("Archive contains a link, special file, or privileged mode.")
        if not allowed(name, is_dir):
            raise SystemExit("Archive contains an unexpected member.")
        if is_dir:
            dirs.add(name.rstrip("/"))
        else:
            regular[name] = m
    required = {"MANIFEST.sha256", "database.dump", "database.migration-ledger.tsv", "database.critical-counts.tsv", "runtime-images.tar", "runtime-image-identities.tsv", "private/host.env", "private/state/WRITE_FREEZE", "private/state/platform-mfa-status", "private/state/provider-admin-status", "release/RELEASE_COMMIT"}
    required_secrets = {
        "pg_owner_password", "app_db_password", "geo_authorizer_password",
        "geo_publisher_password", "auth_otp_hmac_secret", "auth_csrf_secret",
        "auth_rate_limit_secret", "internal_chat_token", "sms_ir_production_api_key",
    }
    if not required.issubset(regular):
        raise SystemExit("Archive is missing required portability files.")
    bundled_secrets = {n.removeprefix("private/secrets/") for n in regular if n.startswith("private/secrets/")}
    mfa_secrets = {"platform_admin_mfa_encryption_key_hex", "platform_admin_recovery_pepper"}
    if bundled_secrets not in (required_secrets, required_secrets | mfa_secrets):
        raise SystemExit("Runtime secret allowlist mismatch.")
    with open(os.path.join(root, "private/state/platform-mfa-status"), encoding="ascii") as f:
        mfa_status = f.read().strip()
    if mfa_status not in {"mfa_enabled", "mfa_disabled"} or (mfa_status == "mfa_enabled") != (bundled_secrets == (required_secrets | mfa_secrets)):
        raise SystemExit("Portable MFA state and protected file allowlist disagree.")
    with open(os.path.join(root, "private/state/provider-admin-status"), encoding="ascii") as f:
        provider_status = f.read().strip()
    provider_files = {"private/provider-keyring/ai_provider_vault_keyring.json", "private/provider-vault.tar"}
    present_provider_files = provider_files.intersection(regular)
    if provider_status not in {"true", "false"} or (provider_status == "true" and present_provider_files != provider_files) or (provider_status == "false" and present_provider_files):
        raise SystemExit("Portable provider-admin state and encrypted vault/keyring files disagree.")
    if provider_status == "true" and mfa_status != "mfa_enabled":
        raise SystemExit("Provider administration portable state lacks its required MFA overlay.")
    if provider_status == "true":
        with tarfile.open(os.path.join(root, "private/provider-vault.tar"), mode="r:") as vault:
            seen_vault = set()
            for member in vault.getmembers():
                name = member.name.removeprefix("./").rstrip("/")
                if name and (name.startswith("/") or "\\" in name or ".." in name.split("/")):
                    raise SystemExit("Unsafe provider-vault archive path.")
                if name in seen_vault or not (member.isdir() or member.isreg()) or member.issym() or member.islnk() or member.mode & 0o6000:
                    raise SystemExit("Unsafe provider-vault archive member.")
                seen_vault.add(name)
    for name in regular:
        parts = name.split("/")
        for i in range(1, len(parts)):
            if "/".join(parts[:i]) in regular:
                raise SystemExit("Archive file is also used as a parent directory.")
    for name in sorted(dirs, key=lambda p: (p.count("/"), p)):
        os.makedirs(os.path.join(root, name), mode=0o700, exist_ok=True)
    for name, member in regular.items():
        target = os.path.join(root, *name.split("/"))
        os.makedirs(os.path.dirname(target), mode=0o700, exist_ok=True)
        src = tf.extractfile(member)
        if src is None:
            raise SystemExit("Unreadable archive member.")
        with src, open(target, "xb") as out:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
        os.chmod(target, 0o700 if member.mode & 0o111 else 0o600)

manifest_path = os.path.join(root, "MANIFEST.sha256")
expected = {}
with open(manifest_path, "r", encoding="utf-8") as f:
    for line in f:
        m = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)\n?", line)
        if not m or not safe_name(m.group(2)) or m.group(2) == "MANIFEST.sha256":
            raise SystemExit("Invalid internal manifest entry.")
        if m.group(2) in expected:
            raise SystemExit("Duplicate internal manifest entry.")
        expected[m.group(2)] = m.group(1)
actual_names = set(regular) - {"MANIFEST.sha256"}
if set(expected) != actual_names:
    raise SystemExit("Manifest/file set mismatch.")
for name, digest in expected.items():
    h = hashlib.sha256()
    with open(os.path.join(root, *name.split("/")), "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != digest:
        raise SystemExit("Internal file checksum mismatch.")
counts_path = os.path.join(root, "database.critical-counts.tsv")
expected_count_keys = {
    "identity.users", "conversation.conversations", "conversation.messages",
    "travel.trips", "travel.itineraries", "travel.itinerary_stops",
    "knowledge.production_destinations",
}
counts = {}
with open(counts_path, "r", encoding="ascii") as f:
    for line in f:
        m = re.fullmatch(r"([a-z_]+\.[a-z_]+)\|([0-9]+)\n?", line)
        if not m or m.group(1) in counts:
            raise SystemExit("Invalid or duplicate privacy-safe critical count.")
        counts[m.group(1)] = int(m.group(2))
if set(counts) != expected_count_keys:
    raise SystemExit("Critical count manifest does not contain the exact allowlisted set.")
with open(os.path.join(root, "release/RELEASE_COMMIT"), "r", encoding="ascii") as f:
    if not re.fullmatch(r"[0-9a-f]{40}\n?", f.read()):
        raise SystemExit("Invalid release marker in archive.")
PY
if command -v pg_restore >/dev/null 2>&1; then
  pg_restore --list "$work/extracted/database.dump" >/dev/null
else
  restore_image="${RAHGARD_PG_RESTORE_IMAGE:-rahgard-postgres:17-postgis36-vector087}"
  restore_docker=docker
  if ! docker image inspect "$restore_image" >/dev/null 2>&1; then
    # Windows Docker Desktop can be reachable from WSL through docker.exe even
    # when its Linux integration is disabled for that distribution.
    command -v docker.exe >/dev/null 2>&1 && restore_docker=docker.exe
  fi
  "$restore_docker" image inspect "$restore_image" >/dev/null 2>&1 || {
    echo 'pg_restore is unavailable and the configured PostgreSQL 17 restore image is not local.' >&2; exit 2;
  }
  "$restore_docker" run --rm -i --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
    --cap-drop ALL --security-opt no-new-privileges:true --entrypoint pg_restore "$restore_image" \
    --list < "$work/extracted/database.dump" >/dev/null
fi
python3 "$work/extracted/release/deploy/staging/verify-portable-images.py" \
  "$work/extracted/runtime-images.tar" "$work/extracted/runtime-image-identities.tsv" \
  "$(cat "$work/extracted/release/RELEASE_COMMIT")"
[[ ! -e "$destination" ]] || { echo 'Destination appeared during inspection; refusing to overwrite.' >&2; exit 2; }
mv -T -n -- "$work/extracted" "$destination"
[[ ! -e "$work/extracted" ]] || { echo 'Destination appeared during inspection; refusing to overwrite.' >&2; exit 2; }
echo 'PASS: bundle HMAC, internal manifest, archive paths/types, and PostgreSQL dump listing verified.'
echo "Isolated files: $destination (contains private runtime data; keep protected)."
echo 'No database or live host was restored or changed.'
