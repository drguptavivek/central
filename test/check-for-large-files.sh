#!/bin/bash -eu
set -o pipefail
shopt -s inherit_errexit

log() { echo "[check-for-large-files] $*"; }

# Historical VG documentation artifacts predate this upstream size gate. Keep
# the exceptions exact so new large files, including new files in these
# directories, still fail the check.
allowedLargeFiles=(
  'docs/vg/screenshots/collect_fork/02_QR_Config.png'
  'docs/vg/vg-server/rebase-2025.04/test-results-upstream-integration copy.json'
  'docs/vg/vg-server/rebase-2025.04/test-results-upstream-integration.json'
)

isAllowedLargeFile() {
  local candidate="$1"
  local allowed
  for allowed in "${allowedLargeFiles[@]}"; do
    [[ "$candidate" = "$allowed" ]] && return 0
  done
  return 1
}

log 'Checking for large files...'
trackedFiles="$(mktemp)"
trap 'rm -f "$trackedFiles"' EXIT
git ls-files -z > "$trackedFiles"

largeFileCount=0
while IFS= read -r -d '' file; do
  [[ -f "$file" ]] || continue
  size="$(wc -c < "$file")"
  if (( size > 1000000 )); then
    if isAllowedLargeFile "$file"; then
      printf '[check-for-large-files] Allowed historical file: %s\t%s\n' "$size" "$file"
    else
      ((largeFileCount += 1))
      printf '%s\t%s\n' "$size" "$file"
    fi
  fi
done < "$trackedFiles"

if (( largeFileCount > 0 )); then
  log "!!! $largeFileCount LARGE FILE(S) FOUND"
  exit 1
fi

log 'No unapproved large files found ✅'
