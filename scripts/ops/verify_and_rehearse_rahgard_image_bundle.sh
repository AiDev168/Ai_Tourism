#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly root=/opt/rahgard-staging
readonly release_sha=d5d9847373b20087a8a866449c6550d306f45b63
readonly verifier="$(cd "$(dirname "$0")" && pwd)/verify_rahgard_release_image_bundle.py"
readonly rehearsal="$(cd "$(dirname "$0")/../../deploy/staging" && pwd)/rehearse-018-021.sh"
bundle_dir="${1:-}"
backup_name="${2:-}"

[[ "$bundle_dir" == "$root"/incoming/* && -d "$bundle_dir" \
  && ! -L "$root" && ! -L "$root/incoming" && ! -L "$bundle_dir" ]] || {
  echo 'Bundle must be a non-symlink directory under /opt/rahgard-staging/incoming.' >&2
  exit 2
}
bundle_dir="$(realpath -e -- "$bundle_dir")"
[[ "$bundle_dir" == "$root"/incoming/* ]] || { echo 'Resolved bundle path escapes the incoming directory.' >&2; exit 2; }
[[ "$backup_name" =~ ^rahgard-[A-Za-z0-9_.-]+\.dump\.enc$ ]] || {
  echo 'Usage: verify_and_rehearse_rahgard_image_bundle.sh <incoming-bundle-dir> <encrypted-backup-basename>' >&2
  exit 2
}
[[ "$(cat "$root/releases/$release_sha/RELEASE_COMMIT")" == "$release_sha" ]] || {
  echo 'The prepared immutable source release is not staged at the expected path.' >&2
  exit 2
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
python3 "$verifier" verify \
  --source-sha "$release_sha" \
  --image-archive "$image_archive" \
  --manifest "$manifest"

for tag in "rahgard-api:$release_sha" "rahgard-web:$release_sha"; do
  if docker image inspect "$tag" >/dev/null 2>&1; then
    echo "Refusing to replace an image tag that already exists: $tag" >&2
    exit 2
  fi
done

docker load --input "$image_archive"
python3 "$verifier" verify \
  --source-sha "$release_sha" \
  --image-archive "$image_archive" \
  --manifest "$manifest" \
  --check-loaded-images

RAHGARD_REHEARSAL_RELEASE_DIR="$root/releases/$release_sha" \
RAHGARD_REHEARSAL_API_IMAGE="rahgard-api:$release_sha" \
RAHGARD_REHEARSAL_WEB_IMAGE="rahgard-web:$release_sha" \
RAHGARD_REQUIRE_RELEASE_IMAGES=true \
  bash "$rehearsal" "$backup_name"

echo "HOSTED_IMAGE_REHEARSAL_PASS source=$release_sha live_services_touched=false live_database_touched=false"
