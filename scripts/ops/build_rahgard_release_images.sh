#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly api_base='python:3.13.9-slim-bookworm'
readonly node_base='node:22.14-alpine'
readonly nginx_base='nginx:1.27-alpine'
source_dir="${1:-}"
output_dir="${2:-}"
release_sha="${RELEASE_SHA:-}"

[[ "$release_sha" =~ ^[0-9a-f]{40}$ ]] || {
  echo 'RELEASE_SHA must be a full immutable 40-character commit SHA.' >&2
  exit 2
}
[[ -d "$source_dir/.git" && -d "$source_dir/deploy/staging" ]] || {
  echo 'Source checkout or staging Dockerfiles are unavailable.' >&2
  exit 2
}
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$release_sha" ]] || {
  echo 'Checked-out source HEAD does not match RELEASE_SHA.' >&2
  exit 2
}
[[ -z "$(git -C "$source_dir" status --porcelain --untracked-files=all)" ]] || {
  echo 'Source checkout is not clean; refusing a non-commit build context.' >&2
  exit 2
}
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || {
  echo 'This workflow requires a GitHub-hosted Linux x86_64 runner.' >&2
  exit 2
}
command -v docker >/dev/null && command -v python3 >/dev/null && command -v sha256sum >/dev/null || {
  echo 'docker, python3, and sha256sum are required on the build runner.' >&2
  exit 2
}
[[ ! -e "$output_dir" ]] || { echo 'Output path already exists.' >&2; exit 2; }
mkdir -m 0700 -p "$output_dir"
work_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/rahgard-release-build.XXXXXX")"
cleanup() { rm -rf -- "$work_dir"; }
trap cleanup EXIT

# Build context comes only from the immutable Git tree. No runner .env,
# credentials, generated artifacts, or untracked files can enter the context.
git -C "$source_dir" archive --format=tar "$release_sha" > "$work_dir/source.tar"
source_archive_sha="$(sha256sum "$work_dir/source.tar" | awk '{print $1}')"
source_tree="$work_dir/source"
mkdir "$source_tree"
tar -xf "$work_dir/source.tar" -C "$source_tree"
python3 - "$source_tree" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
bad = [str(path.relative_to(root)) for path in root.rglob("*.sh") if b"\r" in path.read_bytes()]
if bad:
    raise SystemExit("Source archive contains CRLF shell scripts: " + ", ".join(bad[:20]))
PY
for dockerfile in deploy/staging/Dockerfile.api deploy/staging/Dockerfile.web; do
  [[ -f "$source_tree/$dockerfile" ]] || { echo "Missing target Dockerfile: $dockerfile" >&2; exit 2; }
done

for base in "$api_base" "$node_base" "$nginx_base"; do
  echo "Pulling approved pinned parent on the authorized hosted runner: $base"
  docker pull --platform linux/amd64 "$base"
done

api_tag="rahgard-api:$release_sha"
web_tag="rahgard-web:$release_sha"
docker buildx build --platform linux/amd64 --pull=false --load \
  --label "org.opencontainers.image.revision=$release_sha" \
  --label "org.opencontainers.image.title=Rahgard API" \
  --tag "$api_tag" \
  --file "$source_tree/deploy/staging/Dockerfile.api" "$source_tree"
docker buildx build --platform linux/amd64 --pull=false --load \
  --label "org.opencontainers.image.revision=$release_sha" \
  --label "org.opencontainers.image.title=Rahgard Web" \
  --tag "$web_tag" \
  --file "$source_tree/deploy/staging/Dockerfile.web" "$source_tree"

docker image inspect "$api_tag" "$web_tag" >/dev/null
docker save --output "$output_dir/rahgard-images-linux-amd64.tar" "$api_tag" "$web_tag"

python3 "$(dirname "$0")/verify_rahgard_release_image_bundle.py" create \
  --source-sha "$release_sha" \
  --source-archive "$work_dir/source.tar" \
  --image-archive "$output_dir/rahgard-images-linux-amd64.tar" \
  --output-manifest "$output_dir/release-manifest.json" \
  --source-dir "$source_tree" \
  --api-base "$api_base" --node-base "$node_base" --nginx-base "$nginx_base" \
  --image-tags "$api_tag" "$web_tag"

python3 "$(dirname "$0")/verify_rahgard_release_image_bundle.py" verify \
  --source-sha "$release_sha" \
  --source-archive "$work_dir/source.tar" \
  --image-archive "$output_dir/rahgard-images-linux-amd64.tar" \
  --manifest "$output_dir/release-manifest.json" \
  --check-loaded-images

(
  cd "$output_dir"
  sha256sum rahgard-images-linux-amd64.tar release-manifest.json > SHA256SUMS.txt
  sha256sum --check SHA256SUMS.txt
)
chmod 0444 "$output_dir/rahgard-images-linux-amd64.tar" \
  "$output_dir/release-manifest.json" "$output_dir/SHA256SUMS.txt"
echo "BUILD_ARTIFACT_READY source=$release_sha platform=linux/amd64 artifact_dir=$output_dir"
