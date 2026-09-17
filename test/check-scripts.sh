#!/bin/bash -eu
set -o pipefail
shopt -s inherit_errexit

log() { echo >&2 "[$(basename "$0")] $*"; }

expectedShebang=$'#!/bin/bash -eu\nset -o pipefail\nshopt -s inherit_errexit\n'
expectedPosixShebang=$'#!/bin/sh\nset -eu\n'

scriptFiles="$(
  while IFS= read -r -d '' entry; do
    mode="${entry%% *}"
    [[ "$mode" = 100755 ]] || continue
    file="${entry#*$'\t'}"
    IFS= read -r firstLine < "$file" || true
    if [[ "$firstLine" =~ ^#!.*sh([[:space:]]|$) ]]; then
      printf '%s\n' "$file"
    fi
  done < <(git ls-files --stage -z)
  git ls-files '*.sh'
)"
scriptFiles="$(printf '%s\n' "$scriptFiles" | sort -u)"

for script in $scriptFiles; do
  log "Checking $script ..."

  log "  Checking trailing whitespace on lines..."
  if grep -E '\s+$' "$script"; then
    log "    !!! Whitespace found at end of line !!!"
    exit 1
  fi
  log "    Passed OK."

  log "  Checking trailing newline in files..."
  if [[ -n "$(tail -c 1 < "$script")" ]]; then
    log "    !!! Missing final newline !!!"
    exit 1
  fi
  if [[ -z "$(tail -c 2 < "$script")" ]]; then
    log "    !!! Blank lines at end of file !!!"
    exit 1
  fi
  log "    Passed OK."

  log "  Checking for tab-based indentation..."
  if grep $'\t' "$script"; then
    log "    !!! Tab(s) found."
    log "    !!!"
    log "    !!! Please use spaces for indentation."
    exit 1
  fi
  log "    Passed OK."

  log "  Checking shebang..."
  case "$(head -n1 "$script")" in
    '#!/bin/bash -eu')
      shebangLines=3
      expectedScriptShebang="$expectedShebang"
      ;;
    '#!/bin/sh')
      shebangLines=2
      expectedScriptShebang="$expectedPosixShebang"
      ;;
    *)
      shebangLines=3
      expectedScriptShebang="$expectedShebang"
      ;;
  esac
  shebang="$(head -n"$shebangLines" "$script")"
  if ! diff <(echo "$shebang") <(printf '%s' "$expectedScriptShebang"); then
    log "    !!!"
    log "    !!! Missing or unexpected shebang."
    log "    !!!"
    log "    !!! To make reasoning about script behaviour easier, please"
    log "    !!! use one of the standard shebang and shell config blocks:"
    log "    !!!"
    echo
    printf '%s' "$expectedShebang"
    echo
    printf '%s' "$expectedPosixShebang"
    echo
    exit 1
  fi
  log "    Passed OK."

  log "  Checking for indirect invocations..."
  # shellcheck disable=2086
  if git grep -E "sh.*$(basename "$script")" $scriptFiles; then
    log "    !!!"
    log "    !!! Possible indirect invocation(s) found."
    log "    !!!"
    log "    !!! Invoking scripts indirectly means they may be run with an"
    log "    !!! unexpected shell.  Try invoking the script directly and"
    log "    !!! relying on its shebang."
    log "    !!!"
    exit 1
  fi
  log "    Passed OK."
done

log "Running shellcheck..."
echo "$scriptFiles" | xargs \
    shellcheck \
        --exclude=SC2016
log "  Shellcheck passed OK."

log "All scripts passed OK."
