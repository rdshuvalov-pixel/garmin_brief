#!/usr/bin/env python3
"""Local static server for morning brief HTML pages."""

import argparse
import http.server
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DEFAULT_PORT = 8765
DEFAULT_HOST = "0.0.0.0"


class BriefHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve morning brief static files")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address (0.0.0.0 for VPS)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    with socketserver.TCPServer((args.host, args.port), BriefHandler) as httpd:
        print(f"Serving {WEB_DIR} at http://{args.host}:{args.port}/")
        print(f"Briefs: http://127.0.0.1:{args.port}/briefs/")
        if args.host == "0.0.0.0":
            print("Public: set BRIEF_PUBLIC_BASE_URL=http://<VPS_IP>:{port}".format(port=args.port))
        httpd.serve_forever()


if __name__ == "__main__":
    main()
