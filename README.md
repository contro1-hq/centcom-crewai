# centcom-crewai

CrewAI starter kit for Contro1/CENTCOM webhook approval flows.

## Protocol

This starter uses **Contro1 Integration Protocol v1**:

- canonical request object (`Contro1Request`)
- canonical response object (`Contro1Response`)
- continuation mode: `instruction`
- routing metadata in protocol request

## Files

- `docs/crewai-connector.md`
- `skills/centcom-crewai.md`
- `.env.example`
- `requirements.txt`
- `examples/crewai_bridge.py`

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python examples/crewai_bridge.py
```

Bridge runs on `http://localhost:8082`.

## Smoke Test

Simulate CrewAI webhook event:

```bash
curl -X POST http://localhost:8082/crewai/hitl \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "exec-77",
    "task_id": "task-review",
    "summary": "Approve publishing plan?"
  }'
```

Then approve/deny in CENTCOM and verify `/centcom-callback` logs a mapped CrewAI resume payload.

## Security defaults

- Use env vars only.
- Verify CrewAI inbound webhook auth.
- Verify CENTCOM callback signatures.
- Deduplicate with deterministic idempotency key: `crewai:{execution_id}:{task_id}`.
