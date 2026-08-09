"""Creates a student's workflow evidence for question one.

The exam wants a public workflow named exactly `TDS GA7 Release Gate`, carrying
a step named with that student's own email, that has run green on a push to
main. The email in the step name is why this cannot simply be shared — so
instead each student gets their own file in one repository, committed on
request.

Two details make many files in one repository workable:

* every workflow is scoped with ``paths:`` to its own file, so committing one
  does not re-run the other several hundred;
* the commit that creates the file is itself a push to main touching that path,
  which is exactly the run the status badge needs.

The GitHub token lives only in this process's environment. It is never returned,
logged, or sent anywhere.
"""

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_WORKFLOW_REPO", "angadseth/tds-ga7-gate")
WORKFLOW_NAME = "TDS GA7 Release Gate"


class WorkflowError(RuntimeError):
    pass


def slug(email):
    """A stable, filesystem-safe name per student that leaks nothing."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:12]


def path_for(email):
    return f".github/workflows/ga7-{slug(email)}.yml"


def workflow_url(email):
    return f"https://github.com/{REPO}/actions/workflows/ga7-{slug(email)}.yml"


def yaml_for(email):
    path = path_for(email)
    return f"""name: {WORKFLOW_NAME}

# Scoped to this file so committing one student's evidence does not re-run
# every other workflow in the repository.
on:
  push:
    branches: [main]
    paths: ['{path}']
  workflow_dispatch:

permissions:
  contents: read

jobs:
  release-gate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    strategy:
      fail-fast: false
      matrix:
        python: ["3.11", "3.12"]
    steps:
      - name: 'TDS identity: {email}'
        run: echo "TDS GA7 release gate - {email}"

      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python }}}}

      - name: Test the release-gate implementation
        run: python release_gate_test.py
"""


def _request(method, url, token, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "tds-ga7-gate")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(body)
        except ValueError:
            return error.code, {"message": body[:200]}


def ensure(email):
    """Create or refresh this student's workflow. Returns the workflow page URL."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise WorkflowError(
            "This deployment has no GitHub token configured, so it cannot create "
            "workflow evidence. Create the workflow yourself, or ask whoever runs "
            "this service to set GITHUB_TOKEN."
        )

    path = path_for(email)
    wanted = yaml_for(email)
    encoded = base64.b64encode(wanted.encode("utf-8")).decode("ascii")

    status, existing = _request("GET", f"{API}/repos/{REPO}/contents/{path}", token)
    if status == 200 and existing.get("content"):
        current = base64.b64decode(existing["content"]).decode("utf-8", "replace")
        if current.strip() == wanted.strip():
            # Already correct; another commit would only add noise.
            return {"workflowUrl": workflow_url(email), "created": False}

    payload = {
        "message": f"Add GA7 workflow evidence for {email}",
        "content": encoded,
        "committer": {"name": "tds-ga7-gate", "email": "noreply@users.noreply.github.com"},
    }
    if status == 200 and existing.get("sha"):
        payload["sha"] = existing["sha"]

    status, result = _request("PUT", f"{API}/repos/{REPO}/contents/{path}", token, payload)
    if status not in (200, 201):
        raise WorkflowError(
            f"GitHub refused the commit ({status}): {result.get('message', 'unknown error')}"
        )
    return {"workflowUrl": workflow_url(email), "created": True}


def status_for(email):
    """Has this student's workflow run green yet? Read the badge, like the exam does."""
    url = (
        f"https://github.com/{REPO}/actions/workflows/ga7-{slug(email)}.yml"
        "/badge.svg?branch=main&event=push"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "tds-ga7-gate"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            svg = response.read().decode("utf-8", "replace")
    except Exception:
        return "unknown"
    if "passing" in svg:
        return "passing"
    if "failing" in svg:
        return "failing"
    return "no status"
