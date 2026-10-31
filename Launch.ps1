$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$port = 8765
$url = "http://127.0.0.1:$port"
try {
    $existing = Invoke-RestMethod "$url/api/health" -TimeoutSec 2
    if ($existing.ok -and $existing.version -eq '1.0.0') {
        Start-Process $url
        Write-Host "AlphaGen Workbench is running: $url"
        exit 0
    }
} catch { }
$candidates = @(
    (Join-Path $appRoot '.venv\Scripts\python.exe'),
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
)
$systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($systemPython) { $candidates += $systemPython.Source }
$pythonPath = $null
foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
        & $candidate -c 'import sys,numpy,pandas; assert sys.version_info >= (3,10)' 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonPath = $candidate; break }
    }
}
if (-not $pythonPath) {
    Write-Host 'Python 3.10+ with numpy and pandas is required. Run SETUP.cmd first.'
    exit 1
}
$logDir = Join-Path $appRoot 'data'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$arguments = @(('"' + (Join-Path $appRoot 'app.py') + '"'), '--port', "$port", '--no-browser')
$serverProcess = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'server.log') -RedirectStandardError (Join-Path $logDir 'server-error.log')
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($serverProcess.HasExited) { throw 'Server exited. Check data/server-error.log.' }
    try {
        $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 1
        if ($health.ok) {
            Set-Content -LiteralPath (Join-Path $logDir 'server.pid') -Value $serverProcess.Id
            Start-Process $url
            Write-Host "AlphaGen Workbench started: $url"
            exit 0
        }
    } catch { }
    Start-Sleep -Milliseconds 300
}
throw 'Startup timed out. Check data/server-error.log, or run python app.py --port 8766.'
