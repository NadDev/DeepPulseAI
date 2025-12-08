#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend dashboard
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000
FRONTEND_DIR = Path(__file__).parent / "frontend"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def log_message(self, format, *args):
        # Better logging
        print(f"[{self.log_date_time_string()}] {format % args}")

def run_server():
    os.chdir(FRONTEND_DIR)
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🚀 Frontend server running at http://localhost:{PORT}")
        print(f"📂 Serving files from: {FRONTEND_DIR}")
        print(f"📄 Open http://localhost:{PORT}/dashboard-live.html")
        print(f"\nPress CTRL+C to stop\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✋ Server stopped")

if __name__ == "__main__":
    run_server()
