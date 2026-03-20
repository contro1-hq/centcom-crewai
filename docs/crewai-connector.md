# CrewAI Connector Guide

This guide shows how to connect CrewAI webhook-based HITL with CENTCOM.

## Prerequisites

- CrewAI deployment that supports webhook HITL
- Service endpoint to receive CrewAI HITL callbacks
- `centcom` client available in the bridge service

## Environment setup (bridge service)

```bash
CENTCOM_API_KEY=your_centcom_api_key
CENTCOM_WEBHOOK_SECRET=whsec_your_signing_secret
```

## Recommended flow

1. Start CrewAI execution with `humanInputWebhook`.
2. Receive review payload in your bridge service.
3. Create CENTCOM request with task context.
4. Submit CENTCOM decision back to CrewAI resume endpoint.

## Short example (kickoff)

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

## Short example (resume)

```bash
curl -X POST {BASE_URL}/resume \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "abcd1234",
    "task_id": "review_task",
    "human_feedback": "Approved with rollback plan.",
    "is_approve": true
  }'
```

## Bridge mapping contract

- CrewAI -> CENTCOM:
  - `execution_id`, `task_id`, output summary, risk context
- CENTCOM request fields:
  - `type`, `question`, `context`, `required_role`, `metadata`
- CENTCOM -> CrewAI resume:
  - `is_approve`, `human_feedback`, correlation IDs

## Production checklist

- Verify inbound webhook authentication/signature from CrewAI.
- Verify signature headers on CENTCOM callbacks with `CENTCOM_WEBHOOK_SECRET`.
- Store `execution_id + task_id` to prevent duplicate resume calls.
- Use idempotency for CENTCOM request creation.
- Keep feedback concise and relevant before sending to CrewAI resume.
- Add fallback path for timeout/denial.

## Troubleshooting

- Resume rejected by CrewAI: verify required fields and IDs.
- Duplicate retries: deduplicate by `execution_id + task_id`.
- Missing context in review: include required fields in `metadata`.
