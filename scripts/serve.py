#!/usr/bin/env python3
"""Local preview server.

    python3 scripts/serve.py [port]      default 8050

Serves the app/ folder with the stdlib server. The site also opens fine straight
from the file system (app/index.html), since the data files are plain scripts.
"""
import http.server, os, sys

if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8050
    print(f"serving {os.getcwd()} on http://localhost:{port}/")
    http.server.ThreadingHTTPServer(("", port), http.server.SimpleHTTPRequestHandler).serve_forever()
