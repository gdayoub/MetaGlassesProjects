[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$pnpmCommand = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if (-not $pnpmCommand) { $pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue }
$bundledPnpm = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
if ($pnpmCommand) { $pnpmPath = $pnpmCommand.Source }
elseif (Test-Path -LiteralPath $bundledPnpm) { $pnpmPath = $bundledPnpm }
else { throw 'Install Node.js 22+ and pnpm 11, then rerun this script.' }
Push-Location (Join-Path $projectPath 'apps\web')
try {
    & $pnpmPath install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Web dependency installation failed.' }
    & $pnpmPath run build
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript build failed.' }
} finally { Pop-Location }
