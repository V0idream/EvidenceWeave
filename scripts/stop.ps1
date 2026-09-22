$projectRoot = Split-Path -Parent $PSScriptRoot
foreach ($serviceName in @('server','ollama')) {
    $pidFile = Join-Path $projectRoot "data/$serviceName.pid"
    if (Test-Path -LiteralPath $pidFile) {
        $serviceId = [int](Get-Content -LiteralPath $pidFile)
        $serviceProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$serviceId" -ErrorAction SilentlyContinue
        if ($serviceProcess -and $serviceProcess.ExecutablePath -and $serviceProcess.ExecutablePath.StartsWith($projectRoot,[System.StringComparison]::OrdinalIgnoreCase)) {
            Stop-Process -Id $serviceId -ErrorAction SilentlyContinue
        }
    }
}
