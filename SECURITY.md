# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Onshape Export Manager, please report it privately by emailing the maintainers. Do NOT open a public issue.

## Supported Versions

| Version | Supported |
|---|---|
| Latest release | ✅ |
| Older releases | ❌ |

## Security Design

- Passwords are hashed with **scrypt** (N=2^14, r=8, p=1) — memory-hard, GPU-resistant
- TOTP two-factor authentication uses RFC 6238 (HMAC-SHA1, 30s step)
- Session tokens are SHA-256 hashed before storage
- API keys can be stored as `env:VARIABLE_NAME` references instead of plaintext
- All configuration models use `extra="forbid"` to reject unknown keys
- Backup restore uses path traversal prevention

## Dependency Scanning

Dependencies are scanned via `pip-audit` in CI. To scan locally:

```bash
pip install pip-audit
pip-audit
```
