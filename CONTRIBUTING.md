# Contributing to Controlled Order Agent

Thank you for your interest in contributing to the **Controlled Order Agent**.

This project focuses on building agentic systems with explicit control boundaries, policy enforcement, human approval, persistent auditability, and security-oriented evaluation.

Contributions should preserve those principles.

---

## Development Philosophy

The core architectural rule is:

> **The planner may propose an action, but it must never become the authority that authorizes a sensitive action.**

Changes should preserve the separation between:

```text
Planning
Policy
Validation
Authentication
Authorization
Human Approval
Tool Execution
Persistence
Audit
```

Sensitive WRITE operations must remain behind explicit policy and authorization boundaries.

---

## Requirements

Supported Python versions:

```text
Python >= 3.10
Python < 3.13
```

Install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

For GUI development:

```powershell
python -m pip install -e ".[dev,gui]"
```

---

## Project Structure

The authoritative implementation lives under:

```text
src/controlled_agent/
```

Major areas include:

```text
api/
client/
domain/
persistence/
planners/
policy/
runtime/
security/
services/
tools/
```

Tests live under:

```text
tests/
```

Production-style evaluation lives under:

```text
evals/
```

The historical v1 demonstration is preserved in Git history under:

```text
v1.0-demo
```

New development should target the current `src/controlled_agent` architecture.

---

## Creating a Development Branch

Create a dedicated branch for each meaningful change.

Examples:

```powershell
git switch -c feat/add-new-tool
```

```powershell
git switch -c fix/approval-validation
```

```powershell
git switch -c docs/improve-security-guide
```

Recommended prefixes:

```text
feat/
fix/
security/
test/
docs/
refactor/
chore/
```

---

## Coding Guidelines

Keep changes focused and easy to review.

Prefer:

```text
Explicit behavior

Small components

Typed interfaces

Structured schemas

Dependency injection

Deterministic tests

Fail-closed security behavior

Clear separation of responsibilities
```

Avoid introducing hidden coupling between:

```text
planner logic

policy decisions

authorization

tool execution
```

A planner should never directly bypass the runtime or policy layer to execute a privileged tool.

---

## Security Requirements

Changes affecting sensitive behavior require additional care.

Security-sensitive areas include:

```text
Authentication

RBAC

Approval handling

Approval persistence

Approval consumption

Policy enforcement

WRITE tools

Tool validation

Retry behavior

Secret handling

Audit logging
```

A change must not weaken these invariants:

```text
Planner decision != authorization

Sensitive WRITE requires policy authorization

Sensitive WRITE requires explicit approval

Approval must match execution context

Approval must be one-time use

Untrusted tool output cannot authorize WRITE

Execution must remain bounded

Security failures should fail closed
```

See:

```text
docs/security.md
```

for the complete security architecture.

---

## Secrets

Never commit real credentials.

Do not commit:

```text
.env

API keys

access tokens

passwords

private keys

production credentials

sensitive runtime databases
```

Use:

```text
.env.example
```

only for configuration examples.

---

## Tests

Every behavioral change should include or update automated tests.

Run the complete regression suite before submitting changes:

```powershell
pytest -q
```

Current validated baseline:

```text
199 passed
```

A contribution should not intentionally reduce test coverage of security-critical behavior.

---

## Targeted Testing

During development, targeted tests may be run first.

Example:

```powershell
pytest tests\unit -q
```

or:

```powershell
pytest tests\api -q
```

However, the complete suite must still pass before the change is considered ready.

---

## Production-Style Evaluation

Changes affecting agent behavior must also pass the evaluation suite:

```powershell
python -m evals.run_evals
```

The expected final result is:

```text
Overall Evaluation: PASS
```

The current evaluation includes checks for:

```text
Tool selection

Approval enforcement

Unsafe WRITE blocking

Approval replay protection

Unwanted actions

Tool-output injection

Transient timeout recovery
```

See:

```text
docs/evaluation.md
```

for full evaluation documentation.

---

## Machine-Readable Evaluation

The evaluation runner also supports JSON output:

```powershell
python -m evals.run_evals --json
```

or:

```powershell
python -m evals.run_evals `
    --json-output evaluation-report.json
```

Evaluation failures return a non-zero process exit code.

---

## Code Validation

Before committing changes, run:

```powershell
git diff --check
```

This detects common whitespace problems.

For modified Python files, syntax validation can also be performed with:

```powershell
python -m py_compile path\to\file.py
```

---

## Documentation Changes

Documentation should remain consistent with the actual implementation.

Do not document features as implemented unless they are present and tested.

In particular, distinguish between:

```text
Current implementation

Future work

Production-oriented architecture

Fully deployed production infrastructure
```

The project currently uses:

```text
RuleBasedPlanner
```

as its active deterministic planner.

External LLM integration is an optional future extension and should not be presented as a required active runtime dependency.

---

## Commit Messages

Use clear, descriptive commit messages.

Recommended style:

```text
feat: add persistent run repository

fix: reject mismatched approval context

security: prevent approval replay

test: add RBAC regression coverage

docs: document evaluation architecture

refactor: separate API dependency construction

chore: clean legacy project files
```

Prefer one logical change per commit.

---

## Pull Requests

A contribution should be ready for review before opening a pull request.

The change should:

```text
Have a clear purpose

Preserve architectural boundaries

Include relevant tests

Pass the complete test suite

Pass security evaluation when applicable

Pass git diff --check

Avoid secrets and generated runtime data

Update documentation when behavior changes
```

Explain security implications when modifying:

```text
authentication

authorization

approval

policy

WRITE execution
```

---

## Adding a New Tool

New tools should be classified explicitly as:

```text
READ
```

or:

```text
WRITE
```

A READ tool must still validate untrusted external output.

A WRITE tool must not be executed solely because a planner requested it.

Sensitive WRITE tools should pass through:

```text
Planner
    |
    v
Runtime
    |
    v
Policy
    |
    v
Validation
    |
    v
Human Approval
    |
    v
Authorization
    |
    v
WRITE Tool
```

Tests should verify both allowed and blocked execution paths.

---

## Adding a New Planner

New planners should implement the existing planner abstraction.

The planner must only propose actions.

It must not directly:

```text
access approval storage

override policy

execute privileged tools

modify authorization state
```

This requirement applies equally to deterministic, machine-learning, or LLM-based planners.

---

## Adding New Evaluation Cases

New evaluation scenarios should define:

```text
Input

Expected tools

Expected WRITE behavior

Expected final status

Expected approval state

Security expectation
```

Evaluation scenarios should be deterministic whenever possible.

---

## Reporting Security Issues

Do not report sensitive vulnerabilities through public issues.

Follow the repository security policy:

```text
SECURITY.md
```

---

## Definition of Done

A change is considered ready when:

```text
Implementation is complete

Relevant tests exist

pytest -q passes

Evaluation passes when agent behavior is affected

git diff --check is clean

No secrets are included

Documentation reflects actual behavior

Security boundaries remain intact
```

---

## License and Contribution Terms

By contributing to this repository, you confirm that you have the right to submit the contributed work under the repository's selected license.

The final repository license is defined by the root-level `LICENSE` file.