#Requires -Version 5.1
<#
.SYNOPSIS
Read one exact native thread and emit only allowlisted routing metadata as JSON.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$')]
    [string] $ThreadId,
    [ValidateNotNullOrEmpty()][string] $SessionsDir,
    [switch] $ExpectPrimary
)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'python-common.ps1')
    $python = Get-SolAdvisorPython
    $prefix = @($python.Prefix)
    $arguments = @('inspect')
    if ($PSBoundParameters.ContainsKey('SessionsDir')) { $arguments += @('--sessions-dir', $SessionsDir) }
    if ($ExpectPrimary) { $arguments += '--expect-primary' }
    $arguments += $ThreadId
    & $python.Executable @prefix (Join-Path $PSScriptRoot 'native-support.py') @arguments
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('ERROR: ' + $_.Exception.Message)
    exit 1
}
