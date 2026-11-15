#!/usr/bin/env bash
# Extracts into a NEW isolated directory only. Does not touch a running app/DB.
set -Eeuo pipefail
umask 077
bundle="${1:-}"
keyfile="${2:-}"
destination="${3:-}"
[[ -f "$bundle" && -f "$bundle.sha256" && -s "$keyfile" && -n "$destination" ]] || {
  echo 'Usage: inspect-portable.sh <bundle.tar.enc> <independent-passphrase-file> <new-empty-directory>' >&2
  exit 2
}
[[ ! -e "$destination" ]] || { echo 'Destination already exists; refusing to overwrite.' >&2; exit 2; }
(
  cd "$(dirname "$bundle")"
  sha256sum --check "$(basename "$bundle").sha256"
)
mkdir -m 0700 -- "$destination"
trap 'echo "Portability inspection failed; review isolated staging directory." >&2' ERR
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass file:"$keyfile"   -in "$bundle" | tar -xf - --no-same-owner -C "$destination"
(
  cd "$destination"
  test -s database.dump
  test -s private/host.env
  test -s release/RELEASE_COMMIT
  sha256sum --check MANIFEST.sha256 >/dev/null
  pg_restore --list database.dump >/dev/null
)
echo 'PASS: encrypted portability bundle extracted, every bundled checksum verified, and PostgreSQL dump listed.'
echo "Isolated files: $destination (private: do not publish or commit to GitHub)."
echo 'No database or live host was restored or changed.'
