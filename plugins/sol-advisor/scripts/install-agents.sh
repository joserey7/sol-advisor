#!/bin/sh
# One installation implementation for POSIX and native Windows.
# Core roles by default; --with-astra opts in to installation, never to spending.
set -eu
script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
. "$script_dir/python-common.sh"
sol_advisor_python "$script_dir/native-support.py" install "$@"
