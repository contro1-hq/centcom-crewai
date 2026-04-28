"""CrewAI webhook bridge template for Contro1 approvals."""

from __future__ import annotations

import json
import os
import hashlib
from typing import Any

from centcom import CentcomClient, verify_webhook
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)

CENTCOM_API_KEY = os.environ["CENTCOM_API_KEY"]
CENTCOM_BASE_URL = os.environ.get("CENTCOM_BASE_URL", "https://api.contro1.com/api/centcom/v1")
CENTCOM_WEBHOOK_SECRET = os.environ["CENTCOM_WEBHOOK_SECRET"]
CREWAI_WEBHOOK_TOKEN = os.environ["CREWAI_WEBHOOK_TOKEN"]
PORT = int(os.environ.get("BRIDGE_PORT", "8082"))

client = CentcomClient(api_key=CENTCOM_API_KEY, base_url=CENTCOM_BASE_URL)
PENDING: dict[str, dict[str, str]] = {}


def contro1_thread_id(value: str) -> str:
    if value.startswith("thr_") and len(value) <= 68:
        return value
    return f"thr_crewai_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:32]}"


@app.post("/crewai/hitl")
def crewai_hitl():
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {CREWAI_WEBHOOK_TOKEN}":
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(force=True, silent=False) or {}
    execution_id = str(payload.get("execution_id", "")).strip()
    task_id = str(payload.get("task_id", "")).strip()
    summary = str(payload.get("summary", "CrewAI requested human review")).strip()
    context: Any = payload.get("context", {})

    if not execution_id or not task_id:
        return jsonify({"error": "execution_id and task_id are required"}), 400

    thread_id = contro1_thread_id(execution_id)

    protocol_request = {
        "title": f"CrewAI review for {task_id}",
        "description": summary,
        "request_type": "review",
        "source": {
            "integration": "crewai",
            "framework": "crewai",
            "run_id": execution_id,
            "workflow_id": task_id,
        },
        "routing": {
            "required_role": "manager",
            "priority": "normal",
        },
        "context": {
            "tool_name": "crewai_resume",
            "tool_input": context,
            "summary": summary,
        },
        "continuation": {
            "mode": "instruction",
            "callback_url": f"http://localhost:{PORT}/centcom-callback",
        },
        "external_request_id": f"crewai:{execution_id}:{task_id}",
        "thread_id": thread_id,
        "metadata": {
            "execution_id": execution_id,
            "task_id": task_id,
            "contro1_thread_id": thread_id,
        },
    }

    created = client.create_protocol_request(protocol_request)
    key = f"{execution_id}:{task_id}"
    PENDING[key] = {"request_id": created["id"]}

    return jsonify({"request_id": created["id"], "status": "queued"})


@app.post("/centcom-callback")
def centcom_callback():
    raw_body = request.get_data(as_text=True)
    signature = request.headers.get("X-CentCom-Signature", "")
    timestamp = request.headers.get("X-CentCom-Timestamp", "")

    if not verify_webhook(raw_body, signature, timestamp, CENTCOM_WEBHOOK_SECRET):
        return jsonify({"error": "invalid signature"}), 401

    payload = json.loads(raw_body)
    response = payload.get("response") or {}
    approved = bool(response.get("approved")) if isinstance(response, dict) else False
    message = ""
    if isinstance(response, dict):
        message = str(response.get("comment") or response.get("message") or "")

    metadata = payload.get("metadata") or {}
    execution_id = str(metadata.get("execution_id", ""))
    task_id = str(metadata.get("task_id", ""))
    thread_id = str(metadata.get("contro1_thread_id") or "")

    # Map to CrewAI resume payload shape.
    resume_payload = {
        "execution_id": execution_id,
        "task_id": task_id,
        "is_approve": approved,
        "human_feedback": message or ("Approved by operator" if approved else "Rejected by operator"),
    }
    if thread_id and payload.get("request_id"):
        client.log_action(
            action="crewai.task_resume_mapped",
            summary=f"Mapped operator response to CrewAI task {task_id}",
            source={
                "integration": "crewai",
                "workflow_id": task_id,
                "run_id": execution_id,
            },
            outcome="success" if approved else "partial",
            thread_id=thread_id,
            in_reply_to={"type": "request", "id": payload["request_id"]},
        )
    app.logger.info("Mapped CrewAI resume payload: %s", resume_payload)
    return jsonify({"status": "ok", "resume_payload": resume_payload})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
