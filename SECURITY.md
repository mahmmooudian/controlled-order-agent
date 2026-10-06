# Security Policy

Security is a core design concern of the **Controlled Order Agent**.

This project demonstrates a policy-controlled agent architecture with explicit authorization boundaries, human approval for sensitive actions, role-based API access, persistent auditability, and security-focused evaluation.

For the complete technical security architecture, see:

`docs/security.md`

---

## Supported Versions

| Version | Security Support |
|---|---|
| v2.x | Supported |
| v1.0-demo | Archived / demonstration only |

The `v1.0-demo` tag is preserved for historical and educational purposes and is not the current security baseline.

---

## Reporting a Vulnerability

Please do **not** publish vulnerabilities, working exploits, real credentials, tokens, private keys, or sensitive reproduction details in a public GitHub issue.

If GitHub private vulnerability reporting is enabled for this repository, use that mechanism.

Otherwise, contact the repository maintainer privately through the maintainer's GitHub profile before sharing sensitive technical details.

When reporting a vulnerability, include when possible:

- affected component;
- reproduction steps;
- expected behavior;
- observed behavior;
- potential security impact;
- whether a READ or WRITE operation is involved;
- whether authentication, RBAC, policy, or approval boundaries are involved;
- relevant logs with all secrets removed.

---

## Security-Sensitive Areas

Reports are especially relevant when they involve:

- authentication bypass;
- RBAC bypass or privilege escalation;
- unauthorized WRITE execution;
- human-approval bypass;
- approval replay;
- approval reuse across different orders or contexts;
- policy bypass;
- malicious or malformed tool output;
- prompt injection affecting privileged execution;
- duplicate WRITE operations;
- credential or secret leakage;
- unsafe retry behavior;
- audit-trail integrity;
- production exposure of security-simulation features.

---

## Core Security Principles

The project is designed around the following invariants:

```text
Planner decision != authorization

Sensitive WRITE requires policy authorization

Sensitive WRITE requires explicit human approval

Approval is bound to execution context

Approval is one-time use

Tool output is untrusted

API access follows least privilege

Execution is bounded

Security-sensitive failures fail closed

## Security Evaluation

The project includes deterministic security evaluation for:

- approval enforcement;
- unsafe WRITE blocking;
- approval replay protection;
- unwanted action prevention.

Current evaluation results are documented in:

`docs/evaluation.md`