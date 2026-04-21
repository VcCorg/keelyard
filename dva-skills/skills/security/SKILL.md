---
name: security
description: >-
  Security patterns, secret management, auth flows, OWASP guidelines.
  Use this skill when reviewing or writing security-sensitive code.
---

# Security Best Practices

## Secret Management

- Never hardcode secrets, API keys, or passwords in source code
- Use environment variables or secret managers (GCP Secret Manager, Vault)
- Add sensitive patterns to `.gitignore` (`.env`, `*.pem`, `*.key`)
- Rotate credentials regularly

## Authentication & Authorization

- Use established libraries (Spring Security, Passport.js, etc.)
- Validate JWT tokens server-side; check expiry and issuer
- Implement least-privilege access control
- Use RBAC or ABAC for fine-grained permissions

## Input Validation

- Validate all user input at the boundary (controller/handler layer)
- Use parameterized queries — never concatenate SQL strings
- Sanitize HTML output to prevent XSS
- Validate content types, file uploads, and request sizes

## Common Vulnerabilities (OWASP Top 10)

| Risk | Prevention |
|------|-----------|
| Injection | Parameterized queries, input validation |
| Broken Auth | MFA, session management, token rotation |
| Sensitive Data Exposure | Encrypt at rest and in transit, mask logs |
| XXE | Disable external entity processing |
| Broken Access Control | Server-side authorization checks |
| Security Misconfiguration | Harden defaults, disable debug in prod |
| XSS | Output encoding, CSP headers |
| Insecure Deserialization | Validate and restrict deserialized types |
| Known Vulnerabilities | Keep dependencies updated, run scans |
| Insufficient Logging | Log auth events, access violations |

## Guidelines

- Review dependencies for known CVEs (`npm audit`, `safety check`, `snyk`)
- Log security events but never log sensitive data
- Use HTTPS everywhere; set HSTS headers
- Implement rate limiting on auth endpoints
- Fail securely — deny by default
