# First run: creates .venv and installs deps. Later runs: start server only (no reinstall).
# Prefers real python.org install over Microsoft Store stub (WindowsApps).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-PythonExe {
    $root = Join-Path $env:LOCALAPPDATA "Programs\Python"
    if (Test-Path $root) {
        $best = Get-ChildItem "$root\Python*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object {
            $name = $_.Directory.Name
            if ($name -match '^Python(\d)(\d+)$') {
                [PSCustomObject]@{
                    Path = $_.FullName
                    Ver  = [version]"$($matches[1]).$($matches[2])"
                }
            }
        } | Sort-Object Ver -Descending | Select-Object -First 1
        if ($best) { return $best.Path }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and ($cmd.Source -notmatch 'WindowsApps') -and (Test-Path $cmd.Source)) {
        return $cmd.Source
    }
    if (Get-Command py -ErrorAction SilentlyContinue) { return "py" }
    return $null
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv (first time only)..."

    $pythonExe = Get-PythonExe
    if (-not $pythonExe) {
        Write-Host "ERROR: Python not found. Install from https://www.python.org/downloads/"
        Write-Host "       or: winget install Python.Python.3.12"
        exit 1
    }

    if ($pythonExe -eq "py") {
        & py -m venv .venv
    }
    else {
        & $pythonExe -m venv .venv
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "ERROR: Could not create .venv."
        Write-Host "       Delete the .venv folder if it exists, then run this script again."
        exit 1
    }

    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

Write-Host "Open http://127.0.0.1:8000 in browser (not localhost if you see connection refused). Ctrl+C to stop."
& $venvPython -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
