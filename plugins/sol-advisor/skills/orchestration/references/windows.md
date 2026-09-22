# Native Windows installation and operations

Use PowerShell 5.1+ and Python 3.11+ with the same Codex home as the desktop app.
No Bash, WSL, jq, third-party Python packages, or persistent execution-policy change
is required. Do not fall back to WSL, another home, or another model after a failure.

## Install and update

From a reviewed clone of `joserey7/sol-advisor`:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1
# Later, update the installed marketplace and core profiles:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1 -Update
~~~

This process-only execution-policy option does not override managed organization policy.
The bootstrap finds the exact installed plugin and installs its cached profiles, not
potentially different templates from the working checkout. It never edits Codex model,
sandbox, or default-agent settings. Restart the app and start a NEW task on GPT-6 Sol /
xhigh. Check selected auxiliary access at runtime; installed files are not proof of access.

The default bundle installs Luna implementation, Sol implementation, and Sol review.
Astra is optional. To install its profile explicitly:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1 -Update -WithAstra
~~~

`-WithAstra` installs only; it never authorizes paid use. Every consultation follows
[astra-advice.md](astra-advice.md). Use `-WithAstra` on updates to keep an opted-in
profile current; default updates ignore the optional role.

## Companion checks

In a checkout, or substituting the scripts directory of the installed plugin:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\sol-advisor\scripts\install-agents.ps1 -Check
# Sol implementer, NOT the reviewer:
powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\sol-advisor\scripts\install-agents.ps1 -CheckRole sol-implementer
# The legacy sol check alias still means the reviewer:
powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\sol-advisor\scripts\install-agents.ps1 -CheckRole sol
~~~

Direct script invocation supports `-CheckRole luna,sol` arrays; when using `-File`, check
one role at a time or call Python with repeated `--check-role`. `-TargetDir` overrides
`CODEX_HOME\agents` / `USERPROFILE\.codex\agents`. Checks never create missing roles.

## Plan validation and runtime inspection

When operating from the installed skill, use its helper and resolve Python with the
bundled `python-common.ps1` (prefers a compatible native Python):

~~~powershell
$skillDir = '<directory containing the installed SKILL.md>'
$scripts = [IO.Path]::GetFullPath((Join-Path $skillDir '..\..\scripts'))
. (Join-Path $scripts 'python-common.ps1')
$python = Get-SolAdvisorPython
$prefix = @($python.Prefix)
$helper = Join-Path $scripts 'native-support.py'
'{"mode":"audit","difficulty":"judgment-heavy","risk":"material"}' |
    & $python.Executable @prefix $helper check-plan
& $python.Executable @prefix $helper install --check-role sol
& $python.Executable @prefix $helper inspect --expect-role sol --require-read-only '<native-thread-uuid>'
~~~

The existing `inspect-agent-runtime.ps1 -ThreadId ... -SessionsDir ...` remains a
metadata-only convenience wrapper. Use the Python invocation above for expected-role
and hard-isolation assertions. Runtime checks must follow public metadata precedence
and the actual-isolation rules in [operations.md](operations.md).

## Migration and troubleshooting

Exact recognized v0.7.0 Luna/Sol files migrate to GPT-6. Older immutable fingerprints,
including v0.6.0 CRLF Windows variants, remain supported. Exact Terra files are archived
under the sibling `sol-advisor-retired` directory; customized files remain untouched
with a warning. Review and move retained Terra files outside the agents directory;
this skill never selects them, but their presence can affect other Codex workflows.

A conflicting active profile, symlink, junction, or conflicting retirement archive is
not permission to overwrite it. Back up and inspect the reported file; do not normalize
all line endings, delete a whole Codex home, or reset global config. New current CRLF
profiles remain conflicts, not automatic migrations. Do not run concurrent installers.

For CLI-not-found errors, supply `-CodexCommand` with the native executable/CMD shim.
For Python errors, install a compatible native interpreter; the launcher supports `py`
and `python` without silently selecting an unsupported version. Marketplace/bootstrap
failures stop companion changes and report their stage. Start a new task after success
so old discovered roles are not reused.

CI runs the portable suite and native wrappers with both PowerShell engines and Python
versions. This does not replace a live Codex smoke test on the target Windows installation.
