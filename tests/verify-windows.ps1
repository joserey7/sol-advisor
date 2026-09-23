#Requires -Version 5.1
# Run under BOTH powershell.exe (5.1) and pwsh.exe (7) in CI.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0
$repo = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $repo 'plugins/sol-advisor/scripts'
$engine = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $engine)) { $engine = Join-Path $PSHOME 'pwsh.exe' }
$temp = Join-Path ([IO.Path]::GetTempPath()) ('sol advisor [test] ' + [guid]::NewGuid())
[IO.Directory]::CreateDirectory($temp) | Out-Null
$previous = @{}
foreach ($key in @('CODEX_HOME', 'FAKE_BUNDLE', 'FAKE_LOG', 'FAKE_MODE', 'FAKE_PYTHON')) {
    $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
function Assert-True($Condition, [string] $Message) {
    if (-not $Condition) { throw $Message }
}
function Run-Script([string] $Path, [string[]] $Arguments, [bool] $Success) {
    # PS 5.1 redirects native stderr as ErrorRecords; use exit codes for failures.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $engine -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Path @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($Success -ne ($code -eq 0)) { throw ('Unexpected exit code ' + $code + ': ' + ($output -join "`n")) }
    return ($output -join "`n")
}
try {
    Get-ChildItem -LiteralPath $repo -Recurse -Filter '*.ps1' | ForEach-Object {
        $tokens = $null; $errors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors)
        Assert-True ($errors.Count -eq 0) ('PowerShell syntax error: ' + $_.FullName)
    }
    $env:CODEX_HOME = Join-Path $temp 'native home'
    $installer = Join-Path $scripts 'install-agents.ps1'
    $null = Run-Script $installer @() $true
    $null = Run-Script $installer @('-Check') $true
    $agents = Join-Path $env:CODEX_HOME 'agents'
    $astra = Join-Path $agents 'sol-advisor-astra-advisor.toml'
    Assert-True (-not (Test-Path -LiteralPath $astra)) 'Core installation enabled Astra.'
    $null = Run-Script $installer @('-CheckRole', 'astra') $false
    $null = Run-Script $installer @('-WithAstra') $true
    $null = Run-Script $installer @('-CheckRole', 'astra') $true
    Remove-Item -LiteralPath $astra
    $null = Run-Script $installer @('-Check') $true
    Remove-Item -LiteralPath (Join-Path $agents 'sol-advisor-sol-implementer.toml')
    $null = Run-Script $installer @('-CheckRole', 'luna') $true
    $null = Run-Script $installer @('-Check') $false
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $agents 'sol-advisor-sol-implementer.toml'))) 'Check recreated a missing role.'
    $null = Run-Script $installer @('-CheckRole', 'unknown') $false
    $null = Run-Script $installer @('-CheckRole', 'terra') $false

    $thread = '00000000-0000-0000-0000-000000000001'
    $sessions = Join-Path $temp 'sessions'
    [IO.Directory]::CreateDirectory($sessions) | Out-Null
    $rows = @(
        '{"type":"session_meta","payload":{"id":"00000000-0000-0000-0000-000000000001","agent_role":"sol_advisor_luna_implementer","prompt":"PRIVATE_SENTINEL"}}',
        '{"type":"turn_context","payload":{"model":"gpt-6-luna","effort":"max","cwd":"C:/project"}}'
    )
    [IO.File]::WriteAllText((Join-Path $sessions ('rollout-test-' + $thread + '.jsonl')), ($rows -join "`n"), [Text.UTF8Encoding]::new($false))
    $result = Run-Script (Join-Path $scripts 'inspect-agent-runtime.ps1') @('-SessionsDir', $sessions, '-ThreadId', $thread) $true
    Assert-True (-not $result.Contains('PRIVATE_SENTINEL')) 'Runtime output leaked private data.'
    Assert-True (($result | ConvertFrom-Json).effort -ceq 'max') 'Runtime wrapper lost metadata.'

    # Mock the CLI only: no authentication, model calls, or real home writes.
    . (Join-Path $scripts 'python-common.ps1')
    $python = Get-SolAdvisorPython
    $prefix = @($python.Prefix)
    $env:FAKE_PYTHON = (& $python.Executable @prefix -c 'import sys; print(sys.executable)')
    $env:FAKE_LOG = Join-Path $temp 'cli.jsonl'
    $env:FAKE_BUNDLE = Join-Path $temp 'cached plugin'
    Copy-Item -LiteralPath (Join-Path $repo 'plugins/sol-advisor') -Destination $env:FAKE_BUNDLE -Recurse
    $cachedLuna = Join-Path $env:FAKE_BUNDLE 'agents/sol-advisor-luna-implementer.toml'
    [IO.File]::AppendAllText($cachedLuna, "`n# cache-only fixture`n", [Text.UTF8Encoding]::new($false))
    $fakePy = Join-Path $temp 'fake-cli.py'
    $fakeSource = @'
import json, os, sys
args = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a', encoding='utf-8') as stream:
    stream.write(json.dumps(args) + '\n')
mode = os.environ.get('FAKE_MODE', '')
if mode == 'fail-register' and args[:3] == ['plugin', 'marketplace', 'add']:
    sys.exit(17)
if mode == 'fail-install' and args[:2] == ['plugin', 'add']:
    sys.exit(17)
if args == ['plugin', 'list', '--json']:
    if mode == 'bad-json':
        print('invalid JSON')
    else:
        entry = {'pluginId': 'sol-advisor@sol-advisor-joserey7', 'source': {'path': os.environ['FAKE_BUNDLE']}}
        installed = [] if mode == 'missing' else [entry, entry] if mode == 'duplicate' else [entry]
        print(json.dumps({'installed': installed}))
'@
    [IO.File]::WriteAllText($fakePy, $fakeSource, [Text.UTF8Encoding]::new($false))
    $fakeCmd = Join-Path $temp 'fake codex.cmd'
    [IO.File]::WriteAllText($fakeCmd, "@echo off`r`n`"%FAKE_PYTHON%`" `"%~dp0fake-cli.py`" %*`r`nexit /b %errorlevel%`r`n", [Text.UTF8Encoding]::new($false))
    $bootstrap = Join-Path $repo 'scripts/install-plugin.ps1'
    foreach ($mode in @('fail-register', 'fail-install', 'bad-json', 'missing', 'duplicate')) {
        $env:FAKE_MODE = $mode
        $env:CODEX_HOME = Join-Path $temp $mode
        $null = Run-Script $bootstrap @('-CodexCommand', $fakeCmd) $false
        Assert-True (-not (Test-Path -LiteralPath (Join-Path $env:CODEX_HOME 'agents'))) ('Failure installed agents: ' + $mode)
    }
    $env:FAKE_MODE = 'ok'
    $env:CODEX_HOME = Join-Path $temp 'bootstrap success'
    $sourcePath = Join-Path $temp 'marketplace with spaces [literal]'
    $null = Run-Script $bootstrap @('-CodexCommand', $fakeCmd, '-Source', $sourcePath) $true
    $installedLuna = Join-Path $env:CODEX_HOME 'agents/sol-advisor-luna-implementer.toml'
    Assert-True ((Get-FileHash -LiteralPath $cachedLuna).Hash -ceq (Get-FileHash -LiteralPath $installedLuna).Hash) 'Bootstrap did not use the installed cache templates.'
    $calls = @(Get-Content -LiteralPath $env:FAKE_LOG | ForEach-Object { ,(ConvertFrom-Json $_) })
    Assert-True (@($calls | Where-Object { $_.Count -eq 4 -and $_[0] -eq 'plugin' -and $_[2] -eq 'add' -and $_[3] -ceq $sourcePath }).Count -eq 1) 'Source path argument was corrupted.'
    $null = Run-Script $bootstrap @('-CodexCommand', $fakeCmd, '-Update') $true
    $installedAstra = Join-Path $env:CODEX_HOME 'agents/sol-advisor-astra-advisor.toml'
    Assert-True (-not (Test-Path -LiteralPath $installedAstra)) 'Bootstrap installed Astra without opt-in.'
    $null = Run-Script $bootstrap @('-CodexCommand', $fakeCmd, '-Update', '-WithAstra') $true
    Assert-True (Test-Path -LiteralPath $installedAstra -PathType Leaf) 'Bootstrap lost the explicit Astra opt-in.'
    Write-Output ('WINDOWS VERIFY PASSED: PowerShell ' + $PSVersionTable.PSVersion)
} finally {
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
