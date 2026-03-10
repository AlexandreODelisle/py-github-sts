# Examples

Usage examples for exchanging OIDC tokens from various identity providers via **github-sts**.

---

## Azure AD (Entra ID)

### Prerequisites

- An Azure AD App Registration configured as a federated identity provider
- The Azure AD tenant OIDC issuer added to your github-sts configuration:

```yaml
oidc:
  allowed_issuers:
    - "https://login.microsoftonline.com/<tenant-id>/v2.0"
```

- A trust policy (e.g. `.github/sts/default/my-azure-identity.sts.yaml`) in the target repository that matches Azure AD token claims

---

### Local / CLI Usage

Log in with an Azure AD service principal and exchange the resulting access token for a scoped GitHub token:

```bash
# Authenticate with Azure AD using a service principal
az login --service-principal \
  --username <client-id> \
  --password <client-secret> \
  --tenant <tenant-id> \
  --allow-no-subscriptions

# Obtain an OIDC access token
OIDC_TOKEN=$(az account get-access-token --query accessToken -o tsv)

# Exchange the OIDC token for a scoped GitHub installation token
curl -sf \
  -H "Authorization: Bearer ${OIDC_TOKEN}" \
  "https://github-sts.example.com/sts/exchange?scope=my-org/my-repo&app=default&identity=my-azure-identity"
```

**Example response:**

```json
{
  "token": "ghs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "permissions": {
    "contents": "read"
  },
  "expires_at": "2026-03-09T12:00:00Z"
}
```

---

### GitHub Actions

Use Azure federated credentials with OIDC to obtain a scoped GitHub token inside a workflow:

```yaml
name: Azure STS Example

on:
  workflow_dispatch:
    inputs:
      repository:
        description: "Target repository (org/repo)"
        required: true
      identity:
        description: "STS identity name"
        required: true

permissions:
  id-token: write   # Required for Azure OIDC

jobs:
  azure-sts:
    runs-on: ubuntu-latest
    steps:
      - name: Install Azure CLI
        run: |
          curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZ_APP_ID }}
          tenant-id: ${{ secrets.AZ_TENANT_ID }}
          allow-no-subscriptions: true

      - name: Get scoped GitHub token via STS
        id: sts
        run: |
          OIDC_TOKEN=$(az account get-access-token --query accessToken -o tsv)

          GITHUB_TOKEN=$(curl -sf \
            -H "Authorization: Bearer ${OIDC_TOKEN}" \
            "https://github-sts.example.com/sts/exchange?scope=${{ inputs.repository }}&app=default&identity=${{ inputs.identity }}" \
            | jq -r '.token')

          echo "::add-mask::$GITHUB_TOKEN"
          echo "token=$GITHUB_TOKEN" >> $GITHUB_OUTPUT

      - name: Checkout target repository
        uses: actions/checkout@v4
        with:
          repository: ${{ inputs.repository }}
          token: ${{ steps.sts.outputs.token }}
          path: external-repo
```

**Required repository secrets:**

| Secret | Description |
|---|---|
| `AZ_APP_ID` | Azure AD Application (client) ID |
| `AZ_TENANT_ID` | Azure AD Tenant ID |

> **Note:** No client secret is needed in the GitHub Actions workflow when using [Azure Workload Identity Federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation) with GitHub's OIDC provider.

---

## GitHub Actions (Native OIDC)

GitHub Actions can issue OIDC tokens natively — no external identity provider required. The workflow requests an OIDC token directly from GitHub's token endpoint and exchanges it with github-sts.

### Prerequisites

- The GitHub Actions OIDC issuer added to your github-sts configuration:

```yaml
oidc:
  allowed_issuers:
    - "https://token.actions.githubusercontent.com"
```

- A trust policy (e.g. `.github/sts/default/my-identity.sts.yaml`) in the target repository that matches GitHub Actions token claims
- The workflow must have `id-token: write` permission

---

### GitHub Actions Workflow

```yaml
name: GitHub Actions STS Example

on:
  workflow_dispatch:
    inputs:
      repository:
        description: "Target repository (org/repo)"
        required: true
      identity:
        description: "STS identity name"
        required: true

permissions:
  id-token: write   # Required to request the OIDC token

jobs:
  github-sts:
    runs-on: ubuntu-latest
    steps:
      - name: Get scoped GitHub token via STS
        id: sts
        run: |
          OIDC_TOKEN=$(curl -sH "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=github-sts" | jq -r '.value')

          GITHUB_TOKEN=$(curl -sf \
            -H "Authorization: Bearer $OIDC_TOKEN" \
            "https://github-sts.example.com/sts/exchange?scope=${{ inputs.repository }}&app=default&identity=${{ inputs.identity }}" \
            | jq -r '.token')

          echo "::add-mask::$GITHUB_TOKEN"
          echo "token=$GITHUB_TOKEN" >> $GITHUB_OUTPUT

      - name: Checkout target repository
        uses: actions/checkout@v4
        with:
          repository: ${{ inputs.repository }}
          token: ${{ steps.sts.outputs.token }}
          path: external-repo
```

> **Note:** No secrets are needed — GitHub Actions provides the `ACTIONS_ID_TOKEN_REQUEST_TOKEN` and `ACTIONS_ID_TOKEN_REQUEST_URL` environment variables automatically when `id-token: write` is set.
