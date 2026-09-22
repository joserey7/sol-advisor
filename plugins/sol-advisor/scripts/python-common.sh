#!/bin/sh
# Shared launcher: do not fall back to WSL, another CODEX_HOME, or an older Python.
sol_advisor_python() {
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    python3 "$@"
  elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    python "$@"
  else
    printf '%s\n' 'ERROR: Python 3.11+ is required.' >&2
    return 1
  fi
}
