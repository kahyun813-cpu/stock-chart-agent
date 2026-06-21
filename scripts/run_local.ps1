$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root "venv\Scripts\python.exe"
$BackendUrl = "http://127.0.0.1:8000"
$FrontendUrl = "http://127.0.0.1:8501"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual environment not found. Run: python -m venv venv; .\venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Set-Location $Root
$env:BACKEND_URL = $BackendUrl
$env:LANGCHAIN_TRACING_V2 = "false"

function Test-Backend {
    try {
        Invoke-WebRequest -Uri "$BackendUrl/health" -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

$backendProcess = $null

if (Test-Backend) {
    Write-Host "Backend already running at $BackendUrl"
}
else {
    Write-Host "Starting FastAPI backend at $BackendUrl ..."
    $backendProcess = Start-Process `
        -FilePath $Python `
        -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -PassThru

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-Backend) {
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not (Test-Backend)) {
        if ($backendProcess) {
            Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Error "Backend did not start successfully."
    }
}

Write-Host "Starting Streamlit frontend at $FrontendUrl ..."
Write-Host "Open: $FrontendUrl"
Start-Process $FrontendUrl

try {
    & $Python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
}
finally {
    if ($backendProcess) {
        Write-Host "Stopping FastAPI backend process ..."
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
