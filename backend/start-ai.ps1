$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$runtime = Join-Path $PSScriptRoot 'data\ollama-runtime\ollama.exe'
if (-not (Test-Path -LiteralPath $runtime)) {
    & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'install_portable_ollama.py')
    if ($LASTEXITCODE -ne 0) { throw 'Official Ollama runtime installation failed.' }
}
$env:OLLAMA_MODELS = Join-Path $PSScriptRoot 'data\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
& $runtime serve
