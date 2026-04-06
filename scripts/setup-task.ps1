# InSighTube Task Scheduler registration script
# Requires administrator privileges.
#
# Usage:
#   .\scripts\setup-task.ps1              # Register task
#   .\scripts\setup-task.ps1 -Unregister  # Unregister task

param(
    [switch]$Unregister
)

$TaskName = "InSighTube-Server"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VbsLauncher = Join-Path $ProjectRoot "scripts\start-server.vbs"

# --- 해제 모드 ---
if ($Unregister) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[OK] Task '$TaskName' unregistered." -ForegroundColor Green
    } else {
        Write-Host "[INFO] No registered task '$TaskName' found." -ForegroundColor Yellow
    }
    exit 0
}

# --- 등록 모드 ---

# 이미 등록된 작업이 있으면 먼저 제거
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[INFO] Removing existing task before re-registering."
}

$Action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$VbsLauncher`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "InSighTube FastAPI server auto-start" | Out-Null

Write-Host "[OK] Task '$TaskName' registered." -ForegroundColor Green
Write-Host "  - Trigger: At user logon ($env:USERNAME)" -ForegroundColor Cyan
Write-Host "  - Launcher: $VbsLauncher" -ForegroundColor Cyan
Write-Host "  - Restart: up to 3 retries, 1 min interval" -ForegroundColor Cyan
