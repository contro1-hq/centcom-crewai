---
name: centcom-crewai
description: Guide for integrating CrewAI webhook HITL flows with CENTCOM approvals.
user_invocable: true
---

# CENTCOM + CrewAI Skill

Use this skill when a user wants CrewAI human review managed in CENTCOM.

## Implementation steps

1. Configure CrewAI task/workflow to emit webhook HITL events.
2. Convert incoming review event into a CENTCOM request.
3. Route operator decision back into CrewAI resume API.
4. Ensure idempotency on bridge events.

## Short example

```python
req = centcom.create_request(
    type="approval",
    question="Approve CrewAI task output?",
    context=task_output,
    metadata={"execution_id": execution_id, "task_id": task_id},
)
```
