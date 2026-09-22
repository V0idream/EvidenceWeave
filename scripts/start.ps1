param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
    & $pythonPath -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
    & npm.cmd --prefix frontend ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & npm.cmd --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
}
New-Item -ItemType Directory -Force -Path data/logs | Out-Null
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$ollamaPath = Join-Path $projectRoot 'runtime/ollama/ollama.exe'
if (-not (Test-Path -LiteralPath $ollamaPath)) {
    $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCommand) { $ollamaPath = $ollamaCommand.Source }
}
if (Test-Path -LiteralPath (Join-Path $projectRoot 'runtime/models')) { $env:OLLAMA_MODELS = Join-Path $projectRoot 'runtime/models' }
try { Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null } catch {
    if (Test-Path -LiteralPath $ollamaPath) {
        $ollamaProcess = Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data/logs/ollama.out.log' -RedirectStandardError 'data/logs/ollama.err.log'
        $ollamaProcess.Id | Set-Content 'data/ollama.pid'
    } else { Write-Host 'Ollama is not installed. PDFs can be imported; analysis needs a local model.' }
}
$isRunning = $false
try { $status = Invoke-RestMethod 'http://127.0.0.1:8765/api/system' -TimeoutSec 2; $isRunning = $status.database -eq 'SQLite' -and $status.parser -eq 'PyMuPDF' } catch { }
if (-not $isRunning) {
    $env:PYTHONPATH = Join-Path $projectRoot 'backend'
    $env:PYTHONIOENCODING = 'utf-8'
    $process = Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data/logs/server.out.log' -RedirectStandardError 'data/logs/server.err.log'
    $process.Id | Set-Content 'data/server.pid'
    for ($attempt=0; $attempt -lt 25; $attempt++) {
        Start-Sleep -Milliseconds 400
        try { Invoke-RestMethod 'http://127.0.0.1:8765/api/cases' -TimeoutSec 1 | Out-Null; $isRunning = $true; break } catch { }
        if ($process.HasExited) { break }
    }
    if (-not $isRunning) { throw 'Server did not start. See data/logs/server.err.log.' }
}
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8765' }
Write-Host 'EvidenceWeave is running at http://127.0.0.1:8765'
