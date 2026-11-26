#!/usr/bin/env bash
# Restores only the authenticated Owner-MFA/provider-vault overlays to new,
# isolated targets. It never changes a running Compose project or database.
set -Eeuo pipefail
umask 077
bundle_dir="${1:-}"
destination="${2:-}"
provider_volume="${3:-none}"
confirmation="${4:-}"
[[ -d "$bundle_dir" && ! -L "$bundle_dir" && -n "$destination" ]] || {
  echo 'Usage: restore-portable-runtime.sh <authenticated-extraction-dir> <new-private-runtime-dir> <new-provider-volume-or-none> <exact-volume-confirmation>' >&2
  exit 2
}
bundle_dir=$(realpath -e -- "$bundle_dir")
[[ ! -e "$destination" && ! -L "$destination" ]] || { echo 'Runtime destination already exists; refusing overwrite.' >&2; exit 2; }
[[ "$provider_volume" == none || "$provider_volume" =~ ^rahgard_restore_provider_[A-Za-z0-9_]{1,32}$ ]] || {
  echo 'Provider volume must be a new rahgard_restore_provider_* isolated volume name.' >&2; exit 2;
}
[[ "$confirmation" == "$provider_volume" ]] || { echo 'Exact provider-volume confirmation does not match.' >&2; exit 2; }
(
  cd "$bundle_dir"
  sha256sum --check MANIFEST.sha256 >/dev/null
)
mfa_status=$(cat "$bundle_dir/private/state/platform-mfa-status")
provider_status=$(cat "$bundle_dir/private/state/provider-admin-status")
[[ "$mfa_status" == mfa_enabled || "$mfa_status" == mfa_disabled ]] || { echo 'Invalid protected MFA state.' >&2; exit 2; }
[[ "$provider_status" == true || "$provider_status" == false ]] || { echo 'Invalid protected provider state.' >&2; exit 2; }
if [[ "$provider_status" == true ]]; then
  [[ "$mfa_status" == mfa_enabled && "$provider_volume" != none ]] || { echo 'Provider restore requires MFA state and a new isolated provider volume.' >&2; exit 2; }
  if docker volume inspect "$provider_volume" >/dev/null 2>&1; then echo 'Provider target volume already exists; refusing reuse.' >&2; exit 2; fi
else
  [[ "$provider_volume" == none ]] || { echo 'Bundle has no provider vault; refusing to create an unrelated volume.' >&2; exit 2; }
fi

created_volume=false
created_dir=false
cleanup() {
  local status=$?
  if (( status != 0 )); then
    if [[ "$created_volume" == true ]]; then docker volume rm "$provider_volume" >/dev/null 2>&1 || true; fi
    if [[ "$created_dir" == true ]]; then rm -rf -- "$destination"; fi
  fi
  return "$status"
}
trap cleanup EXIT
install -d -m 0700 "$destination"
created_dir=true
if [[ "$mfa_status" == mfa_enabled ]]; then
  install -d -m 0700 "$destination/admin-secrets"
  for name in platform_admin_mfa_encryption_key_hex platform_admin_recovery_pepper; do
    [[ -f "$bundle_dir/private/secrets/$name" && ! -L "$bundle_dir/private/secrets/$name" && -s "$bundle_dir/private/secrets/$name" ]] || {
      echo "Authenticated runtime bundle is missing required MFA material: $name" >&2; exit 2;
    }
    install -m 0400 "$bundle_dir/private/secrets/$name" "$destination/admin-secrets/$name"
  done
fi
if [[ "$provider_status" == true ]]; then
  [[ -f "$bundle_dir/private/provider-keyring/ai_provider_vault_keyring.json" && ! -L "$bundle_dir/private/provider-keyring/ai_provider_vault_keyring.json" && -s "$bundle_dir/private/provider-vault.tar" ]] || {
    echo 'Authenticated runtime bundle is missing the provider keyring or vault archive.' >&2; exit 2;
  }
  install -d -m 0700 "$destination/provider-keyring"
  install -m 0400 "$bundle_dir/private/provider-keyring/ai_provider_vault_keyring.json" \
    "$destination/provider-keyring/ai_provider_vault_keyring.json"
  docker volume create --label rahgard.restore.target=isolated --label rahgard.environment=restore-test \
    "$provider_volume" >/dev/null
  created_volume=true
  release_sha=$(cat "$bundle_dir/release/RELEASE_COMMIT")
  [[ "$release_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid source release identity in portable bundle.' >&2; exit 2; }
  api_image="rahgard-api:$release_sha"
  expected_api_id=$(awk -F'|' -v image="$api_image" '$1==image {print $2}' "$bundle_dir/runtime-image-identities.tsv")
  actual_api_id=$(docker image inspect --format '{{.Id}}' "$api_image" 2>/dev/null || true)
  image_identity=$(docker image inspect --format '{{.Os}}|{{.Architecture}}|{{index .Config.Labels "org.opencontainers.image.revision"}}' "$api_image" 2>/dev/null || true)
  [[ "$expected_api_id" =~ ^sha256:[0-9a-f]{64}$ && "$actual_api_id" == "$expected_api_id" && "$image_identity" == "linux|amd64|$release_sha" ]] || {
    echo 'Exact archived API image is not loaded; load the verified runtime-images.tar before restoring provider state.' >&2; exit 2;
  }
  # Extract only regular files/directories, without restoring archive ownership.
  # The Docker volume is initialized from the API image's UID-10001 directory,
  # and extraction runs as that unprivileged application user.
  extract_python=$(cat <<'PY'
import os, pathlib, sys, tarfile
root = pathlib.Path('/var/lib/rahgard/provider-vault')
if any(root.iterdir()):
    raise SystemExit('Provider restore volume is not empty.')
with tarfile.open(fileobj=sys.stdin.buffer, mode='r|') as archive:
    for member in archive:
        raw = member.name
        name = raw.removeprefix('./').rstrip('/')
        if name and (name.startswith('/') or '\\' in name or '..' in name.split('/')):
            raise SystemExit('Unsafe provider vault archive path.')
        if not (member.isdir() or member.isreg()) or member.issym() or member.islnk() or member.mode & 0o6000:
            raise SystemExit('Unsafe provider vault archive member.')
        if not name:
            continue
        target = root.joinpath(*pathlib.PurePosixPath(name).parts)
        resolved = target.resolve()
        if not resolved.is_relative_to(root):
            raise SystemExit('Provider vault archive path escapes target.')
        if member.isdir():
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(target, 0o700)
            continue
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        source = archive.extractfile(member)
        if source is None:
            raise SystemExit('Provider vault archive member cannot be read.')
        with source, target.open('xb') as output:
            while block := source.read(1024 * 1024):
                output.write(block)
        os.chmod(target, 0o600)
if not any(root.iterdir()):
    raise SystemExit('Provider vault archive was empty.')
PY
)
  docker run --rm -i --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
    --cap-drop ALL --security-opt no-new-privileges:true \
    --mount "type=volume,src=$provider_volume,dst=/var/lib/rahgard/provider-vault" \
    --entrypoint python "$api_image" -c "$extract_python" < "$bundle_dir/private/provider-vault.tar"
  volume_labels=$(docker volume inspect --format '{{index .Labels "rahgard.restore.target"}}|{{index .Labels "rahgard.environment"}}' "$provider_volume")
  [[ "$volume_labels" == 'isolated|restore-test' ]] || { echo 'Restored provider volume lacks isolated restore-test labels.' >&2; exit 2; }
fi
printf 'PASS: protected runtime overlay restored to a new isolated target; MFA=%s provider_admin=%s.\n' "$mfa_status" "$provider_status"
printf 'No application container, database, existing volume, or live deployment was modified.\n'
