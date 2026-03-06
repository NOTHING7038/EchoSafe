#!/usr/bin/env python3
"""
Simple HTTP server for EchoSafe frontend development
Serves index.html on port 8080
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8080
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = Path(FRONTEND_DIR).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"🚀 Frontend Server running at http://localhost:{PORT}")
    print(f"📁 Serving files from: {FRONTEND_DIR}")
    print(f"🏠 Access Page (local file): {(ROOT_DIR / 'index.html').as_uri()}")
    print(f"👥 HR Portal (local file): {(ROOT_DIR / 'hr_portal' / 'index.html').as_uri()}")
    print(f"🔗 Backend API: http://localhost:8000")
    print(f"\nPress CTRL+C to stop")
    httpd.serve_forever()
