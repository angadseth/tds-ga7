"""TDS GA7 — one deterministic policy service, five endpoints.

  POST /release-gate      Q1  CI/CD container release gate
  POST /action-firewall   Q2  LLM action firewall
  POST /terraform/plan    Q3  Terraform plan policy gate
  POST /sanitize-output   Q4  LLM output handling gate (OWASP LLM05)
  POST /corroborate       Q5  OSINT corroboration engine

Every decision is pure Python: no LLM, no network, no wall clock.
"""

import os
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gates"))

from q1_release_gate import handle as release_gate  # noqa: E402
from q2_firewall import handle as action_firewall  # noqa: E402
from q3_terraform import handle as terraform_plan  # noqa: E402
from q4_sanitize import handle as sanitize_output  # noqa: E402
from q5_corroborate import handle as corroborate  # noqa: E402

app = FastAPI(title="TDS GA7 policy service", docs_url="/docs")

ROUTES = {
    "/release-gate": release_gate,
    "/action-firewall": action_firewall,
    "/terraform/plan": terraform_plan,
    "/sanitize-output": sanitize_output,
    "/corroborate": corroborate,
}


async def _body(request: Request):
    """Parse the JSON body, returning a sentinel the gates treat as invalid."""
    try:
        return await request.json()
    except Exception:
        return None


def _register(path, fn):
    async def endpoint(request: Request):
        return JSONResponse(fn(await _body(request)))

    # Mounted twice so the function works with or without Vercel's /api prefix.
    app.post(path)(endpoint)
    app.post("/api" + path)(endpoint)


for _path, _fn in ROUTES.items():
    _register(_path, _fn)


@app.get("/")
def index():
    return {"service": "tds-ga7", "endpoints": sorted(ROUTES), "identity": "24f2004141@ds.study.iitm.ac.in"}


@app.get("/healthz")
def healthz():
    return {"ok": True}
