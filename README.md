# Project Intentions: GitHub Security Token Service (pyocto-sts)

## Overview

**GitHub Security Token Service** is a Python-based Security Token Service (STS) that exchanges OpenID Connect (OIDC) tokens for short-lived, scoped GitHub installation tokens. It provides a flexible and secure alternative to managing GitHub App credentials across distributed systems.

---

## Inspiration

This project is inspired by [**octo-sts/app**](https://github.com/octo-sts/app), an excellent Go-based implementation that pioneered the concept of using OIDC federation for GitHub token exchange. 

**Key concepts borrowed from octo-sts:**
- OIDC token validation and exchange flow
- Trust policy evaluation for fine-grained permission control
- GitHub App installation token generation
- Policy-as-code approach for declarative access control

---

## Project Vision & Intentions

### The Problem We Solve

**Current State:**
Organizations using GitHub often face a dilemma when distributing access:
1. **GitHub App Tokens** - Secure but complex to manage across many systems
2. **Personal Access Tokens (PATs)** - Simple but pose security risks (long-lived, broad permissions)
3. **Deploy Keys** - Limited to read-only repository access
4. **SSH Keys** - Hard to audit, tied to individuals

Teams must choose between:
- **Security**: Complex GitHub App management across multiple runtimes
- **Operational Simplicity**: Storing long-lived credentials everywhere

### Use Cases

**CI/CD & Automation:**
```
Workflow → OIDC Token → STS → Scoped GitHub Token → Deploy
```


**Internal Tools & Scripts:**
```
Developer Tool → OIDC Token (from corporate IdP) → STS → Temporary Access
```

## Contributing

This is an open-source project inspired by the security community's best practices. We welcome contributions that:
- Improve security
- Enhance usability
- Add observability features
- Extend policy evaluation capabilities
- Improve documentation

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup and contribution guidelines.

---

## License

MIT License - See [LICENSE](LICENSE)

---

## References

- [octo-sts/app](https://github.com/octo-sts/app) - Original Go implementation
- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [OpenID Connect Specification](https://openid.net/connect/)

