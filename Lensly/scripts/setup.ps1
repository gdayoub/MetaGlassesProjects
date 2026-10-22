[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
Push-Location $projectPath
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and rerun setup.'
    }
    & uv sync --frozen --extra dev --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    if (-not (Test-Path -LiteralPath '.env')) {
        $configText = Get-Content -LiteralPath '.env.example' -Raw
        $randomBytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
        $accessToken = [BitConverter]::ToString($randomBytes).Replace('-', '').ToLowerInvariant()
        $configText = $configText.Replace('LENSAGENT_API_TOKEN=', "LENSAGENT_API_TOKEN=$accessToken")
        [IO.File]::WriteAllText((Join-Path $projectPath '.env'), $configText)
        Write-Host 'Created a private .env file with a random access token. Existing .env files are preserved.'
    }
    & (Join-Path $PSScriptRoot 'build-web.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
    Write-Host 'Setup complete. Run .\scripts\start.ps1, then open http://127.0.0.1:8765.'
    Write-Host 'Paste LENSAGENT_API_TOKEN from .env into the connection screen. AI providers start disabled.'
} finally { Pop-Location }
