# Sarembok Engineering Agent

This package is the first executable Sarembok Engineering Agent slice. It is a
provider-neutral execution controller, not a model integration.

It accepts a bounded `ExecutionPlan` from any planner and owns the Sarembok
execution loop: capability lookup, separate permission checks, authorized tool
invocation, observation, validation, bounded retries, durable checkpoints, and
append-only audit records. `RepositoryReadTool` and `ValidationTool` provide
safe read and allowlisted validation boundaries. Mutating tools can be added
only with an explicit `ToolDescriptor`, policy permission, and tests.

The controller does not call OpenAI, Anthropic, Microsoft, or another provider.
Provider integrations may implement planning later through the plan boundary;
they do not receive direct infrastructure authority.

## Remote terminal / SSH connector

`RemoteTerminalTool` exposes the `server.remote_terminal` Sarembok capability.
It requires both `server.connect` and `server.execute`, accepts only explicitly
allowlisted commands, supports dry-run, bounds captured output, and delegates
the connection to `OpenSSHTransport`. `RemoteServer.from_environment()` reads
`SAREMBOK_SSH_HOST`, `SAREMBOK_SSH_USER`, `SAREMBOK_SSH_PORT`, and an optional
`SAREMBOK_SSH_IDENTITY_FILE`; passwords are never stored or emitted to audit.

Example operator configuration:

```text
SAREMBOK_SSH_HOST=15.204.173.205
SAREMBOK_SSH_USER=ubuntu
SAREMBOK_SSH_PORT=22
```

For production automation, use an SSH key or agent and a managed known_hosts
entry. Interactive password login is intentionally outside autonomous
execution and must not be placed in plans, environment files, or logs.

Run the focused tests from this directory with:

```text
python -m unittest -v test_engineering_agent.py
```

The implementation follows `Architecture/AGENTIC_CAPABILITY_MODEL_V1.md` and
`Architecture/AGENTIC_EXECUTION_CONTRACT_V1.md`. Each execution step produces
an audit event, and each checkpoint is fsync'd before execution continues.

