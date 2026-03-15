# GitHub STS Helm Chart

A Kubernetes Helm chart for deploying the GitHub Security Token Service (STS).

## Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.0+

### Quick Start

1. **Create a Kubernetes secret with your GitHub App private key:**

```bash
kubectl create secret generic my-github-app-credentials \
  --from-file=github-app-private-key=/path/to/private_key.pem
```

2. **Install with the app configured:**

```bash
helm install github-sts . \
  --set github.apps.default.appId="YOUR_GITHUB_APP_ID" \
  --set github.apps.default.existingSecret="my-github-app-credentials"
```

3. **Multiple apps:**

```bash
kubectl create secret generic app1-credentials \
  --from-file=github-app-private-key=/path/to/app1_key.pem
kubectl create secret generic app2-credentials \
  --from-file=github-app-private-key=/path/to/app2_key.pem

helm install github-sts . \
  --set github.apps.app1.appId="111" \
  --set github.apps.app1.existingSecret="app1-credentials" \
  --set github.apps.app2.appId="222" \
  --set github.apps.app2.existingSecret="app2-credentials"
```

> **Note:** Each app's private key must be stored in an existing Kubernetes Secret.
> The app name is used in policy paths: `{policy.basePath}/{appName}/{identity}.sts.yaml`

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
| `github.apps` | `{}` | Map of GitHub App configs (appId, existingSecret, secretPrivateKeyKey) |

## Ingress & Routing

### Ingress (Traditional)

```bash
helm install github-sts . \
  --set github.apps.default.appId="YOUR_APP_ID" \
  --set github.apps.default.existingSecret="my-github-app-credentials" \
  --set ingress.enabled=true \
  --set ingress.className="nginx" \
  --set ingress.hosts[0].host="github-sts.example.com"
```

### HTTPRoute (Gateway API - Modern)

Requires Gateway API CRDs. HTTPRoute is more powerful and flexible than Ingress.

```bash
helm install github-sts . \
  --set github.apps.default.appId="YOUR_APP_ID" \
  --set github.apps.default.existingSecret="my-github-app-credentials" \
  --set httproute.enabled=true \
  --set httproute.parentRefs[0].name="my-gateway" \
  --set httproute.hostnames[0]="github-sts.example.com"
```

## Upgrade

```bash
helm upgrade github-sts . \
  --set github.apps.default.appId="YOUR_APP_ID" \
  --set github.apps.default.existingSecret="my-github-app-credentials"
```

## Uninstall

```bash
helm uninstall github-sts
```

## Features

- ✅ Multi-replica deployment support
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
