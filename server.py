"""TDS GA7 policy service — stdlib-only HTTP server for Cloud Run.

Two ways to reach the same five gates:

    POST /release-gate                 the values compiled into the gates
    POST /s/<token>/release-gate       the values belonging to <token>'s student

`<token>` is a student's email, base64url encoded, so one deployment answers
correctly for anyone: the grader's payloads are identical, but the assigned
tenant, workspace, labels and host allowlist are derived per student exactly as
the exam derives them.

No LLM, no phrase lists, no network calls, no wall-clock reads — every decision
is a pure function of the request body and the student's identity.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gates"))

import variant  # noqa: E402
import workflow  # noqa: E402
from q1_release_gate import handle as release_gate  # noqa: E402
from q2_firewall import handle as action_firewall  # noqa: E402
from q3_terraform import handle as terraform_plan  # noqa: E402
from q4_sanitize import handle as sanitize_output  # noqa: E402
from q5_corroborate import handle as corroborate  # noqa: E402

ROUTES = {
    "/release-gate": release_gate,
    "/action-firewall": action_firewall,
    "/terraform/plan": terraform_plan,
    "/sanitize-output": sanitize_output,
    "/corroborate": corroborate,
}


def _split(path):
    """Return (endpoint, email or None) for a request path.

    Accepts an optional /api prefix and an optional /s/<token> identity segment,
    with or without a trailing slash, so a base URL pasted with either style
    still resolves.
    """
    p = urlparse(path).path
    p = "/" + p.strip("/")
    if p.startswith("/api/"):
        p = p[4:]
    email = None
    if p.startswith("/s/"):
        rest = p[3:]
        token, _, tail = rest.partition("/")
        email = variant.decode_email(token)
        if email is None:
            return None, False  # a malformed identity is its own error
        p = "/" + tail
    return (p.rstrip("/") or "/"), email


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "tds-ga7"

    def do_POST(self):
        endpoint, email = _split(self.path)
        if endpoint is None:
            return self._send({"error": "unknown identity in path"}, 404)

        if endpoint == "/workflow":
            # Creating question one's evidence: the one thing a student cannot
            # share, made a single request instead of a repository to build.
            if not email:
                return self._send({"error": "use your /s/<token>/workflow URL"}, 400)
            try:
                result = workflow.ensure(email)
            except workflow.WorkflowError as error:
                return self._send({"error": str(error)}, 503)
            result["status"] = workflow.status_for(email)
            return self._send(result)

        fn = ROUTES.get(endpoint)
        if fn is None:
            return self._send({"error": "not found", "endpoints": sorted(ROUTES)}, 404)

        try:
            n = int(self.headers.get("content-length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else None
        except Exception:
            # A malformed body is not a crash: each gate rejects it on its own terms.
            body = None

        if email:
            with variant.use(variant.for_email(email)):
                return self._send(fn(body))
        return self._send(fn(body))

    def do_GET(self):
        endpoint, email = _split(self.path)
        if endpoint is None:
            return self._send({"error": "unknown identity in path"}, 404)

        if endpoint in ("/", "/healthz"):
            payload = {"service": "tds-ga7", "ok": True, "endpoints": sorted(ROUTES)}
            if email:
                payload["assigned"] = _describe(email)
            return self._send(payload)

        if endpoint == "/score":
            query = parse_qs(urlparse(self.path).query)
            who = email or (query.get("email") or [None])[0]
            if not who:
                return self._send({"error": "pass ?email=… or use a /s/<token>/ URL"}, 400)
            quiz = (query.get("quiz") or ["tds-2026-05-ga7"])[0]
            return self._send(workflow.saved_score(who, quiz))

        if endpoint == "/workflow":
            query = parse_qs(urlparse(self.path).query)
            who = email or (query.get("email") or [None])[0]
            if not who:
                return self._send({"error": "pass ?email=… or use a /s/<token>/ URL"}, 400)
            return self._send({
                "workflowUrl": workflow.workflow_url(who),
                "status": workflow.status_for(who),
            })

        if endpoint == "/variant":
            query = parse_qs(urlparse(self.path).query)
            who = email or (query.get("email") or [None])[0]
            if not who:
                return self._send({"error": "pass ?email=… or use a /s/<token>/ URL"}, 400)
            return self._send(_describe(who))

        if endpoint in ROUTES:
            return self._send({"endpoint": endpoint, "method": "POST"})

        return self._send({"error": "not found", "endpoints": sorted(ROUTES)}, 404)

    def _send(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        # The solver page is served from a different origin and reads these.
        self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")
        self.send_header("content-length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


def _describe(email):
    """What this service will enforce for one student — so they can check it."""
    v = variant.for_email(email)
    return {
        "email": v["email"],
        "baseUrl": f"/s/{variant.encode_email(email)}",
        "tenantId": v["tenantId"],
        "emailDomain": v["emailDomain"],
        "environment": v["environment"],
        "labels": v["labels"],
        "allowedHosts": sorted(v["allowedHosts"]),
        "subject": v["subject"],
        "stalenessDays": v["stalenessDays"],
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
