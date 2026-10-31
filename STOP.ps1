$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'data\server.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'No launcher-managed server PID found.'; exit }
$serverProcessId = [int](Get-Content -LiteralPath $pidFile)
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$serverProcessId" -ErrorAction SilentlyContinue
$appFile = Join-Path $PSScriptRoot 'app.py'
if ($process -and $process.CommandLine -and $process.CommandLine.Contains($appFile)) {
    Stop-Process -Id $serverProcessId
    Remove-Item -LiteralPath $pidFile
    Write-Host 'AlphaGen Workbench stopped.'
} else { Write-Host 'Process no longer matches this workbench; no process was stopped.' }
