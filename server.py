"""TDS GA7 policy service — stdlib-only HTTP server for Cloud Run.

  POST /release-gate      Q1  CI/CD container release gate
  POST /action-firewall   Q2  LLM action firewall
  POST /terraform/plan    Q3  Terraform plan policy gate
  POST /sanitize-output   Q4  LLM output handling gate (OWASP LLM05)
  POST /corroborate       Q5  OSINT corroboration engine

No LLM, no phrase lists, no network calls, no wall-clock reads — every
decision is a pure function of the request body.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gates"))

from q1_release_gate import handle as release_gate  # noqa: E402
from q2_firewall import handle as action_firewall  # noqa: E402
from q3_terraform import handle as terraform_plan  # noqa: E402
from q4_sanitize import handle as sanitize_output  # noqa: E402
from q5_corroborate import handle as corroborate  # noqa: E402

IDENTITY = "24f2004141@ds.study.iitm.ac.in"

ROUTES = {
    "/release-gate": release_gate,
    "/action-firewall": action_firewall,
    "/terraform/plan": terraform_plan,
    "/sanitize-output": sanitize_output,
    "/corroborate": corroborate,
}


def _normalise(path):
    """Accept the bare path and an optional /api prefix, with or without a slash."""
    p = urlparse(path).path.rstrip("/") or "/"
    if p.startswith("/api/"):
        p = p[4:]
    return p


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "tds-ga7"

    def do_POST(self):
        fn = ROUTES.get(_normalise(self.path))
        if fn is None:
            return self._send({"error": "not found", "endpoints": sorted(ROUTES)}, 404)
        try:
            n = int(self.headers.get("content-length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else None
        except Exception:
            # A malformed body is not a crash: the gates reject it on their own terms.
            body = None
        self._send(fn(body))

    def do_GET(self):
        p = _normalise(self.path)
        if p in ("/", "/healthz"):
            return self._send({"service": "tds-ga7", "ok": True,
                               "endpoints": sorted(ROUTES), "identity": IDENTITY})
        if p in ROUTES:
            return self._send({"endpoint": p, "method": "POST", "identity": IDENTITY})
        return self._send({"error": "not found", "endpoints": sorted(ROUTES)}, 404)

    def _send(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
