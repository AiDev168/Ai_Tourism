#!/usr/bin/env bash
# Shared guarded selector for the base Compose file and opt-in security overlays.
set -Eeuo pipefail

rahgard_compose_init() {
  local env_file="$1" release="$2" target_name="$3" tmp
  [[ "$target_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] || {
    echo 'Invalid internal Compose array name.' >&2; return 2;
  }
  local repo_root helper
  repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
  helper="$repo_root/scripts/ops/rahgard_runtime_compose.py"
  [[ -f "$helper" && ! -L "$helper" ]] || {
    echo 'Release is missing the guarded runtime Compose selector.' >&2; return 2;
  }
  tmp=$(mktemp "${TMPDIR:-/tmp}/rahgard-compose-args.XXXXXX")
  if ! python3 "$helper" --env-file "$env_file" --release "$release" --format nul > "$tmp"; then
    rm -f -- "$tmp"
    return 2
  fi
  local -a parsed=()
  mapfile -d '' -t parsed < "$tmp"
  rm -f -- "$tmp"
  [[ ${#parsed[@]} -ge 6 && "${parsed[0]}" == docker && "${parsed[1]}" == compose ]] || {
    echo 'Runtime Compose selector returned an invalid command.' >&2; return 2;
  }
  local -n target="$target_name"
  target=("${parsed[@]}")
}
