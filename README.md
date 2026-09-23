# Sol Advisor

**GPT-6 Sol owns delivery. Luna implements bounded work. A fresh Sol reviews when
risk warrants it. Astra advises only on explicitly authorized exceptional decisions.**

A Codex-native workflow with four selective routes, not an always-on agent pipeline.
The primary keeps intent, architecture, verification, and acceptance. Start with `solo`;
delegate only when it replaces meaningful work or context. GPT-6 Sol replaces the Terra
implementation lane. **v0.8.0** is the GPT-6 release; v0.7.0 remains the
published GPT-5.6 checkpoint. See [CHANGELOG.md](CHANGELOG.md).

## Quick start

Use a current Codex CLI with plugins and native custom agents, and the same Codex home
as the desktop app. **Python 3.11+ is required on Windows, macOS, and Linux.** Both
platform wrappers now use one standard-library implementation. Select **GPT-6 Sol /
xhigh** in the primary session. Only selected auxiliaries need model access.

### Windows: native PowerShell

From a reviewed clone of this fork, with PowerShell 5.1+:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1
~~~

The policy option is process-scoped; do not change managed policy. No Bash, WSL, or jq.
See [Windows installation and troubleshooting](plugins/sol-advisor/skills/orchestration/references/windows.md).

### macOS / Linux

The following plugin-path convenience command uses jq (not needed by the installer):

~~~sh
codex plugin marketplace add joserey7/sol-advisor --ref main
codex plugin add sol-advisor@sol-advisor-joserey7
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "sol-advisor@sol-advisor-joserey7") | .source.path')" && test -n "$plugin_dir" && test "$plugin_dir" != null && test -d "$plugin_dir" && sh "$plugin_dir/scripts/install-agents.sh"
~~~

Start a NEW task after installation:

~~~text
Use $sol-advisor:orchestration to build and verify this feature. Declare the route,
inspect before confirming it, and do not use Astra without my explicit authorization.
~~~

## Routes and models

| Mode | Delivery | Select it when |
|---|---|---|
| `solo` | Primary Sol plans, implements, tests, and self-reviews. | Default; consequence risk is contained. |
| `delegate` | One Luna or Sol implementer executes; primary verifies. | Delegation replaces substantial work/context; consequences are contained. |
| `audit` | Primary implements and verifies; fresh read-only Sol reviews. | Independent scrutiny matters more than delegating implementation. |
| `full` | One implementer, primary verification, fresh Sol review. | Explicitly justified broad or material-risk exception. |

Luna / max handles fully specified bounded implementation. Sol / xhigh handles
judgment-heavy implementation and fresh review in SEPARATE roles. The primary remains
Sol / xhigh. Material consequence risk requires audit/full even for a small diff.
Difficulty chooses the worker; consequences choose review; work saved justifies delegation.

Sol declares a provisional route before task tools, permits bounded read-only discovery,
and confirms the route before edits or spawns. Normal delivery uses at most one auxiliary;
full is an exception. Reports never replace parent diff inspection and verification.
A reviewer does not implement its own fixes; any correction invalidates the prior verdict.

## Astra is optional, not automatic

Astra / high is absent from the default companion installation. To install its profile:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1 -Update -WithAstra
~~~

On POSIX run `sh "$plugin_dir/scripts/install-agents.sh" --with-astra` after resolving
the installed plugin directory as above. Installation is NOT authorization to spend.

Only explicitly authorized, bounded consequential decisions qualify. Astra is read-only,
never implements or spawns agents, and never replaces required Sol review. Repeated
consultations require renewed authorization. The gate is a workflow policy and declared-
plan validation, **not a hard token/credit limit**. See the
[Astra contract](plugins/sol-advisor/skills/orchestration/references/astra-advice.md).

## Updating and migration

Windows: rerun the bootstrap with `-Update`; add `-WithAstra` only for an opted-in profile.
POSIX: upgrade the marketplace, add the plugin again, resolve its installed path, and
rerun `install-agents.sh`. Start a fresh task after updating.

~~~sh
codex plugin marketplace upgrade sol-advisor-joserey7
codex plugin add sol-advisor@sol-advisor-joserey7
~~~

Recognized released Luna/Sol profiles migrate safely, including historical Windows CRLF
variants. Exact Terra profiles are archived outside the agents directory. Customized
Terra files are preserved with a warning; review and move them outside discovery manually.
Modified or unsafe selected active profiles are never overwritten. No Codex configuration
is edited. Missing Astra does not block ordinary routes. Read the
[migration and native operations](plugins/sol-advisor/skills/orchestration/references/operations.md)
for archive locations, checks, actual-isolation rules, and partial-update limitations.

## Validate before releasing

~~~sh
sh plugins/sol-advisor/scripts/verify.sh
python3 -m unittest discover -s tests -v
git diff --check
~~~

Portable tests cover migration, runtime privacy, selected roles, and declared authorization.
CI also runs native PowerShell fixtures. Model access, observed sandbox behavior, and
cost per accepted change still require the
[live validation and evaluation checklist](plugins/sol-advisor/skills/orchestration/references/evaluation.md).
No performance or savings claims are implied by passing static tests.

## Credits

Fork of [Daniel McAteer's Sol Advisor](https://github.com/DannyMac180/sol-advisor),
retaining the upstream architect-owned, evidence-based delivery approach. This fork adds
native Windows support and GPT-6 selective delivery with optional authorized Astra advice.
Daniel writes [Attention Heads](https://attentionheads.substack.com/) and the
Agentic Engineering Field Notes series. MIT license; original attribution is retained.
