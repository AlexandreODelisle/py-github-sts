# GitHub STS Helm Chart

A Kubernetes Helm chart for deploying the GitHub Security Token Service (STS).

## Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.0+

### Quick Start

1. **Using an existing secret (recommended):**

First, create the secret:
```bash
kubectl create secret generic github-sts-credentials \
  --from-literal=github-app-id="YOUR_GITHUB_APP_ID" \
  --from-file=github-app-private-key=/path/to/private_key.pem
```

Then install with the existing secret:
```bash
helm install github-sts . \
  --set github.existingSecret="github-sts-credentials"
```

2. **With `--set-file` for the private key:**

```bash
helm install github-sts . \
  --set github.appId="YOUR_GITHUB_APP_ID" \
  --set-file github.appPrivateKey=/path/to/private_key.pem
```

> **Note:** Avoid passing multi-line PEM keys via `--set` on the command line.
> Use `--set-file`, an existing secret, or a values file instead to prevent
> shell history exposure and YAML escaping issues.

3. **Using Vault:**

If you have Vault integration configured:
```bash
export GITHUB_APP_ID=$(vault kv get -field=github_app_id homelab/github-action/octo-sts)

helm install github-sts . \
  --set github.appId="$GITHUB_APP_ID" \
  --set-file github.appPrivateKey=/path/to/private_key.pem
```

## Configuration

Key configuration options (see `values.yaml` for all options):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image.repository` | `github-sts` | Docker image repository |
| `image.tag` | `""` | Docker image tag (defaults to Chart.appVersion) |
| `replicaCount` | `1` | Number of replicas |
| `service.port` | `8080` | Service port |
| `resources` | `{}` | CPU/memory requests and limits |
| `autoscaling.enabled` | `false` | Enable HPA |
| `ingress.enabled` | `false` | Enable Ingress (traditional API) |
| `httproute.enabled` | `false` | Enable HTTPRoute (Gateway API) |
| `github.appId` | `""` | GitHub App ID (required) |
| `github.appPrivateKey` | `""` | GitHub App Private Key (required) |
| `github.existingSecret` | `""` | Use an existing secret for credentials |
| `github.appName` | `"default"` | GitHub App name for env-configured app |

## Ingress & Routing

### Ingress (Traditional)

```bash
helm install github-sts . \
  --set github.existingSecret="github-sts-credentials" \
  --set ingress.enabled=true \
  --set ingress.className="nginx" \
  --set ingress.hosts[0].host="github-sts.example.com"
```

### HTTPRoute (Gateway API - Modern)

Requires Gateway API CRDs. HTTPRoute is more powerful and flexible than Ingress.

```bash
helm install github-sts . \
  --set github.existingSecret="github-sts-credentials" \
  --set httproute.enabled=true \
  --set httproute.parentRefs[0].name="my-gateway" \
  --set httproute.hostnames[0]="github-sts.example.com"
```

## Upgrade

```bash
helm upgrade github-sts . \
  --set github.existingSecret="github-sts-credentials"
```

## Uninstall

```bash
helm uninstall github-sts
```

## Features

- ✅ Multi-replica deployment with pod anti-affinity
- ✅ Health checks (readiness & liveness probes)
- ✅ Horizontal pod autoscaling
- ✅ Ingress support (traditional Kubernetes API)
- ✅ HTTPRoute support (Gateway API - modern approach)
- ✅ Security context (non-root user, read-only filesystem)
- ✅ Resource limits and requests
- ✅ Prometheus metrics support
- ✅ Support for existing secrets

## Security

The chart enforces security best practices:
- Runs as non-root user (UID 1000)
- Read-only root filesystem
- No privileged escalation
- Dropped Linux capabilities
- Health probes for auto-recovery
