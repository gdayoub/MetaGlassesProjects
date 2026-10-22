[CmdletBinding()]
param([ValidateRange(1024,65535)][int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
Push-Location $projectPath
try {
    $pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run .\scripts\setup.ps1 first.' }
    if (-not (Test-Path -LiteralPath '.env')) { throw 'Run setup to create your private .env file.' }
    if (-not (Test-Path -LiteralPath 'apps\web\dist\index.html')) { throw 'Run .\scripts\build-web.ps1 first.' }
    $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if ($listeners | Where-Object Port -EQ $Port) { throw "Port $Port is already in use. Stop the existing server before starting LensAgent again." }
    Write-Host "LensAgent: http://127.0.0.1:$Port (Ctrl+C to stop)"
    # Windows PowerShell can wrap native stderr (including Uvicorn INFO logs)
    # as NativeCommandError. Keep logs visible and use the actual exit code.
    $previousErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $pythonPath -m uvicorn lensagent.api:create_app --factory --host 127.0.0.1 --port $Port --no-access-log
        $serverExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
    }
    if ($serverExitCode -ne 0) { throw 'LensAgent stopped with an error. See the error above.' }
} finally { Pop-Location }
