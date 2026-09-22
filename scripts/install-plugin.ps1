#Requires -Version 5.1
<#
.SYNOPSIS
Register this fork as a Codex plugin and install the companion native agents.
.DESCRIPTION
Requires a current native Codex CLI and Python 3.11+. Defaults to this checkout,
not the current working directory. Does not modify model/sandbox settings or
execution policy. Use the same CODEX_HOME as Codex Desktop, then start a new task.
-WithAstra installs the optional profile, not permission to use it.
.EXAMPLE
.\scripts\install-plugin.ps1
.EXAMPLE
.\scripts\install-plugin.ps1 -Source joserey7/sol-advisor -Ref main
.EXAMPLE
.\scripts\install-plugin.ps1 -Update -WithAstra
#>
[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()][string] $Source,
    [ValidateNotNullOrEmpty()][string] $Ref,
    [switch] $Update,
    [switch] $WithAstra,
    [ValidateNotNullOrEmpty()][string] $CodexCommand
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0
$marketplace = 'sol-advisor-joserey7'
$pluginId = 'sol-advisor@' + $marketplace
try {
    if ($Update -and ($PSBoundParameters.ContainsKey('Source') -or $PSBoundParameters.ContainsKey('Ref'))) {
        throw '-Update cannot be combined with -Source or -Ref.'
    }
    $repo = Split-Path -Parent $PSScriptRoot
    . (Join-Path $repo 'plugins/sol-advisor/scripts/python-common.ps1')
    $python = Get-SolAdvisorPython # Check prerequisites before registering anything.
    $prefix = @($python.Prefix)
    if (-not $CodexCommand) {
        # Prefer the native executable/npm CMD shim over an execution-policy-sensitive PS1 shim.
        foreach ($name in @('codex.exe', 'codex.cmd', 'codex')) {
            $candidate = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($null -ne $candidate) { $CodexCommand = $candidate.Source; break }
        }
    }
    if (-not $CodexCommand) { throw 'Codex CLI was not found. Install the native CLI or supply -CodexCommand with its executable path.' }
    if ($Update) {
        & $CodexCommand plugin marketplace upgrade $marketplace
    } else {
        if (-not $Source) { $Source = $repo }
        $registration = @('plugin', 'marketplace', 'add', $Source)
        if ($Ref) { $registration += @('--ref', $Ref) }
        & $CodexCommand @registration
    }
    if ($LASTEXITCODE -ne 0) { throw 'Marketplace registration/update failed. Companion agents were not changed.' }
    & $CodexCommand plugin add $pluginId
    if ($LASTEXITCODE -ne 0) { throw 'Plugin installation failed. Companion agents were not changed.' }
    $raw = & $CodexCommand plugin list --json
    if ($LASTEXITCODE -ne 0) { throw 'Could not query installed plugins. Companion agents were not changed.' }
    $listing = ($raw -join "`n") | ConvertFrom-Json
    $installed = @($listing.installed | Where-Object { $_.pluginId -ceq $pluginId })
    if ($installed.Count -ne 1) { throw 'Expected exactly one installed plugin for this fork.' }
    $pluginPath = $installed[0].source.path
    if ([string]::IsNullOrWhiteSpace($pluginPath) -or -not (Test-Path -LiteralPath $pluginPath -PathType Container)) {
        throw 'Installed plugin source.path is missing or is not a directory.'
    }
    $manifestPath = Join-Path $pluginPath '.codex-plugin/plugin.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.repository -cne 'https://github.com/joserey7/sol-advisor') {
        throw 'Installed plugin does not identify this fork. Refusing to run its companion installer.'
    }
    $helper = Join-Path $pluginPath 'scripts/native-support.py'
    if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) { throw 'Installed plugin is missing its shell-free companion installer.' }
    # Use the installed bundle, not potentially different templates in this checkout.
    $installArguments = @('install')
    if ($WithAstra) { $installArguments += '--with-astra' }
    & $python.Executable @prefix $helper @installArguments
    if ($LASTEXITCODE -ne 0) { throw 'Plugin is registered, but companion installation failed. Resolve the reported conflict; do not overwrite customized files blindly.' }
    Write-Output 'PLUGIN INSTALL PASSED. Restart Codex Desktop and start a NEW task; select GPT-6 Sol / xhigh in the primary session.'
    exit 0
} catch {
    [Console]::Error.WriteLine('ERROR: ' + $_.Exception.Message)
    exit 1
}
