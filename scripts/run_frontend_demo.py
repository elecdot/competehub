import http.server
import socketserver
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "frontend" / "demo"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(DEMO_DIR))
    with ReusableTCPServer(("127.0.0.1", 5173), handler) as httpd:
        print("CompeteHub demo frontend: http://localhost:5173")
        httpd.serve_forever()

