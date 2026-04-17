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

See `examples/crewai_bridge.py` for a runnable webhook + resume template.

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
    metadata={"execution_id": execution_id, "task_id": task_id},
)
```

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

## Common mistakes to avoid

- Losing correlation IDs between kickoff and resume.
- Not re-sending webhook URLs in CrewAI resume flow when required.
- Sending verbose, unstructured feedback back into the run context.
