#Requires -Version 5.1
<#
.SYNOPSIS
Install exact companion roles, or check selected roles without changing anything.
.EXAMPLE
.\install-agents.ps1 -CheckRole luna,sol
#>
[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()][string] $TargetDir,
    [switch] $Check,
    [ValidateSet('luna', 'terra', 'sol')][string[]] $CheckRole
)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'python-common.ps1')
    $python = Get-SolAdvisorPython
    $prefix = @($python.Prefix)
    $arguments = @('install')
    if ($PSBoundParameters.ContainsKey('TargetDir')) { $arguments += @('--target-dir', $TargetDir) }
    if ($Check) { $arguments += '--check' }
    foreach ($role in $CheckRole) { $arguments += @('--check-role', $role) }
    & $python.Executable @prefix (Join-Path $PSScriptRoot 'native-support.py') @arguments
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('ERROR: ' + $_.Exception.Message)
    exit 1
}
