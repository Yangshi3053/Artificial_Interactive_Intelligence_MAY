param(
    [string]$CosyVoicePath = "C:\Projects\bigProjects\CosyVoice",
    [string]$CondaPython = "C:\Users\20831\miniconda3\envs\cosyvoice\python.exe",
    [int]$Port = 50000,
    [string]$ModelDir = "iic/CosyVoice-300M",
    [switch]$UseCuda
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CosyVoicePath)) {
    throw "CosyVoice folder was not found: $CosyVoicePath"
}

if (-not (Test-Path -LiteralPath $CondaPython)) {
    throw "CosyVoice Python was not found: $CondaPython"
}

$logPath = Join-Path $CosyVoicePath "cosyvoice_server.log"

if ($UseCuda) {
    Remove-Item Env:CUDA_VISIBLE_DEVICES -ErrorAction SilentlyContinue
} else {
    $env:CUDA_VISIBLE_DEVICES = ""
}

Write-Host "Starting CosyVoice..."
Write-Host "Folder: $CosyVoicePath"
Write-Host "Port: $Port"
Write-Host "Model: $ModelDir"
Write-Host "Log: $logPath"

Set-Location $CosyVoicePath
& $CondaPython runtime\python\fastapi\server.py --port $Port --model_dir $ModelDir
