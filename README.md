# TDS GA7 — deterministic policy service

One FastAPI app exposing five independent policy endpoints. Every decision is pure Python:
no LLM, no suspicious-phrase lists, no network calls, and no reads of the wall clock.

| Endpoint | Question |
| --- | --- |
| `POST /release-gate` | CI/CD container release gate |
| `POST /action-firewall` | LLM action firewall |
| `POST /terraform/plan` | Terraform plan policy gate |
| `POST /sanitize-output` | LLM output handling gate (OWASP LLM05) |
| `POST /corroborate` | OSINT corroboration engine |

## Layout

- `api/index.py` — routing only; each route delegates to one pure `handle(body) -> dict`.
- `api/gates/q*.py` — the rule engines, stdlib only.
- `api/gates/test_q*.py` — plain-assert suites, runnable with `python test_qN.py` or pytest.

## Run the tests

```bash
for f in api/gates/test_q*.py; do python "$f"; done
```

The `TDS GA7 Release Gate` workflow runs these on every push to `main`.

Identity: 24f2004141@ds.study.iitm.ac.in
