#!/usr/bin/env python3
"""
Dedicated HR Portal Server - Optimized for performance
Runs on port 3000 by default
"""

import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs
from pathlib import Path

DEFAULT_PORT = 3000
HR_PORTAL_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = Path(HR_PORTAL_DIR).parent  # This is the EchoSafe project root
FRONTEND_DIR = ROOT_DIR / "frontend"

class HRPortalHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HR_PORTAL_DIR, **kwargs)

    def end_headers(self):
        """Add caching and security headers"""
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
        super().end_headers()

    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[HR Portal] {format % args}")

    def do_GET(self):
        """Handle GET requests, serving index.html for SPA routes."""
        # If the path doesn't point to an existing file, serve index.html.
        # This allows the frontend's router to handle the path.
        path = self.translate_path(self.path)
        if not os.path.exists(path):
            self.path = "/index.html"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    max_tries = 10
    
    for current_port in range(DEFAULT_PORT, DEFAULT_PORT + max_tries):
        try:
            with socketserver.TCPServer(("", current_port), HRPortalHandler) as httpd:
                print("=" * 60)
                print("🚀 EchoSafe HR Portal Server")
                print("=" * 60)
                print(f"✓ Portal running at http://localhost:{current_port}")
                print(f"✓ Serving application from: {HR_PORTAL_DIR}")
                print(f"✓ Backend API: http://localhost:8000")
                print("=" * 60)
                print("\nPress CTRL+C to stop\n")
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\n\nServer stopped.")
                break
        except OSError as e:
            print(f"⚠️ Port {current_port} is busy, trying next port...")
    else:
        print(f"❌ Error: Could not find an open port between {DEFAULT_PORT} and {DEFAULT_PORT + max_tries - 1}")
