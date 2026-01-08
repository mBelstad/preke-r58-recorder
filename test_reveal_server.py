#!/usr/bin/env python3
"""Test server for reveal.js that properly maps /reveal.js/ paths"""
import http.server
import socketserver
from pathlib import Path
import sys

PORT = 8888
reveal_dist = Path('reveal.js/dist')

class RevealHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path.cwd()), **kwargs)
    
    def translate_path(self, path):
        # Map /reveal.js/* to reveal.js/dist/*
        if path.startswith('/reveal.js/'):
            file_path = path.replace('/reveal.js/', '')
            full_path = reveal_dist / file_path
            if full_path.exists() and full_path.is_file():
                return str(full_path)
            # If it's a directory request, try index.html
            if full_path.is_dir():
                index_path = full_path / 'index.html'
                if index_path.exists():
                    return str(index_path)
        # Default behavior for other paths
        return super().translate_path(path)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Only log errors
        if args[1].startswith('4') or args[1].startswith('5'):
            super().log_message(format, *args)

if __name__ == '__main__':
    if not reveal_dist.exists():
        print(f"ERROR: reveal.js/dist not found at {reveal_dist.absolute()}")
        sys.exit(1)
    
    print(f"Starting reveal.js test server on http://localhost:{PORT}")
    print(f"Serving reveal.js from: {reveal_dist.absolute()}")
    print(f"\nTest page: http://localhost:{PORT}/test_reveal_local.html")
    print("Press Ctrl+C to stop\n")
    
    with socketserver.TCPServer(("", PORT), RevealHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
