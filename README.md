# centcom-crewai

Official CENTCOM connector guides and examples for CrewAI HITL workflows.

## What this repo provides

- A webhook-first integration playbook for CrewAI human review events.
- Clear mapping between CrewAI kickoff/resume and CENTCOM approvals.
- A skill file for consistent AI-assisted implementation.

## Security defaults (required)

- Use environment variables only. Never hardcode secrets.
- Bridge service credentials:

```bash
CENTCOM_API_KEY=your_centcom_api_key
CENTCOM_WEBHOOK_SECRET=whsec_your_signing_secret
```

- Verify both directions:
  - Inbound CrewAI webhook authentication/signature.
  - Inbound CENTCOM callback signature headers.

## Recommended architecture

1. CrewAI emits review payload to `humanInputWebhook`.
2. Bridge converts review into CENTCOM request with correlation metadata.
3. Operator decides in CENTCOM.
4. Bridge maps decision and calls CrewAI `/resume`.

## Quick Start snippets

Kickoff:

```bash
curl -X POST {BASE_URL}/kickoff \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": { "topic": "AI Research" },
    "humanInputWebhook": {
      "url": "https://your-app.com/crewai/hitl",
      "authentication": { "strategy": "bearer", "token": "your-webhook-secret-token" }
    }
  }'
```

Resume:

```json
{
  "execution_id": "abcd1234",
  "task_id": "review_task",
  "human_feedback": "Approved with rollback plan.",
  "is_approve": true
}
```

## Mapping contract

- CrewAI -> CENTCOM:
  - `execution_id`, `task_id`, summary, risk context.
- CENTCOM request fields:
  - `type`, `question`, `context`, `required_role`, `metadata`.
- CENTCOM -> CrewAI:
  - `is_approve`, `human_feedback`, correlation IDs.

## Production checklist

- Deduplicate by `execution_id + task_id` before resume.
- Add idempotency keys when creating CENTCOM requests.
- Log lifecycle states (received -> queued -> decided -> resumed).
- Keep resume feedback short and actionable.
- Add timeout fallback path for no-response cases.

## Troubleshooting

- Resume rejected: verify payload field names and IDs.
- Duplicate resume calls: deduplicate on stable correlation IDs.
- Missing context in operator screen: ensure metadata includes task details.

## Documentation in this repo

- Guide: `docs/crewai-connector.md`
- Skill: `skills/centcom-crewai.md`

## Related repositories

- [`centcom`](https://github.com/contro1-hq/centcom)
- [`centcom-langgraph`](https://github.com/contro1-hq/centcom-langgraph)
