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

PORT = 3000
HR_PORTAL_DIR = os.path.dirname(os.path.abspath(__file__))

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
        """Handle GET requests"""
        # Route all requests to index.html for SPA routing
        if self.path == '/' or not self.path.startswith('/'):
            self.path = '/index.html'
        
        return super().do_GET()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), HRPortalHandler) as httpd:
        print("=" * 60)
        print("🚀 EchoSafe HR Portal Server")
        print("=" * 60)
        print(f"✓ Running at http://localhost:{PORT}")
        print(f"✓ Serving from: {HR_PORTAL_DIR}")
        print(f"✓ Backend API: http://localhost:8000")
        print("=" * 60)
        print("\nPress CTRL+C to stop\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
