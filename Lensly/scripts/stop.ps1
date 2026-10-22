[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
$processes = Get-CimInstance Win32_Process
$servers = $processes | Where-Object {
    $_.ExecutablePath -eq $pythonPath -and $_.CommandLine -match 'lensagent\.api:create_app'
}
if (-not $servers) { Write-Host 'No LensAgent server is running for this project.' }
foreach ($serverProcess in $servers) {
    # Windows venv Python can launch the base interpreter as a child process.
    $children = $processes | Where-Object {
        $_.ParentProcessId -eq $serverProcess.ProcessId -and
        $_.Name -match '^python' -and $_.CommandLine -match 'lensagent\.api:create_app'
    }
    if ($children) {
        foreach ($childProcess in $children) { Stop-Process -Id $childProcess.ProcessId }
    } else { Stop-Process -Id $serverProcess.ProcessId }
    Write-Host "Stopped LensAgent server $($serverProcess.ProcessId)."
}
