# Start both CRBot servers
Write-Host "Starting CRBot servers..." -ForegroundColor Green

# Start FastAPI backend
$backendProcess = Start-Process -FilePath "C:/CRBot/.venv/Scripts/python.exe" `
  -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload" `
  -WorkingDirectory "c:\CRBot\backend" `
  -NoNewWindow -PassThru

# Start HTTP frontend
$frontendProcess = Start-Process -FilePath "C:/CRBot/.venv/Scripts/python.exe" `
  -ArgumentList "-m http.server 3000" `
  -WorkingDirectory "c:\CRBot\frontend" `
  -NoNewWindow -PassThru

Write-Host "✓ API running on http://127.0.0.1:8002" -ForegroundColor Green
Write-Host "✓ Frontend running on http://localhost:3000" -ForegroundColor Green
Write-Host "✓ Open http://localhost:3000/dashboard-pro.html" -ForegroundColor Cyan
Write-Host "`nPress CTRL+C to stop both servers" -ForegroundColor Yellow

# Wait for processes
$backendProcess | Wait-Process
$frontendProcess | Wait-Process
