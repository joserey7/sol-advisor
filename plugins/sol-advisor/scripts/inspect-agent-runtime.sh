#!/bin/sh
# Inspect only the requested thread; never print messages, tokens, or arbitrary logs.
set -eu
script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1
. "$script_dir/python-common.sh"
sol_advisor_python "$script_dir/native-support.py" inspect "$@"
