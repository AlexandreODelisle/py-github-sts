This project is inspired by octo-sts/app (https://github.com/octo-sts/app),
an excellent Go-based implementation that pioneered the concept of using OIDC
federation for GitHub token exchange.

octo-sts/app is licensed under the Apache License, Version 2.0:
https://github.com/octo-sts/app/blob/main/LICENSE

While github-sts is an independent Python implementation and does not share
code with octo-sts/app, the core concept of exchanging OIDC tokens for scoped
GitHub installation tokens — including the trust policy model and the
repository-based policy resolution pattern — originated from that project.
