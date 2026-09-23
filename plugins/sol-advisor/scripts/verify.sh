#!/bin/sh
# Portable regression suite, including historical migration and POSIX CLI fixtures.
set -eu
script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
repo_dir=$(CDPATH= cd "$script_dir/../../.." && pwd) || exit 1
. "$script_dir/python-common.sh"
for script in "$script_dir"/*.sh; do sh -n "$script"; done
sol_advisor_python -m unittest discover -s "$repo_dir/tests" -v
