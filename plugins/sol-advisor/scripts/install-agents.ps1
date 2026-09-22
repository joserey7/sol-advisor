#Requires -Version 5.1
<#
.SYNOPSIS
Install core companion roles, or check selected roles without changing anything.
.EXAMPLE
.\install-agents.ps1 -CheckRole luna,sol
.EXAMPLE
.\install-agents.ps1 -WithAstra
#>
[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()][string] $TargetDir,
    [switch] $Check,
    [switch] $WithAstra,
    [ValidateSet('luna', 'sol-implementer', 'sol', 'astra')][string[]] $CheckRole
)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'python-common.ps1')
    $python = Get-SolAdvisorPython
    $prefix = @($python.Prefix)
    $arguments = @('install')
    if ($PSBoundParameters.ContainsKey('TargetDir')) { $arguments += @('--target-dir', $TargetDir) }
    if ($Check) { $arguments += '--check' }
    if ($WithAstra) { $arguments += '--with-astra' }
    foreach ($role in $CheckRole) { $arguments += @('--check-role', $role) }
    & $python.Executable @prefix (Join-Path $PSScriptRoot 'native-support.py') @arguments
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('ERROR: ' + $_.Exception.Message)
    exit 1
}
