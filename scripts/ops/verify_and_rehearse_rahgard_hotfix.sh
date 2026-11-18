#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly root=/opt/rahgard-staging
source_sha="${1:-}"
bundle_dir="${2:-}"
backup_name="${3:-}"
readonly verifier="$(cd "$(dirname "$0")" && pwd)/verify_rahgard_release_image_bundle.py"
readonly rehearsal="$(cd "$(dirname "$0")/../../deploy/staging" && pwd)/rehearse-20-20.sh"

[[ "$source_sha" =~ ^[0-9a-f]{40}$ && "$bundle_dir" == "$root"/incoming/* \
  && -d "$bundle_dir" && ! -L "$bundle_dir" \
  && "$backup_name" =~ ^rahgard-[A-Za-z0-9_.-]+\.dump\.enc$ ]] || {
  echo 'Usage: verify_and_rehearse_rahgard_hotfix.sh <source-sha> <incoming-bundle-dir> <post-0021-backup-name>' >&2
  exit 2
}
bundle_dir="$(realpath -e -- "$bundle_dir")"
[[ "$bundle_dir" == "$root"/incoming/* && ! -L "$root" && ! -L "$root/incoming" ]] || {
  echo 'Resolved bundle path escapes the protected incoming directory.' >&2; exit 2;
}
release_dir="$root/releases/$source_sha"
[[ -s "$release_dir/RELEASE_COMMIT" && "$(cat "$release_dir/RELEASE_COMMIT")" == "$source_sha" ]] || {
  echo 'The exact immutable source release must be staged before image rehearsal.' >&2; exit 2;
}
image_archive="$bundle_dir/rahgard-images-linux-amd64.tar"
manifest="$bundle_dir/release-manifest.json"
checksums="$bundle_dir/SHA256SUMS.txt"
for file in "$image_archive" "$manifest" "$checksums"; do
  [[ -f "$file" && ! -L "$file" && -s "$file" ]] || { echo 'Image bundle is incomplete.' >&2; exit 2; }
done
(
  cd "$bundle_dir"
  sha256sum --check -- SHA256SUMS.txt
)
python3 "$verifier" verify --source-sha "$source_sha" --image-archive "$image_archive" --manifest "$manifest"

api_tag="rahgard-api:$source_sha"
web_tag="rahgard-web:$source_sha"
api_present=false; web_present=false
docker image inspect "$api_tag" >/dev/null 2>&1 && api_present=true || true
docker image inspect "$web_tag" >/dev/null 2>&1 && web_present=true || true
if [[ "$api_present" == false && "$web_present" == false ]]; then
  docker load --input "$image_archive"
elif [[ "$api_present" != "$web_present" ]]; then
  echo 'Only one immutable application image tag is loaded; refusing to overwrite a partial tag pair.' >&2
  exit 2
else
  echo 'Both immutable target tags already exist; verifying them without replacement.'
fi
python3 "$verifier" verify --source-sha "$source_sha" --image-archive "$image_archive" \
  --manifest "$manifest" --check-loaded-images

RAHGARD_REHEARSAL_RELEASE_DIR="$release_dir" \
  bash "$rehearsal" "$backup_name" "$source_sha" "$api_tag" "$web_tag"

echo "HOTFIX_IMAGE_REHEARSAL_PASS source=$source_sha live_application_touched=false live_database_mutated=false migrations_applied=0"
