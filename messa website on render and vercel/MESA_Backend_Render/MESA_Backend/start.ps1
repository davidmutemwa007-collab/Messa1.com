$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) { $pythonExe = "py"; $pythonArgs = @("-3", "app.py") } else {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if (-not $python) { Write-Host "Python 3 is required. Install Python from python.org and select Add Python to PATH." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
  $pythonExe = "python"; $pythonArgs = @("app.py")
}
Write-Host "Starting MESA backend..." -ForegroundColor Cyan
& $pythonExe @pythonArgs
