# centcom-crewai

CrewAI starter kit for Contro1/CENTCOM webhook approval flows.

## Agent Integration Kit

To save time, give your coding agent this skill. It inspects your system, reports governance gaps, and suggests Contro1 integration (optional):

```
https://contro1.com/agent-kit
```

This starter uses **Contro1 Integration Protocol v1**:

- canonical request object (`Contro1Request`) and response (`Contro1Response`)
- continuation mode: `instruction`
- routing metadata in protocol request
- case correlation via `correlation_id`

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

## Human review vs audit log

Use `create_protocol_request` when a CrewAI task must pause for operator guidance. Pass `execution_id` directly as `correlation_id` - no hashing or prefix needed - so all tasks in the same run appear in one case timeline.

```python
task_output = payload["context"]  # exact CrewAI task output, copied verbatim
reason = task_output.pop("reason", None)  # required field on the task's output model

created = client.create_protocol_request({
    "title": f"CrewAI review for {task_id}",
    "request_type": "review",
    "source": {"integration": "crewai", "run_id": execution_id, "workflow_id": task_id},
    "context": {
        "action": {"tool": task_id, "input": task_output},
        "machine_observed": {"execution_id": execution_id, "task_id": task_id},
        "agent_reported": {"justification": reason},
    },
    "continuation": {"mode": "instruction", "callback_url": callback_url},
    "external_request_id": f"crewai:{execution_id}:{task_id}",
    "correlation_id": execution_id,
})
```

## Send context the reviewer can trust

Build `context` in the bridge from three sources: the exact CrewAI task/tool output copied verbatim, the event that triggered the run, and the agent's own justification - captured by making `reason` a required output field on the CrewAI task so it's produced at decision time, not requested afterward. Keep the split explicit in the payload: verbatim facts under `machine_observed`, model-authored text under `agent_reported`. Agent-reported text should never change routing or risk level, and a review request missing its required justification should fail closed rather than being forwarded to a human to guess. Full pattern: https://contro1.com/docs/requests-api.

Use `log_action` when the crew has already performed an allowed action and you only need audit evidence:

```python
client.log_action(
    action="crewai.task_resume_mapped",
    summary=f"Mapped operator feedback to CrewAI task {task_id}",
    source={"integration": "crewai", "workflow_id": task_id, "run_id": execution_id},
    correlation_id=execution_id,
    in_reply_to={"type": "request", "id": created["id"]},
)
```

## Control Map preview

For requests that use `required_roles` or multi-person approval, Control Map can preview whether routing is satisfiable. Cache the result for 5-15 minutes.

```python
preview = client.post("/requests/control-map", {
    "approval_requirements": {"required_roles": ["manager"], "required_approvals": 1},
    "approval_policy": {"mode": "single", "fail_closed_on_timeout": True},
})

if not preview["satisfiable"]:
    print("Routing setup needed:", preview["warnings"])
```

Still create the review request when the task needs human input; the final signed decision is what resumes or blocks the workflow.

## Production pattern: Agent Plugin

```python
from datetime import datetime, timedelta
from centcom import CentcomClient

class Contro1Plugin:
    def __init__(self, client: CentcomClient, cache_ttl_minutes: int = 10):
        self._client = client
        self._cache: dict = {}
        self._ttl = timedelta(minutes=cache_ttl_minutes)

    def preview_policy(self, approval_requirements: dict, approval_policy: dict) -> dict:
        key = str(sorted(approval_requirements.items()))
        cached = self._cache.get(key)
        if cached and datetime.utcnow() < cached["expires"]:
            return cached["data"]
        result = self._client.post("/requests/control-map", {
            "approval_requirements": approval_requirements,
            "approval_policy": approval_policy,
        })
        self._cache[key] = {"data": result, "expires": datetime.utcnow() + self._ttl}
        return result

    def request_human_review(self, payload: dict) -> dict:
        return self._client.create_protocol_request(payload)

    def log_audit_action(self, payload: dict) -> dict:
        return self._client.log_action(**payload)

    def resume_from_decision(self, case_id: str) -> dict:
        return self._client.get(f"/cases/{case_id}")
```

## Security defaults

- Use env vars only.
- Verify CrewAI inbound webhook auth.
- Verify CENTCOM callback signatures.
- Deduplicate with deterministic idempotency key: `crewai:{execution_id}:{task_id}`.

## Related repositories

- [`centcom`](https://github.com/contro1-hq/centcom)
- [`centcom-langgraph`](https://github.com/contro1-hq/centcom-langgraph)
- [`contro1-microsoft-agent-governance-toolkit-integration`](https://github.com/contro1-hq/contro1-microsoft-agent-governance-toolkit-integration)

## Governance readiness

For teams operating AI in regulated environments:
- [EU AI Act readiness guide](https://contro1.com/guides/eu-ai-act-readiness)
- [US AI Governance readiness guide](https://contro1.com/guides/us-ai-governance-readiness)
