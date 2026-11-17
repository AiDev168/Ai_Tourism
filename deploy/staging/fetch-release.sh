#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
sha="${1:-}"
archive="${2:-}"
expected="${3:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: fetch-release.sh <40-hex-commit> <archive> <sha256>' >&2; exit 2; }
[[ "$expected" =~ ^[0-9a-f]{64}$ && -f "$archive" ]] || { echo 'Archive or expected SHA-256 is invalid.' >&2; exit 2; }
actual=$(sha256sum "$archive" | cut -d' ' -f1)
[[ "$actual" == "$expected" ]] || { echo 'Release archive checksum mismatch.' >&2; exit 2; }
release="$root/releases/$sha"
[[ ! -e "$release" ]] || { echo 'Release directory already exists; preserving it.' >&2; exit 2; }
mkdir -m 0700 "$release"
trap 'rm -rf -- "$release"' ERR
if tar -tzf "$archive" | awk 'BEGIN{bad=0} /^\// || /(^|\/)\.\.(\/|$)/ {bad=1} END{exit bad?0:1}'; then
  echo 'Release archive contains an unsafe path.' >&2; exit 2
fi
tar -xzf "$archive" -C "$release" --no-same-owner
# The release archive is application source, not secret material. Because this
# script runs with umask 077, restore readable modes so containers running as
# non-root can read their bind-mounted SQL and init scripts. Preserve the
# executable bit only for files that were executable in the archive.
find "$release" -type d -exec chmod 0755 {} +
find "$release" -type f -perm /111 -exec chmod 0755 {} +
find "$release" -type f ! -perm /111 -exec chmod 0644 {} +
chmod 0755 "$release"
printf '%s\n' "$sha" > "$release/RELEASE_COMMIT"
chmod 0444 "$release/RELEASE_COMMIT"
test -s "$release/deploy/staging/compose.yaml"
printf 'Release %s unpacked and SHA-256 verified.\n' "$sha"
