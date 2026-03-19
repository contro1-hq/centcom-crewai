# CrewAI Connector Guide

This guide shows how to connect CrewAI webhook-based HITL with CENTCOM.

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
