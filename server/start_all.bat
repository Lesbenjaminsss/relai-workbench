@echo off
cd /d "%~dp0"

echo [*] Ollama kontrol ediliyor...
where ollama >nul 2>&1
if %errorlevel%==0 (
  powershell -NoProfile -Command "try { Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 2 | Out-Null; Write-Host '[+] Ollama zaten calisiyor' } catch { Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden; Write-Host '[+] Ollama baslatildi' }"
) else (
  echo [!] Ollama bulunamadi. Lutfen kurun: https://ollama.com/download
)

echo [*] AI Server baslatiliyor: http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
