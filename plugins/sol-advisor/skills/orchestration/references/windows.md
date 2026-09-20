# Native Windows installation and operations

This fork adds PowerShell entry points backed by Python's standard library. It does
not require sh, Bash, WSL, jq, or third-party Python packages on native Windows.
The POSIX scripts remain available on macOS/Linux. Model/effort contracts, selected
routes, fresh-review rules, and the reviewer sandbox request are unchanged.

## Prerequisites and Desktop setup

Use Windows PowerShell 5.1 or PowerShell 7, native Python 3.11+, and a current native
Codex CLI exposing `codex plugin`. The CLI and Codex Desktop must use the same
`CODEX_HOME`. Without an override, the native helpers use
`$env:USERPROFILE\.codex`; they do not use a WSL home. Git is needed to clone the
repository. Python is checked before the installer makes registration changes.

The plugin is packaged using `.agents/plugins/marketplace.json` and
`plugins/sol-advisor/.codex-plugin/plugin.json`. Installing it through the CLI uses
the Codex plugin mechanism; it does not turn it into a loose skill. Companion agent
registration is an additional step performed by this repository's installer.
Desktop integration still requires a supported Desktop build and a fresh task.

From a PowerShell terminal, after reviewing this fork's code:

~~~powershell
git clone https://github.com/joserey7/sol-advisor.git
Set-Location sol-advisor
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1
~~~

To test a pull request before merge, check out its branch before running the script.
The default marketplace source is the script's own checkout, not the terminal's
current directory. `-ExecutionPolicy Bypass` is process-scoped and does not edit the
machine policy; do not work around an organization-enforced policy.

The installer registers `sol-advisor-joserey7`, installs
`sol-advisor@sol-advisor-joserey7`, resolves that exact ID using `codex plugin list
--json`, validates its source directory and fork manifest, then installs the exact
companion templates from the **installed bundle**, not a guessed cache directory.
It stops on CLI errors, invalid JSON, missing or duplicate matches, or conflicts.
If plugin registration succeeds but companions fail, it reports that partial state.

Restart Codex Desktop and start a new task so the custom-agent types can be discovered.
Select Sol / xhigh in the primary session, then use:

~~~text
Use $sol-advisor:orchestration to build this feature and verify it. Declare the selective route before task tools.
~~~

The fork has a distinct marketplace identity but retains the skill name and three
role filenames. If the upstream plugin is also installed, disable that other copy
in Codex's plugin controls before using the fork, avoiding duplicate skills. The
installer does not disable other plugins or overwrite customized agent files.

## Remote source and updates

After the Windows changes are merged into this fork's main branch, an existing
checkout can instead register the remote marketplace explicitly:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1 -Source joserey7/sol-advisor -Ref main
~~~

Update the registered marketplace and companion roles with:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1 -Update
~~~

For a local marketplace, update that checkout first. `-Update` cannot be combined
with `-Source` or `-Ref`. Every install/update must be followed by a new task. The
script never edits Codex model, effort, sandbox, or approval settings. Custom
`CODEX_HOME` values must already be present in both the CLI and Desktop processes;
setting one only in a terminal does not change an already-running Desktop process.

## Native companion operations

From a repository checkout, these examples use its scripts:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\sol-advisor\scripts\install-agents.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\sol-advisor\scripts\install-agents.ps1 -Check
powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\sol-advisor\scripts\install-agents.ps1 -CheckRole luna
~~~

For an installed skill, `$skillDir` must be the actual directory containing this
skill's `SKILL.md`. Resolve the scripts from that directory, never from an unrelated
working repository. In an existing PowerShell session:

~~~powershell
$skillDir = 'C:\actual\installed\plugin\skills\orchestration'
$installer = Join-Path $skillDir '..\..\scripts\install-agents.ps1'
& $installer -CheckRole luna,sol
~~~

Use `-CheckRole luna` or `terra` for delegate, `-CheckRole sol` for audit, and
`-CheckRole luna,sol` or `terra,sol` for full. Solo has no companion preflight.
`-Check` validates all three; `-CheckRole` implies a non-mutating selective check.
Pass arrays inside PowerShell as above, not as a comma-delimited single string to
`powershell.exe -File`. A process-level alternative with repeated flags is:

~~~powershell
python .\plugins\sol-advisor\scripts\native-support.py install --check-role luna --check-role sol
~~~

An explicit `-TargetDir 'C:\custom home\agents'` overrides the default. Check-only
mode never creates that directory. Filenames and contents are compared exactly:
manual edits, line-ending changes, links, junctions, other reparse points, and
nonregular destinations are not silently repaired. Only known byte-exact historical
Luna/Terra profiles are automatically migrated. `.gitattributes` pins template line
endings to LF for Windows clones. Keep backups and resolve a reported conflict
manually; there is no force-overwrite option. Checks are cached only for the task,
as specified in [operations.md](operations.md).

## Runtime evidence fallback

Use public routing evidence first. When model or effort is absent from that public
record, inspect only the exact native thread ID using the bundled helper:

~~~powershell
$inspector = Join-Path $skillDir '..\..\scripts\inspect-agent-runtime.ps1'
& $inspector -ThreadId '00000000-0000-0000-0000-000000000001'
~~~

Replace the example UUID with the actual native thread ID. `-SessionsDir` overrides
the sessions root for a fixture or another explicitly selected home. The helper
selects exactly one rollout filename, validates consistent metadata, and prints
only the ten allowlisted routing fields. It does not dump messages, prompts,
credentials, environment variables, or arbitrary payloads. Invalid IDs, missing or
ambiguous files, invalid JSON, or inconsistent evidence are failures, not permission
to choose another model. Apply the same reviewer-isolation rules as operations.md.

## Troubleshooting and verification

If `codex` is not found, install the native Codex CLI or supply
`-CodexCommand 'C:\path\to\codex.exe'`. The Desktop application alone does not
necessarily put its CLI on PATH. An unsupported `codex plugin` command is a client
prerequisite failure, not a reason to copy a guessed cache path. If Python discovery
fails, install Python 3.11+ and make `python` or the `py` launcher available.

Maintainers can run the shell-free tests from the repository root:

~~~powershell
python -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\verify-windows.ps1
pwsh -NoProfile -File .\tests\verify-windows.ps1
~~~

CI includes Windows PowerShell 5.1 and PowerShell 7, Python 3.11/3.13, and the existing
Linux POSIX regression suite. The PowerShell bootstrap tests use a fake CLI and
disposable homes; they do not authenticate or run real model sessions. CI success
is not a live Desktop end-to-end test. A release should additionally record an
actual Desktop install, restart/new task, and selected-role preflight on Windows.

Official context: [Codex on Windows](https://developers.openai.com/codex/app/windows),
[plugins](https://developers.openai.com/codex/plugins), and
[plugin packaging](https://developers.openai.com/plugins/build/plugins).
