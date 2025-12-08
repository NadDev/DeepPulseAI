#!/bin/bash
# Start both API and Frontend servers

echo "Starting CRBot servers..."

# Start FastAPI backend
cd /c/CRBot/backend
/c/CRBot/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload &
API_PID=$!

# Start HTTP frontend
cd /c/CRBot/frontend
/c/CRBot/.venv/Scripts/python.exe -m http.server 3000 &
HTTP_PID=$!

echo "API running on http://127.0.0.1:8002 (PID: $API_PID)"
echo "Frontend running on http://localhost:3000 (PID: $HTTP_PID)"
echo "Press CTRL+C to stop both servers"

# Wait for signals
wait
