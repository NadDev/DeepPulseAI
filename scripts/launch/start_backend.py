#!/usr/bin/env python
"""
CRBot Backend Server Launcher
Lance le serveur FastAPI sur le port 8002
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Déterminer le chemin du projet (remonter 2 niveaux depuis scripts/launch)
    script_dir = Path(__file__).parent.parent.parent.absolute()
    backend_dir = script_dir / "backend"
    venv_python = script_dir / ".venv" / "Scripts" / "python.exe"
    
    print("=" * 60)
    print("CRBot - Backend Server Launcher")
    print("=" * 60)
    print(f"\nBackend Directory: {backend_dir}")
    print(f"Python Interpreter: {venv_python}")
    
    # Vérifier que le répertoire backend existe
    if not backend_dir.exists():
        print("\n[ERROR] Backend directory not found!")
        sys.exit(1)
    
    # Vérifier que le venv Python existe
    if not venv_python.exists():
        print("\n[ERROR] Python virtual environment not found!")
        print(f"Expected: {venv_python}")
        sys.exit(1)
    
    print("[INFO] Starting FastAPI server...")
    print("[INFO] Server will run on http://localhost:8002")
    print("[INFO] Press CTRL+C to stop the server\n")
    
    # Lancer le serveur
    try:
        # Create a real subprocess that doesn't close immediately
        process = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "app.main:app", 
             "--host", "localhost", "--port", "8002"],
            cwd=str(backend_dir),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Wait for process to complete
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n[INFO] Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
