# Define the task details
$TaskName = "PlayhubEventFinder"
$BatchPath = Join-Path $PSScriptRoot "run_weekly.bat"

Write-Host "Scheduling weekly task to run: $BatchPath" -ForegroundColor Cyan

# Create the weekly scheduled task in Windows Task Scheduler
# Scheduled to run every Sunday (/d SUN) at 10:00 AM (/st 10:00)
# /f overrides the task if it already exists
schtasks /create /tn $TaskName /tr "`"$BatchPath`"" /sc weekly /d SUN /st 10:00 /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Scheduled task '$TaskName' registered successfully!" -ForegroundColor Green
    Write-Host "The script will run automatically every Sunday at 10:00 AM." -ForegroundColor Green
    Write-Host "You can open or refresh your HTML report at any time:" -ForegroundColor Yellow
    Write-Host "File URL: file:///C:/Users/Thomas/playhub-event-finder/index.html" -ForegroundColor Yellow
} else {
    Write-Error "Failed to register scheduled task. Please make sure you are running this PowerShell window as Administrator."
}
