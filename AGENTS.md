# AGENTS.md

You are working on the Siren Driver project.

Priorities:
1. Safety: GPIO must default off. Never leave siren energized after errors.
2. Security: webhook must require auth. Prefer HMAC or strong bearer token.
3. Deployability: target Raspberry Pi OS, Podman, systemd.
4. Simplicity: minimal Python service is preferred unless existing repo says otherwise.
5. Hardware assumptions are documented in docs/SIREN_PROJECT_CONTEXT.md.

Before editing code:
- Read docs/SIREN_PROJECT_CONTEXT.md
- Inspect existing files
- Propose small, reviewable changes
