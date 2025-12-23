Set-Location "$PSScriptRoot\backend"
& "..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host localhost --port 8002 --reload