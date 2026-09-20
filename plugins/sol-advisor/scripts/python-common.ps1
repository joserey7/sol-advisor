#Requires -Version 5.1
# Shared interpreter discovery. Dot-source from an entry point; no global policy edits.
function Get-SolAdvisorPython {
    foreach ($name in @('python', 'py', 'python3')) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $command) { continue }
        $prefix = @()
        if ($name -eq 'py') { $prefix = @('-3') }
        try {
            & $command.Source @prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' *> $null
            if ($LASTEXITCODE -eq 0) {
                return @{ Executable = $command.Source; Prefix = $prefix }
            }
        } catch { continue }
    }
    throw 'Python 3.11+ is required. Install native Python with its launcher or add it to PATH; no Bash, WSL, or jq is needed.'
}
