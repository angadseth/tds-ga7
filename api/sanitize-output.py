"""Vercel serverless entry: LLM output handling gate"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gates"))

from q4_sanitize import handle  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n = int(self.headers.get("content-length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else None
        except Exception:
            body = None
        self._send(handle(body))

    def do_GET(self):
        self._send({"endpoint": '/sanitize-output', "method": "POST", "identity": "24f2004141@ds.study.iitm.ac.in"})

    def _send(self, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass
