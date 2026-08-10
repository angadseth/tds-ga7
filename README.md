# TDS GA7 — CI/CD, Security & Cloud

Deterministic policy service (Q1–Q5) + OSINT guides (Q6–Q10).

## Policy Endpoints (Q1–Q5)

Every decision is pure Python: no LLM, no suspicious-phrase lists, no network calls, and no reads of the wall clock.

| Endpoint | Question |
| --- | --- |
| `POST /release-gate` | CI/CD container release gate |
| `POST /action-firewall` | LLM action firewall |
| `POST /terraform/plan` | Terraform plan policy gate |
| `POST /sanitize-output` | LLM output handling gate (OWASP LLM05) |
| `POST /corroborate` | OSINT corroboration engine |

## OSINT Guides (Q6–Q10)

| Question | Guide | Topic |
| --- | --- | --- |
| Q6 | [Street View Geolocation](Q6.md) | Where in the world is this? |

## Layout

- `api/index.py` — routing only; each route delegates to one pure `handle(body) -> dict`.
- `api/gates/q*.py` — the rule engines, stdlib only.
- `api/gates/test_q*.py` — plain-assert suites, runnable with `python test_qN.py` or pytest.

## Run the tests

```bash
for f in api/gates/test_q*.py; do python "$f"; done
```

The `TDS GA7 Release Gate` workflow runs these on every push to `main`.

---

## Collaboration & Attribution

**Built by:** Angad Jangir (24f2004141@ds.study.iitm.ac.in)

- **GitHub:** https://github.com/angadseth — **⭐ Follow for more TDS resources**
- **LinkedIn:** https://linkedin.com/in/angadseth
- **This Repo:** https://github.com/angadseth/tds-ga7

If these guides help, star the repo! Suggestions and contributions welcome.
