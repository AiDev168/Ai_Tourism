#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

image="${1:-}"
release_sha="${2:-}"
[[ "$image" == "rahgard-web:$release_sha" && "$release_sha" =~ ^[0-9a-f]{40}$ ]] || {
  echo 'Usage: test_rahgard_web_image_pwa.sh rahgard-web:<full-source-sha> <full-source-sha>' >&2
  exit 2
}
read -r image_id image_os image_arch image_revision < <(
  docker image inspect --format '{{.Id}} {{.Os}} {{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}' "$image"
)
[[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ && "$image_os" == linux && "$image_arch" == amd64 && "$image_revision" == "$release_sha" ]] || {
  echo 'Web image identity, platform, or source revision does not match the requested release.' >&2
  exit 3
}

probe="rahgard-pwa-probe-${release_sha:0:8}-$$"
[[ "$probe" =~ ^rahgard-pwa-probe-[0-9a-f]{8}-[0-9]+$ ]] || { echo 'Invalid PWA probe container name.' >&2; exit 2; }
[[ -z "$(docker ps -aq --filter "name=^/${probe}$")" ]] || { echo 'PWA probe container already exists.' >&2; exit 2; }
cleanup() {
  local status=$?
  if docker inspect "$probe" >/dev/null 2>&1; then
    labels=$(docker inspect -f '{{index .Config.Labels "rahgard.test"}}|{{index .Config.Labels "org.opencontainers.image.revision"}}' "$probe" 2>/dev/null || true)
    if [[ "$labels" == "web-pwa|$release_sha" ]]; then docker rm -f "$probe" >/dev/null 2>&1 || true; fi
  fi
  exit "$status"
}
trap cleanup EXIT

# No network attachment, published port, bind mount, writable image layer, or
# application secret. Test Nginx and its own unprivileged worker in the image.
docker run -d --rm --name "$probe" --network none --add-host api:127.0.0.1 --read-only \
  --tmpfs /var/cache/nginx:rw,noexec,nosuid,size=32m \
  --tmpfs /var/run:rw,noexec,nosuid,size=4m \
  --tmpfs /tmp:rw,noexec,nosuid,size=4m \
  --security-opt no-new-privileges:true --cap-drop ALL --cap-add CHOWN --cap-add SETUID --cap-add SETGID \
  --label rahgard.test=web-pwa --label "org.opencontainers.image.revision=$release_sha" \
  --entrypoint nginx "$image" -g 'daemon off;' >/dev/null

ready=false
for _ in $(seq 1 20); do
  if docker exec "$probe" nginx -t >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Nginx did not start in the isolated Web image probe.' >&2; exit 3; }
docker exec "$probe" nginx -T 2>&1 | grep -Eq '^[[:space:]]*user[[:space:]]+nginx;'
docker exec --user nginx "$probe" sh -ec \
  'test -r /usr/share/nginx/html/manifest.webmanifest && test -r /usr/share/nginx/html/sw.js && test -r /usr/share/nginx/html/index.html'

fetch() { docker exec "$probe" wget -q -O - "http://127.0.0.1:8080$1"; }
headers() { docker exec "$probe" sh -c 'wget -S -O /dev/null "$1" 2>&1' sh "http://127.0.0.1:8080$1"; }
html=$(fetch /)
[[ "$html" == *'<div id="root">'* ]] || { echo 'PWA probe root was not the application shell.' >&2; exit 3; }
manifest=$(fetch /manifest.webmanifest)
[[ "$manifest" == *'"name":"Rahgard'* ]] || { echo 'PWA manifest body is missing or unexpected.' >&2; exit 3; }
manifest_headers=$(headers /manifest.webmanifest)
grep -Eiq 'Content-Type:[[:space:]]*application/manifest\+json' <<<"$manifest_headers" || {
  echo 'PWA manifest has the wrong content type.' >&2; exit 3;
}
sw=$(fetch /sw.js)
[[ "$sw" == *'self.addEventListener'* && "$sw" == *'rahgard-shell-'* ]] || {
  echo 'Service worker body is missing or unexpected.' >&2; exit 3;
}
sw_headers=$(headers /sw.js)
grep -Eiq 'Content-Type:[[:space:]]*(application|text)/javascript' <<<"$sw_headers" || {
  echo 'Service worker has the wrong content type.' >&2; exit 3;
}

mapfile -t assets < <(python3 -c 'import re,sys; print("\n".join(sorted(set(re.findall(r"/assets/[^\" ]+\.(?:js|css)", sys.stdin.read()))))' <<<"$html")
[[ "${#assets[@]}" -ge 2 ]] || { echo 'Application shell did not reference hashed JS and CSS assets.' >&2; exit 3; }
seen_js=false; seen_css=false
for asset in "${assets[@]}"; do
  [[ "$asset" =~ ^/assets/[A-Za-z0-9._-]+\.(js|css)$ ]] || { echo 'Invalid or unhashed application asset path.' >&2; exit 3; }
  asset_headers=$(headers "$asset")
  if [[ "$asset" == *.js ]]; then
    seen_js=true
    grep -Eiq 'Content-Type:[[:space:]]*(application|text)/javascript' <<<"$asset_headers" || { echo 'Hashed JS asset has the wrong content type.' >&2; exit 3; }
  else
    seen_css=true
    grep -Eiq 'Content-Type:[[:space:]]*text/css' <<<"$asset_headers" || { echo 'Hashed CSS asset has the wrong content type.' >&2; exit 3; }
  fi
done
[[ "$seen_js" == true && "$seen_css" == true ]] || { echo 'Hashed JS or CSS asset is absent.' >&2; exit 3; }
if docker exec "$probe" wget -q -O /dev/null http://127.0.0.1:8080/assets/rahgard-missing-regression.js >/dev/null 2>&1; then
  echo 'Missing asset unexpectedly returned success; SPA fallback could conceal broken assets.' >&2; exit 3
fi

printf 'PWA_IMAGE_PASS image=%s id=%s worker=nginx mode=readable root=200 manifest=200 service_worker=200 hashed_js_css=200 mime=pass missing_asset=404\n' \
  "$image" "$image_id"
