"""
Prometheus metrics for github-sts.
"""
from prometheus_client import Counter, Gauge, Histogram, Info

# ── HTTP metrics ──────────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "pygithubsts_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "pygithubsts_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

IN_FLIGHT = Gauge(
    "pygithubsts_requests_in_flight",
    "Number of requests currently being processed",
)

# ── Token exchange metrics ────────────────────────────────────────────────────
TOKEN_EXCHANGES_TOTAL = Counter(
    "pygithubsts_token_exchanges_total",
    "Total token exchange attempts",
    ["scope", "identity", "result"],  # result: success | denied | error
)

TOKEN_EXCHANGE_LATENCY = Histogram(
    "pygithubsts_token_exchange_duration_seconds",
    "Token exchange duration in seconds",
    ["scope", "identity"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

OIDC_VALIDATION_ERRORS = Counter(
    "pygithubsts_oidc_validation_errors_total",
    "OIDC token validation failures",
    ["issuer", "reason"],  # reason: expired | signature | claims | unknown
)

# ── JTI replay prevention metrics ─────────────────────────────────────────────
JTI_REPLAY_ATTEMPTS = Counter(
    "pygithubsts_jti_replay_attempts_total",
    "Total JTI replay attack attempts detected",
)

JTI_CACHE_ERRORS = Counter(
    "pygithubsts_jti_cache_errors_total",
    "JTI cache operation errors",
    ["error_type"],  # error_type: redis_connection | cache_check | other
)

# ── Audit logging metrics ─────────────────────────────────────────────────────
AUDIT_EVENTS_LOGGED = Counter(
    "pygithubsts_audit_events_logged_total",
    "Total audit events logged",
    ["result"],  # result: success | policy_denied | oidc_invalid | etc
)

AUDIT_LOG_ERRORS = Counter(
    "pygithubsts_audit_log_errors_total",
    "Audit log write errors",
    ["backend"],  # backend: file | database
)

# ── Policy metrics ────────────────────────────────────────────────────────────
POLICY_LOADS_TOTAL = Counter(
    "pygithubsts_policy_loads_total",
    "Total policy file load attempts",
    ["backend", "result"],  # backend: github | database
)

POLICY_CACHE_HITS = Counter(
    "pygithubsts_policy_cache_hits_total",
    "Policy cache hits",
)

POLICY_CACHE_MISSES = Counter(
    "pygithubsts_policy_cache_misses_total",
    "Policy cache misses",
)

# ── GitHub App metrics ────────────────────────────────────────────────────────
GITHUB_API_CALLS = Counter(
    "pygithubsts_github_api_calls_total",
    "Total GitHub API calls",
    ["endpoint", "result"],
)

GITHUB_TOKEN_ISSUED = Counter(
    "pygithubsts_github_tokens_issued_total",
    "GitHub installation tokens issued",
    ["scope", "permissions"],
)

# ── App info ──────────────────────────────────────────────────────────────────
APP_INFO = Info(
    "pygithubsts_app",
    "github-sts application info",
)
APP_INFO.info({"version": "1.0.0", "description": "Python OIDC STS for GitHub"})
