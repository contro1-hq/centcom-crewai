# Contro1 CrewAI Skill

Use this when wiring CrewAI task review or crew-level approval into Contro1.

## Rules

- Use `execution_id` to derive the Contro1 `thread_id`.
- Use `external_request_id = crewai:{execution_id}:{task_id}` for idempotency.
- Use `create_protocol_request` for task reviews that need human input before resume.
- Use `log_action` for autonomous CrewAI actions and for callback-to-resume mappings.
- Reply inside an existing thread with `in_reply_to={"type": "request", "id": request_id}`.

## Resume mapping

After the Contro1 callback is verified, convert it to CrewAI's resume payload and log the mapping:

```python
client.log_action(
    action="crewai.task_resume_mapped",
    summary=f"Mapped operator response to CrewAI task {task_id}",
    source={"integration": "crewai", "workflow_id": task_id, "run_id": execution_id},
    outcome="success" if approved else "partial",
    thread_id=thread_id,
    in_reply_to={"type": "request", "id": request_id},
)
```
---
name: centcom-crewai
description: Guide for integrating CrewAI webhook HITL flows with CENTCOM approvals.
user_invocable: true
---

# CENTCOM + CrewAI Skill

Use this skill when a user wants CrewAI human review managed in CENTCOM with a webhook bridge.

## Installation

```bash
pip install centcom flask python-dotenv
```

## Required configuration

```bash
CENTCOM_API_KEY=your_centcom_api_key
CENTCOM_BASE_URL=https://api.contro1.com/api/centcom/v1
CENTCOM_WEBHOOK_SECRET=whsec_your_signing_secret
```

Initialize the client from environment:

```python
import os
from centcom import CentcomClient

centcom = CentcomClient(api_key=os.environ["CENTCOM_API_KEY"])
```

## Webhook endpoint (production)

CENTCOM sends the operator's decision to a URL you own. Expose an endpoint that:
1. Verifies `centcom-signature` using `CENTCOM_WEBHOOK_SECRET`.
2. Reads `approved` / `value` from the payload body.
3. Calls the CrewAI `/resume` endpoint with mapped feedback.

Use the runnable webhook + resume template at https://github.com/contro1-hq/centcom-crewai/blob/main/examples/crewai_bridge.py.

## What to build

Build a bridge service between CrewAI HITL webhooks and CENTCOM:

1. Receive CrewAI human review payload.
2. Create CENTCOM request with task context.
3. Wait for operator decision.
4. Call CrewAI resume endpoint with mapped feedback.

## Implementation steps

1. Configure CrewAI task/workflow to emit webhook HITL events.
2. Persist `execution_id` + `task_id` for idempotent resume.
3. Convert incoming review event into CENTCOM `approval` or `free_text` request.
4. Include CrewAI IDs in CENTCOM `metadata`.
5. On CENTCOM response, map:
   - operator approve -> `is_approve: true`
   - operator reject -> `is_approve: false`
6. Call CrewAI `/resume` endpoint and include required webhook URLs when your CrewAI setup requires them.

## Bridge request example

```python
req = centcom.create_request(
    type="approval",
    question="Approve CrewAI task output?",
    context=task_output,
    required_role="manager",
    approval_policy={
        "mode": "threshold",
        "required_approvals": 2,
        "required_roles": ["manager", "admin"],
        "separation_of_duties": True,
        "fail_closed_on_timeout": True,
    },
    metadata={"execution_id": execution_id, "task_id": task_id},
)
```

For high-risk task output, require two-person approval. The first approval is audit-only and CrewAI should not resume until Contro1 sends the final callback after quorum, rejection, or timeout.

## Resume mapping example

```json
{
  "execution_id": "abcd1234",
  "task_id": "review_task",
  "human_feedback": "Approved with rollback plan",
  "is_approve": true
}
```

## Reliability checklist

- Verify webhook auth/signature on inbound CrewAI events.
- Verify CENTCOM callback signatures using `CENTCOM_WEBHOOK_SECRET`.
- Add idempotency keys for CENTCOM request creation.
- Deduplicate resume calls by `execution_id + task_id`.
- Log transitions: received -> sent_to_centcom -> decided -> resumed.
- Fail closed if a multi-approval request times out before quorum.

## Common mistakes to avoid

- Losing correlation IDs between kickoff and resume.
- Not re-sending webhook URLs in CrewAI resume flow when required.
- Sending verbose, unstructured feedback back into the run context.
- Resuming CrewAI after the first approval when quorum is still pending.

## Full reference links

- Repo: https://github.com/contro1-hq/centcom-crewai
- Runnable bridge example: https://github.com/contro1-hq/centcom-crewai/blob/main/examples/crewai_bridge.py
- Skill file source: https://github.com/contro1-hq/centcom-crewai/blob/main/skills/centcom-crewai.md
- Core Python SDK: https://github.com/contro1-hq/centcom
- Protocol docs: https://contro1.com/docs/audit-records-and-threads
