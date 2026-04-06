# InSighTube server start script
# Called by Windows Task Scheduler.
# Automatically restarts the server on crash (max 10 consecutive failures).

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$LogFile = Join-Path $ProjectRoot "logs\server.log"
$RestartDelaySec = 5
$MaxConsecutiveFailures = 10

# Log directory
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Working directory
Set-Location $ProjectRoot

$failures = 0

while ($failures -lt $MaxConsecutiveFailures) {
    $startTime = Get-Date
    "[$startTime] Server starting..." *>> $LogFile

    & $VenvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 *>> $LogFile

    $exitCode = $LASTEXITCODE
    $endTime = Get-Date
    $uptime = ($endTime - $startTime).TotalSeconds

    "[$endTime] Server exited (code=$exitCode, uptime=${uptime}s)" *>> $LogFile

    # If server ran for more than 60s, reset failure counter
    if ($uptime -gt 60) {
        $failures = 0
    } else {
        $failures++
    }

    if ($failures -lt $MaxConsecutiveFailures) {
        "[$endTime] Restarting in ${RestartDelaySec}s... (consecutive failures: $failures/$MaxConsecutiveFailures)" *>> $LogFile
        Start-Sleep -Seconds $RestartDelaySec
    }
}

"[$(Get-Date)] Max consecutive failures reached ($MaxConsecutiveFailures). Stopping." *>> $LogFile
