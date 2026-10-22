[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
Push-Location $projectPath
try {
    $pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
    & $pythonPath -m ruff check apps/backend
    if ($LASTEXITCODE -ne 0) { throw 'Lint checks failed.' }
    & $pythonPath -m mypy
    if ($LASTEXITCODE -ne 0) { throw 'Type checks failed.' }
    & $pythonPath -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
    & (Join-Path $PSScriptRoot 'build-web.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
} finally { Pop-Location }
