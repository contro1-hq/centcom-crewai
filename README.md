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

## Human review vs audit log

Use `create_protocol_request` when a CrewAI task must pause for operator guidance. Use `log_action` when the crew has already performed an allowed action and you only need audit evidence.

```python
thread_id = f"thr_crewai_{stable_hash(execution_id)}"

created = client.create_protocol_request({
    "title": f"CrewAI review for {task_id}",
    "request_type": "review",
    "source": {"integration": "crewai", "run_id": execution_id, "workflow_id": task_id},
    "continuation": {"mode": "instruction", "callback_url": callback_url},
    "external_request_id": f"crewai:{execution_id}:{task_id}",
    "thread_id": thread_id,
})

client.log_action(
    action="crewai.task_resume_mapped",
    summary=f"Mapped operator feedback to CrewAI task {task_id}",
    source={"integration": "crewai", "workflow_id": task_id, "run_id": execution_id},
    thread_id=thread_id,
    in_reply_to={"type": "request", "id": created["id"]},
)
```

See the full bridge example at https://github.com/contro1-hq/centcom-crewai/blob/main/examples/crewai_bridge.py.
