# github-sts

A Python-based Security Token Service (STS) for the GitHub API.

Workloads with OIDC tokens (GitHub Actions, Azure AD, GCP, AWS, Kubernetes, Okta, …) exchange them for **short-lived, scoped GitHub installation tokens**. No PATs required.

Supports **multiple GitHub Apps** with YAML-based configuration (ideal for Kubernetes ConfigMaps).

Inspired by [**octo-sts/app**](https://github.com/octo-sts/app) — see [NOTICE](NOTICE) for attribution.

---

## How It Works

```
Workload → OIDC Token → github-sts → Scoped GitHub Token
```

```
  Workload                  github-sts                   GitHub
     │                          │                          │
     │  GET /sts/exchange       │                          │
     │  ?scope=org/repo         │                          │
     │  &app=my-app             │                          │
     │  &identity=ci            │                          │
     │  Authorization: Bearer   │                          │
     │─────────────────────────>│                          │
     │                          │  Validate OIDC sig/exp   │
     │                          │  Load trust policy       │
     │                          │  Evaluate claims         │
     │                          │  Request install token ──>
     │                          │<─────────────────────────│
     │<─────────────────────────│                          │
     │  { token, permissions }  │                          │
```

---

## Quick Start

### Option 1: Docker (local only)

A pre-built image is available from [GitHub Container Registry](https://github.com/AlexandreODelisle/py-github-sts/pkgs/container/py-github-sts):

```bash
docker run -p 9999:8080 \
  -e PYGITHUBSTS_GITHUB_APP_ID="your_app_id" \
  -e PYGITHUBSTS_GITHUB_APP_PRIVATE_KEY="$(cat /path/to/private_key.pem)" \
  ghcr.io/alexandreodelisle/py-github-sts:latest
```

### Option 2: Helm (Kubernetes)

The Helm chart is published to the GitHub Container Registry OCI repository:

```bash
# Create credentials secret
kubectl create secret generic github-sts-credentials \
  --from-literal=github-app-id="YOUR_GITHUB_APP_ID" \
  --from-file=github-app-private-key=/path/to/private_key.pem

# Install from OCI registry
helm install github-sts \
  oci://ghcr.io/alexandreodelisle/py-github-sts/github-sts-chart \
  --set github.existingSecret="github-sts-credentials"
```

See the [chart README](charts/github-sts/README.md) for full configuration options including Ingress/HTTPRoute setup.

### Option 3: From Source

```bash
# Prerequisites: Python 3.14+, uv (https://docs.astral.sh/uv/)
uv sync

export PYGITHUBSTS_GITHUB_APP_ID=your_app_id
export PYGITHUBSTS_GITHUB_APP_PRIVATE_KEY="$(cat /path/to/private_key.pem)"

uv run python -m uvicorn github_sts.main:app --host 0.0.0.0 --port 9999
```

### Verify

```bash
curl http://localhost:9999/health
# {"status":"ok"}
```

---

## Usage

Exchange an OIDC token for a scoped GitHub token:

```bash
curl -sf -H "Authorization: Bearer $OIDC_TOKEN" \
  "http://localhost:9999/sts/exchange?scope=org/repo&app=default&identity=ci"
```

For complete usage examples — including GitHub Actions (native OIDC), Azure AD / Entra ID (CLI and workflows), and more — see **[EXAMPLES.md](EXAMPLES.md)**.

---

## Trust Policies

Policies are fetched directly from GitHub repositories at:

```
{base_path}/{app_name}/{identity}.sts.yaml
```

Default: `.github/sts/default/{identity}.sts.yaml`

### Policy Schema

**Exact match (most secure):**
```yaml
issuer: https://token.actions.githubusercontent.com
subject: repo:org/repo:ref:refs/heads/main
permissions:
  contents: read
  issues: write
```

**Regex patterns (flexible):**
```yaml
issuer: https://login.microsoftonline.com/<tenant-id>/v2.0
subject_pattern: "[a-f0-9-]+"     # Azure AD object ID
claim_pattern:
  azp: "<client-id>"              # restrict by app registration
permissions:
  contents: read
```

**Restrict to specific workflow (least-privilege):**
```yaml
issuer: https://token.actions.githubusercontent.com
subject_pattern: "repo:org/repo:.*"
claim_pattern:
  job_workflow_ref: "org/repo/.github/workflows/deploy\\.yml@.*"
permissions:
  deployments: write
  statuses: write
```

### Policy Fields

| Field | Type | Description |
|---|---|---|
| `issuer` | string (exact) | OIDC `iss` claim |
| `subject` | string (exact) | OIDC `sub` claim |
| `subject_pattern` | regex | Used when `subject` is absent |
| `claim_pattern` | map[str→regex] | Match any additional JWT claims |
| `permissions` | map[str→read\|write\|admin] | GitHub App permissions to grant |

---

## Configuration

github-sts uses YAML-based configuration, ideal for Kubernetes ConfigMaps.
See [config/github-sts.example.yaml](config/github-sts.example.yaml) for a complete example.

```bash
export PYGITHUBSTS_CONFIG_PATH=/etc/github-sts/config.yaml
```

### Environment Variables

Environment variables with `PYGITHUBSTS_` prefix override YAML config.

| Env var | Default | Description |
|---|---|---|
| `PYGITHUBSTS_CONFIG_PATH` | — | Path to YAML config file |
| `PYGITHUBSTS_GITHUB_APP_ID` | required | GitHub App numeric ID |
| `PYGITHUBSTS_GITHUB_APP_PRIVATE_KEY` | required | PEM string or path to file |
| `PYGITHUBSTS_GITHUB_APP_NAME` | `default` | App name for env-configured app |
| `PYGITHUBSTS_POLICY_BASE_PATH` | `.github/sts` | Base path in repos for policies |
| `PYGITHUBSTS_POLICY_CACHE_TTL_SECONDS` | `60` | 0 = disable |
| `PYGITHUBSTS_OIDC_ALLOWED_ISSUERS` | — | Comma-sep allowlist (empty = any) |
| `PYGITHUBSTS_JTI_BACKEND` | `memory` | `memory` \| `redis` |
| `PYGITHUBSTS_JTI_REDIS_URL` | — | Redis connection (if backend=redis) |
| `PYGITHUBSTS_AUDIT_FILE_PATH` | `./audit.log` | Audit log file path |
| `PYGITHUBSTS_AUDIT_ROTATION_POLICY` | `daily` | `daily` \| `size` |
| `PYGITHUBSTS_SERVER_LOG_LEVEL` | `INFO` | Log level |
| `PYGITHUBSTS_METRICS_ENABLED` | `true` | Enable/disable metrics |

---

## Metrics

`GET /metrics` — Prometheus text format

| Metric | Type | Description |
|---|---|---|
| `pygithubsts_requests_total` | Counter | HTTP requests by method/path/status |
| `pygithubsts_request_duration_seconds` | Histogram | HTTP latency |
| `pygithubsts_requests_in_flight` | Gauge | Concurrent requests |
| `pygithubsts_token_exchanges_total` | Counter | Exchange attempts by scope/identity/result |
| `pygithubsts_token_exchange_duration_seconds` | Histogram | Exchange latency |
| `pygithubsts_oidc_validation_errors_total` | Counter | OIDC failures by issuer/reason |
| `pygithubsts_policy_loads_total` | Counter | Policy loads by backend/result |
| `pygithubsts_policy_cache_hits_total` | Counter | Cache hits |
| `pygithubsts_policy_cache_misses_total` | Counter | Cache misses |
| `pygithubsts_github_api_calls_total` | Counter | GitHub API calls by endpoint/result |
| `pygithubsts_github_tokens_issued_total` | Counter | Tokens issued by scope/permissions |

---

## Development

### Linting & Formatting

**Check for linting issues:**
```bash
uv run ruff check .
```

**Format code:**
```bash
uv run ruff format .
```

**Check formatting without applying:**
```bash
uv run ruff format --check .
```

**Check import organization:**
```bash
uv run ruff check --select=I .
```

### Running Tests

**All tests:**
```bash
uv run pytest
```

**Specific test file:**
```bash
uv run pytest tests/test_policy.py -v
```

**Specific test:**
```bash
uv run pytest tests/test_policy.py::TestTrustPolicyExactMatch::test_exact_match_passes -v
```

**With coverage:**
```bash
uv run pytest --cov=src/github_sts
```

### Code Quality Tools

The project uses **Ruff** for linting and formatting:
- **E/W**: pycodestyle (PEP 8)
- **F**: Pyflakes (undefined names, etc.)
- **I**: isort (import organization)
- **C4**: flake8-comprehensions
- **B**: flake8-bugbear (common bugs)
- **UP**: pyupgrade (modern Python syntax)
- **RUF**: Ruff-specific rules

Configuration is in `pyproject.toml` under `[tool.ruff]`

---

## Contributing

We welcome contributions that:
- Improve security
- Enhance usability
- Add observability features
- Extend policy evaluation capabilities
- Improve documentation

---

## License

MIT License — See [LICENSE](LICENSE)

---

## References

**Inspiration:**
- [octo-sts/app](https://github.com/octo-sts/app) — Original Go implementation

**GitHub:**
- [GitHub Apps](https://docs.github.com/en/apps)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)

**Standards:**
- [OpenID Connect Specification](https://openid.net/connect/)

**Tools:**
- [FastAPI](https://fastapi.tiangolo.com/)
- [uv](https://docs.astral.sh/uv/)
- [Ruff](https://docs.astral.sh/ruff/)
- [pytest](https://docs.pytest.org/)
