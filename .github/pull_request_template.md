## Summary

Describe what this pull request changes and why.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Security improvement
- [ ] CI / tooling
- [ ] Other

## Security Impact

Does this change affect any of the following?

- Authentication
- RBAC
- Human approval
- Policy enforcement
- Tool execution
- Persistent state
- Audit logging
- LLM planner boundaries
- Secret handling

If yes, explain the impact and the controls that remain in place.

## Validation

- [ ] `pytest -q`
- [ ] `python -m evals.run_evals`
- [ ] `git diff --check`
- [ ] Relevant new or updated tests were added
- [ ] No secrets or sensitive data were committed

## Control-Boundary Check

- [ ] Planner output remains a proposal rather than authorization.
- [ ] Sensitive WRITE operations cannot bypass policy and approval controls.
- [ ] External or model-generated content is treated as untrusted input.
- [ ] Security-sensitive failure paths fail closed where applicable.

## Additional Notes

Add screenshots, logs, architecture notes, migration considerations, or other context if needed.