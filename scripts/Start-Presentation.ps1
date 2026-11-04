param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $projectRoot 'state'
New-Item -ItemType Directory -Path $statePath -Force | Out-Null

function Test-ServiceUrl([string]$Url) {
    try { $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3; return $true }
    catch { return $false }
}

$pythonCandidates = @()
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) { $pythonCandidates += $pythonCommand.Source }
$pythonCandidates += Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA 'Python') -Directory -ErrorAction SilentlyContinue | ForEach-Object { Join-Path $_.FullName 'python.exe' } | Where-Object { Test-Path -LiteralPath $_ }
$pythonPath = $null
foreach ($candidate in $pythonCandidates) {
    try { & $candidate -c 'import fastapi,httpx,pypdf,uvicorn' 2>$null; if ($LASTEXITCODE -eq 0) { $pythonPath=$candidate; break } }
    catch { }
}
if (-not $pythonPath) { throw 'ไม่พบ Python ที่ติดตั้ง dependencies โปรดติดตั้ง backend/requirements.txt ก่อน' }

if (-not (Test-ServiceUrl 'http://127.0.0.1:11434/api/version')) {
    $ollamaPath = (Get-Command ollama -ErrorAction Stop).Source
    Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden
}
if (-not $env:BGT_ASSISTANT_MODEL) { $env:BGT_ASSISTANT_MODEL='qwen3.5:4b' }
if (-not (Test-ServiceUrl 'http://127.0.0.1:8000/api/health')) {
    if (-not $env:BGT_ADMIN_PASSWORD) {
        $secret = Read-Host 'ตั้งรหัสผ่านผู้ดูแลสำหรับการเปิด Backend ครั้งนี้' -AsSecureString
        $env:BGT_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', $secret).Password
        if (-not $env:BGT_ADMIN_PASSWORD) { throw 'กรุณาตั้งรหัสผ่านผู้ดูแล' }
    }
    Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $statePath 'backend-presentation.log') -RedirectStandardError (Join-Path $statePath 'backend-presentation-error.log')
}
if (-not (Test-ServiceUrl 'http://127.0.0.1:5500')) {
    Start-Process -FilePath $pythonPath -ArgumentList @('-m','http.server','5500','--bind','127.0.0.1','--directory','Code') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $statePath 'frontend-presentation.log') -RedirectStandardError (Join-Path $statePath 'frontend-presentation-error.log')
}
for ($attempt=0; $attempt -lt 10; $attempt++) {
    if ((Test-ServiceUrl 'http://127.0.0.1:8000/api/health') -and (Test-ServiceUrl 'http://127.0.0.1:5500')) { break }
    Start-Sleep -Milliseconds 500
}
Push-Location $projectRoot
try { & $pythonPath -X utf8 (Join-Path $PSScriptRoot 'presentation_check.py') }
finally { Pop-Location }
if ($OpenBrowser) { Start-Process 'http://127.0.0.1:5500' }
Write-Host 'เปิดเว็บที่ http://127.0.0.1:5500 แล้วกด Ctrl+F5 ก่อนเริ่มสาธิต'
Write-Host 'ถ้ามี Backend เดิมเปิดอยู่ สคริปต์จะใช้บริการเดิม กรุณาตรวจว่าเป็นโค้ดล่าสุด'
