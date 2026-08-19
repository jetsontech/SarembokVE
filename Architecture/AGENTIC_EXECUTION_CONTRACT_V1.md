# Sarembok Agentic Execution Contract v1

## Purpose

Define the platform-neutral contract for long-horizon autonomous work in Sarembok.

Sarembok agents do not directly own infrastructure, model vendors, or user interfaces. They operate through controlled capabilities and produce durable execution state.

## Execution loop

1. Understand task and constraints.
2. Create a bounded plan.
3. Select an allowed capability.
4. Execute one action.
5. Observe the result.
6. Validate the result against the plan and policy.
7. Checkpoint state.
8. Continue, recover, escalate, or complete.

## Horizon dimensions

Every autonomous task has:

- `max_time_seconds`: wall-clock execution boundary.
- `max_steps`: action-loop boundary.
- `checkpoint_interval`: maximum actions between durable checkpoints.
- `max_retries`: bounded recovery attempts.
- `human_escalation`: policy for requesting human approval.

These are system controls, not claims about foundation-model capability.

## Required state

An execution record must be able to represent:

- execution ID
- agent ID
- task ID
- current state
- current step
- plan version
- capability/action name
- action input reference
- observation/result reference
- validation status
- checkpoint reference
- retry count
- timestamps
- failure/escalation reason

## State machine

```text
QUEUED
  -> PLANNING
  -> EXECUTING
  -> OBSERVING
  -> VALIDATING
  -> CHECKPOINTED
  -> EXECUTING ...

VALIDATING -> COMPLETED
VALIDATING -> RECOVERY
VALIDATING -> ESCALATED
EXECUTING  -> FAILED
RECOVERY   -> EXECUTING
```

## Safety boundaries

- No unbounded action loops.
- No hidden persistence of credentials.
- No capability execution outside an explicit policy boundary.
- Destructive or externally consequential actions may require human approval.
- Every autonomous execution must have an inspectable state trail.
- Failed actions must not silently masquerade as successful actions.

## Vendor neutrality

The execution contract is independent of OpenAI, Microsoft, NVIDIA, Anthropic, xAI, Google, or any other model/provider. A provider can supply reasoning, perception, speech, or other capabilities, but Sarembok owns the orchestration contract, state, policy, identity, memory, and execution lifecycle.

## Long-horizon principle

Sarembok should increase autonomy by improving planning, checkpointing, observation, validation, recovery, and capability composition—not merely by increasing model context or token budgets.
