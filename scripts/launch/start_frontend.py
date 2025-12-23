#!/usr/bin/env python
"""
CRBot Frontend Server Launcher
Lance le serveur Vite pour le développement React
Port: 5173 (Vite default) ou 3000
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Déterminer le chemin du projet (remonter 2 niveaux depuis scripts/launch)
    script_dir = Path(__file__).parent.parent.parent.absolute()
    frontend_dir = script_dir / "frontend"
    
    print("=" * 60)
    print("CRBot - Frontend Server Launcher (Vite)")
    print("=" * 60)
    print(f"\nFrontend Directory: {frontend_dir}")
    
    # Vérifier que le répertoire frontend existe
    if not frontend_dir.exists():
        print("\n[ERROR] Frontend directory not found!")
        sys.exit(1)
    
    # Vérifier que node_modules existe
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("\n[WARNING] node_modules not found!")
        print("[INFO] Running npm install first...")
        try:
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True)
        except subprocess.CalledProcessError:
            print("[ERROR] npm install failed!")
            sys.exit(1)
    
    print("\n[INFO] Starting Vite dev server...")
    print("[INFO] Server will run on http://localhost:5173")
    print("[INFO] Press CTRL+C to stop the server\n")
    
    # Lancer Vite
    try:
        subprocess.run(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n[INFO] Server stopped by user")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to start Vite server: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n[ERROR] npm not found!")
        print("[INFO] Please install Node.js: https://nodejs.org/")
        sys.exit(1)

if __name__ == "__main__":
    main()
