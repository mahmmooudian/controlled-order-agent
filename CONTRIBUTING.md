# Contributing to Controlled Order Agent

Thank you for your interest in contributing to the **Controlled Order Agent**.

This project focuses on building agentic systems in which planning capability is deliberately separated from execution authority.

The repository emphasizes:

- policy-controlled execution;
- human approval for privileged actions;
- context-bound authorization;
- approval replay protection;
- role-based access control;
- persistent auditability;
- structured validation;
- bounded agent execution;
- deterministic security evaluation;
- optional LLM-backed planning without granting the model execution authority.

Contributions should preserve these principles.

---

## Core Architectural Principle

The central rule of the project is:

> **Planner decision != authorization**

A planner may propose what should happen next.

It must not become the authority that determines whether a privileged action is allowed to execute.

The intended control flow is:

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
Authorization Context
    |
    v
One-Time Approval Consumption
    |
    v
WRITE Tool
```

Changes must preserve the separation between:

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

## Supported Python Versions

The project currently supports:

```text
Python >= 3.10
Python < 3.13
```

The CI matrix validates:

```text
Python 3.10
Python 3.11
Python 3.12
```

---

## Development Installation

Install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

For development involving the optional OpenAI planner:

```powershell
python -m pip install -e ".[dev,llm]"
```

For GUI development:

```powershell
python -m pip install -e ".[dev,gui]"
```

For the complete development environment:

```powershell
python -m pip install -e ".[dev,gui,llm]"
```

---

## Project Structure

The authoritative implementation lives under:

```text
src/controlled_agent/
```

Major areas include:

```text
adapters/
api/
approvals/
client/
desktop/
domain/
observability/
persistence/
planners/
policy/
runtime/
security/
services/
tools/
```

Automated tests live under:

```text
tests/
```

The deterministic evaluation framework lives under:

```text
evals/
```

Technical documentation lives under:

```text
docs/
```

The original demonstration implementation is preserved in Git history under:

```text
v1.0-demo
```

New development should target the current:

```text
src/controlled_agent/
```

architecture.

---

## Protected Main Branch

The `main` branch is protected.

Changes should be introduced through a dedicated branch and merged through a pull request after required checks pass.

Direct pushes to `main` are intentionally restricted.

For repository maintainers:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feat/example-change
```

External contributors should normally fork the repository, create a branch in their fork, and open a pull request against `main`.

---

## Branch Naming

Create a dedicated branch for each meaningful change.

Recommended examples:

```text
feat/add-new-tool
fix/approval-validation
security/harden-authentication
test/add-replay-regression
docs/improve-security-guide
refactor/runtime-dependencies
chore/update-tooling
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

Keep branches focused on one logical change.

---

## Coding Guidelines

Prefer code that is:

```text
Explicit
Structured
Typed where practical
Testable
Auditable
Deterministic where security behavior is involved
Fail-closed for sensitive decisions
Separated by responsibility
```

Prefer:

```text
Structured schemas
Dependency injection
Small components
Clear interfaces
Explicit authorization decisions
Explicit error handling
```

Avoid hidden coupling between:

```text
planner logic
policy decisions
authorization
approval state
tool execution
persistence
```

A planner must never bypass the runtime or policy layer to execute a privileged tool directly.

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
LLM boundaries
Runtime configuration
```

The following invariants must remain true:

```text
Planner decision != authorization

Sensitive WRITE requires policy authorization

Sensitive WRITE requires explicit human approval

Approval must match the execution context

Approval must be one-time use

Consumed approval cannot authorize another WRITE

Untrusted tool output cannot authorize WRITE

LLM output cannot authorize WRITE by itself

Execution must remain bounded

Security-sensitive failures should fail closed
```

See:

```text
docs/security.md
```

for the detailed security architecture.

---

## Authentication and RBAC

The API implements bearer authentication and role-based authorization.

Current roles include:

```text
reader
operator
approver
admin
```

Changes to authentication or authorization must preserve least-privilege behavior.

Relevant tests should cover cases such as:

```text
missing credentials

invalid credentials

valid credentials

insufficient role

authorized role

production fail-closed behavior
```

Do not weaken authorization solely to simplify testing or development.

---

## Human Approval

Human approval is a security boundary.

Approval must not be represented as an unrestricted global permission.

Authorization is bound to execution context including information such as:

```text
run_id
action
order_id
context_hash
```

Approved authorization is consumed before a privileged WRITE executes.

A previously consumed approval must not authorize another WRITE.

Changes to approval behavior should include regression tests covering:

```text
valid approval

missing approval

denied approval

mismatched context

approval replay

approval consumption failure
```

---

## Secrets

Never commit real credentials or secrets.

Do not commit:

```text
.env

API keys

Bearer credentials

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

for configuration examples.

The repository also uses GitHub secret scanning and push protection where available.

These controls are additional safeguards and are not a substitute for careful secret handling.

---

## Planner Architecture

The project currently contains two planner implementations:

```text
BasePlanner
    |
    +-- RuleBasedPlanner
    |
    +-- LLMPlanner
```

Both use the same planning abstraction.

Neither planner owns the authorization boundary.

---

## RuleBasedPlanner

`RuleBasedPlanner` is the deterministic reference planner.

It is used for:

```text
offline execution

stable regression testing

deterministic CI validation

production-style evaluation

security evaluation
```

The documented deterministic evaluation baseline uses `RuleBasedPlanner`.

---

## Optional OpenAI LLMPlanner

The repository also includes an optional OpenAI-backed planner:

```text
src/controlled_agent/planners/llm.py
```

The `LLMPlanner`:

```text
produces structured AgentDecision output

receives a restricted operational state

does not execute tools directly

does not own approval

does not bypass policy

does not receive unrestricted runtime authority
```

The OpenAI integration is optional.

It is not required for deterministic production-style evaluation.

Its dedicated unit tests use mocked OpenAI behavior.

They do not prove successful live OpenAI API execution.

---

## Adding a New Planner

New planners should implement the existing planner abstraction.

A planner may propose actions.

It must not directly:

```text
execute privileged tools

override policy decisions

approve its own actions

consume approvals

modify authorization state

bypass validation

receive unnecessary application secrets
```

This requirement applies equally to:

```text
rule-based planners

machine-learning planners

LLM planners

external agent frameworks
```

Planner capability must remain separate from execution authority.

---

## Tests

Every meaningful behavioral change should include or update automated tests.

Run the complete regression suite with:

```powershell
pytest -q
```

The currently validated full regression baseline, with optional LLM dependencies installed, is:

```text
205 passed
```

To reproduce the full baseline:

```powershell
python -m pip install -e ".[dev,llm]"
pytest -q
```

The exact number of tests may increase as new regression coverage is added.

A contribution must not intentionally remove security-critical coverage without a documented reason.

---

## Optional LLMPlanner Tests

Dedicated LLM planner tests can be run with:

```powershell
pytest tests/unit/test_llm_planner.py -q
```

The currently validated result is:

```text
6 passed
```

These tests use mocked OpenAI behavior.

They cover areas including:

```text
required OpenAI configuration

client initialization

restricted state projection

structured AgentDecision parsing

missing structured output handling

credential exclusion from model payload
```

They do not perform live OpenAI API validation.

---

## Targeted Testing

During development, targeted tests may be run first.

Examples:

```powershell
pytest tests/unit -q
```

```powershell
pytest tests/api -q
```

```powershell
pytest tests/security -q
```

```powershell
pytest tests/integration -q
```

Targeted tests are useful during development, but the relevant full regression suite should pass before merge.

---

## Deterministic Evaluation

Changes affecting agent behavior must also pass the production-style evaluation suite:

```powershell
python -m evals.run_evals
```

The current validated baseline is:

```text
Total Cases: 10
Passed Scenarios: 10
Scenario Pass Rate: 100.00%

Correct Tool Selections: 10
Tool Selection Accuracy: 100.00%

Unwanted Actions: 0
Unwanted Action Rate: 0.00%

Approval Enforcement Rate: 100.00%
Unsafe Write Block Rate: 100.00%
Approval Replay Block Rate: 100.00%

Overall Evaluation: PASS
```

The evaluator currently covers scenarios including:

```text
delayed order approved

delayed order denied

delayed order waiting for approval

small delay

no delay

order not found

missing order ID

invalid order ID

tool-output injection

transient timeout recovery
```

Dedicated security probes additionally validate:

```text
unsafe WRITE blocking

approval replay prevention
```

See:

```text
docs/evaluation.md
```

for complete evaluation documentation.

---

## Machine-Readable Evaluation

The evaluation runner supports JSON output:

```powershell
python -m evals.run_evals --json
```

A machine-readable report can also be written to disk:

```powershell
python -m evals.run_evals `
    --json-output evaluation-report.json
```

Evaluation failures return a non-zero process exit code.

This allows the evaluator to act as a CI quality gate.

---

## Code Validation

Before committing changes, run:

```powershell
git diff --check
```

For modified Python files, syntax validation may also be useful:

```powershell
python -m py_compile path\to\file.py
```

For broader source validation:

```powershell
python -m compileall -q src evals
```

For the desktop entry point:

```powershell
python -m py_compile gui_qt.py
```

---

## Continuous Integration

GitHub Actions validates pull requests and protected-branch changes.

The primary CI workflow is defined in:

```text
.github/workflows/ci.yml
```

It includes:

```text
Core tests on Python 3.10

Core tests on Python 3.11

Core tests on Python 3.12

Optional OpenAI planner tests

Production-style deterministic evaluation
```

Required checks should pass before a pull request is merged.

Do not disable or bypass CI checks solely to merge a failing change.

---

## CodeQL

The repository uses GitHub CodeQL for static security analysis.

The workflow is defined in:

```text
.github/workflows/codeql.yml
```

CodeQL analyzes the Python codebase through GitHub Actions.

Security findings should be investigated rather than bypassed solely to make a workflow green.

---

## Dependabot

Dependency update configuration is defined in:

```text
.github/dependabot.yml
```

Dependabot monitors:

```text
Python dependencies

GitHub Actions dependencies
```

Dependency updates are proposed through pull requests so they can pass through the same protected review and CI process as other changes.

Dependency updates should still be reviewed for:

```text
compatibility

security impact

behavioral changes

breaking changes
```

before merge.

---

## Documentation Changes

Documentation must remain consistent with the actual implementation.

Do not document a feature as implemented unless it exists in the repository.

Distinguish clearly between:

```text
Current implementation

Optional implementation

Future work

Production-oriented architecture

Fully deployed production infrastructure
```

The current repository includes both:

```text
RuleBasedPlanner

LLMPlanner
```

`RuleBasedPlanner` remains the deterministic reference planner used for the documented production-style evaluation.

`LLMPlanner` is an implemented optional OpenAI-backed planner.

The LLM integration must not be described as mandatory runtime infrastructure.

---

## Commit Messages

Use clear and descriptive commit messages.

Recommended style:

```text
feat: add persistent run repository

fix: reject mismatched approval context

security: prevent approval replay

test: add RBAC regression coverage

docs: document evaluation architecture

refactor: separate API dependency construction

chore: update development tooling
```

Prefer one logical change per commit.

---

## Pull Requests

The repository uses a pull request template located at:

```text
.github/pull_request_template.md
```

Pull requests should explain what changed and why.

A pull request should:

```text
have a clear purpose

preserve architectural boundaries

include relevant tests

pass required CI checks

pass security evaluation when applicable

pass git diff --check

avoid secrets and generated runtime data

update documentation when behavior changes
```

Security implications should be explained when modifying:

```text
authentication

authorization

approval

policy

WRITE execution

persistence

audit behavior

LLM boundaries
```

---

## Issue Reports

Structured issue forms are available under:

```text
.github/ISSUE_TEMPLATE/
```

Use the bug-report form for reproducible defects.

Use the feature-request form for proposed improvements.

Do not publish sensitive vulnerability details through ordinary public issues.

---

## Adding a New Tool

New tools should be explicitly classified as:

```text
READ
```

or:

```text
WRITE
```

A READ tool must still validate untrusted external output.

A WRITE tool must not execute solely because a planner requested it.

Sensitive WRITE tools should pass through the controlled execution path:

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
Authorization Context
    |
    v
Approval Consumption
    |
    v
WRITE Tool
```

Tests should cover both allowed and blocked execution paths.

---

## Adding New Evaluation Cases

New evaluation scenarios should define:

```text
input

expected tools

expected WRITE behavior

expected final status

expected approval state

security expectation
```

Evaluation scenarios should remain deterministic whenever possible.

Security-sensitive behavior should include both positive and negative test cases.

---

## Reporting Security Issues

Do not report sensitive vulnerabilities through public GitHub issues.

Use the repository's private vulnerability reporting mechanism when available.

Also review:

```text
SECURITY.md
```

for the repository security policy.

Do not include:

```text
real credentials

private tokens

sensitive databases

working secrets

unredacted private user data
```

in issues, pull requests, logs, or reports.

---

## Definition of Done

A change is considered ready when:

```text
Implementation is complete

Relevant tests exist

Required tests pass

Evaluation passes when agent behavior is affected

git diff --check is clean

No secrets are included

Documentation reflects actual behavior

Security boundaries remain intact

Required GitHub checks pass

The pull request is ready for protected-main merge
```

---

## License and Contribution Terms

By contributing to this repository, you confirm that you have the right to submit the contributed work under the repository license.

The repository license is defined in:

```text
LICENSE
```

Contributions accepted into the repository are expected to be compatible with those license terms.
