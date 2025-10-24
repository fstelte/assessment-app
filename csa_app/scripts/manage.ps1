<#
.SYNOPSIS
  Convenience wrapper for common project tasks (development run, tests, imports, migrations).
.DESCRIPTION
  Use this script to execute Poetry-backed commands without remembering the full syntax. Example:
    ./scripts/manage.ps1 run
    ./scripts/manage.ps1 test --Coverage
    ./scripts/manage.ps1 import -ImportPath data/controls.json
.PARAMETER Task
  The task to execute. Supported values: run, test, import, upgrade, lint.
.PARAMETER ImportPath
  Path to the control JSON file when running the import task.
.PARAMETER Coverage
  Switch to run tests with coverage enabled.
#>
[CmdletBinding(DefaultParameterSetName = 'Task')]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('run', 'test', 'import', 'upgrade', 'lint')]
    [string]$Task,

    [Parameter(ParameterSetName = 'Task')]
    [string]$ImportPath = 'iso_27002_controls.json',

    [Parameter(ParameterSetName = 'Task')]
    [switch]$Coverage
)

function Invoke-PoetryCommand {
    param(
        [string[]]$Arguments
    )

    Write-Host "→ poetry $($Arguments -join ' ')" -ForegroundColor Cyan
    poetry @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE."
    }
}

switch ($Task) {
    'run' {
        Invoke-PoetryCommand -Arguments @('run', 'flask', '--app', 'autoapp', '--debug', 'run')
    }
    'test' {
        if ($Coverage) {
            Invoke-PoetryCommand -Arguments @('run', 'pytest', '--cov=app', '--cov-report=term-missing')
        }
        else {
            Invoke-PoetryCommand -Arguments @('run', 'pytest')
        }
    }
    'import' {
        Invoke-PoetryCommand -Arguments @('run', 'flask', '--app', 'autoapp', 'import-controls', $ImportPath)
    }
    'upgrade' {
        Invoke-PoetryCommand -Arguments @('run', 'flask', '--app', 'autoapp', 'db', 'upgrade')
    }
    'lint' {
        Invoke-PoetryCommand -Arguments @('run', 'tox', '-e', 'lint')
    }
    default {
        throw "Unsupported task: $Task"
    }
}
