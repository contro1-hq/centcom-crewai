# centcom-crewai

CrewAI starter kit for Contro1/CENTCOM webhook approval flows.

<!-- contro1:connect:start - generated from contro1.com/docs/connect-an-agent -->
## Connect your CrewAI agent to Contro1

A CrewAI agent runs in your own code, so it connects with an Agent Credential: a key bound to one agent, so every call is attributed to it and nothing in a request can change which agent it is.

1. Register the agent: contro1 init --name "<name>" --framework crewai, and finish the setup link it prints (purpose and owner).
2. Connect the application account under Apps, if it is not connected yet.
3. Give the agent the Actions it needs under Access. It starts with none.
4. Create an Agent Credential for it (Settings, API keys) and store it as CONTRO1_API_KEY in your secret manager.
5. Call Actions from your tools as below. The same credential creates approval requests for work your own code does.

Full guide: [Connect an agent: every path, in full](https://contro1.com/docs/connect-an-agent)

### Run an application Action from a CrewAI tool

Contro1 holds the account and makes the call, so the record is what Contro1 observed. The tool returns what the Action produced; when a person has to approve first, it waits and then returns the result. It never re-submits: a retry could send a second email.

Before writing the input, read the exact input_schema with get_action_contract, or from the Action on the Access page.

Install: `pip install "centcom>=1.5.0"`

```python
import os, uuid
from centcom import CentcomClient, needs_human_resolution

contro1 = CentcomClient(api_key=os.environ["CONTRO1_API_KEY"])  # an Agent Credential

def run_action(action_id: str, input: dict, *, account_mode: str = "shared", **kw):
    """Run a Contro1 Action and return what it produced. Never retries a send."""
    out = contro1.actions.invoke(
        action_id, input,
        authority_mode=kw.pop("authority_mode", "agent_principal"),
        account_mode=account_mode,
        idempotency_key=kw.pop("idempotency_key", str(uuid.uuid4())),
        **kw,
    )
    inv = out["invocation"]
    if inv["state"] == "executed":
        return out["result"]
    if inv["state"] == "awaiting_approval":
        settled = contro1.actions.wait_for_invocation(inv["invocation_id"])
        if needs_human_resolution(settled):
            raise RuntimeError("Outcome unknown; a person must check. Do not retry.")
        return contro1.actions.get_result(settled["invocation_id"])
    raise RuntimeError(f"Not run: {inv['state']} {out.get('not_run', '')}")

from crewai.tools import tool

@tool("List recent emails")
def list_recent_emails(max_results: int = 5) -> list:
    """List the most recent emails in the team mailbox."""
    return run_action("gmail.message.list", {"max_results": max_results})
```

Everything below this section covers the other half: asking a person before a step your own code runs, using the same credential.

<!-- contro1:connect:end -->

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
