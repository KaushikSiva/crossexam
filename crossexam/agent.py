"""Fetch uAgents verification protocol over signed, local HTTP messages.

No Agentverse registration, token transfers, or model calls occur here.
The verifier retrieves a frozen evaluation from MongoDB and executes it.
"""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import uuid

from .doctor import inspect_sandbox
from .runner import check
from .scenarios import digest, validate_suite
from .storage import MongoArchive, StorageError

try:
    from pydantic.v1 import Field
    from uagents import Agent, Context, Model
    from uagents.communication import send_sync_message
    from uagents.resolver import RulesBasedResolver
    from uagents_core.identity import Identity
    import uvicorn
except ImportError:
    raise RuntimeError("Fetch verification agent needs: pip install -r requirements-fetch-agent.txt") from None


class VerifyRequest(Model):
    request_id: str = Field(min_length=1, max_length=80)
    campaign_id: str = Field(regex=r"^[a-f0-9]{64}$")
    files: dict[str, str]


class VerifyResponse(Model):
    receipt_json: str
    signer: str
    signature: str


class LocalVerificationAgent(Agent):
    """Pin uAgents to loopback without publishing an identity to Agentverse."""

    def start_registration_loop(self):
        pass

    async def _update_agent_status(self, active):
        pass

    async def start_server(self):
        # uAgents 0.26.1's default server binds all interfaces. Use its ASGI
        # protocol handler with an explicitly loopback-bound Uvicorn server.
        config = uvicorn.Config(self._server, host="127.0.0.1", port=self._port, log_level="warning")
        await uvicorn.Server(config).serve()


def evaluate_request(message, requester, archive):
    if set(message.files) != {"service.py", "cache.py"} or any(len(v) > 64000 for v in message.files.values()):
        raise ValueError("Candidate must contain only service.py and cache.py, at most 64,000 characters each")
    report = archive.read_report(message.campaign_id)
    active = next((v for v in report["versions"] if v["version"] == report["active_version"]), None)
    if active is None:
        raise StorageError("Archived campaign has no active evaluation")
    suite = validate_suite(active["suite"])
    if not active["accepted"] or digest(suite) != active["suite_sha256"]:
        raise StorageError("Archived active evaluation failed integrity checks")
    result = check(message.files, suite)
    return {"schema": 1, "request_id": message.request_id, "requester": requester,
            "campaign_id": message.campaign_id, "candidate_sha256": digest(message.files),
            "suite_sha256": digest(suite), "suite_version": active["version"],
            "event_root_sha256": report["event_root_sha256"], "scenarios": len(suite),
            "verdict": "ERROR" if result["error"] else "PASS" if result["passed"] else "BLOCKED",
            "result": result, "checked_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Synthetic sequential reservation API; a pass is not a general safety guarantee"}


def make_agent(output, port=8868):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    seed = os.environ.get("FETCH_AGENT_SEED")
    if not seed:
        seed_path = output / "identity.seed"
        if not seed_path.exists():
            fd = os.open(seed_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_hex(32))
        seed = seed_path.read_text().strip()
    agent = LocalVerificationAgent(name="crossexam-verifier", seed=seed, port=port,
        endpoint=f"http://127.0.0.1:{port}/submit", enable_agent_inspector=False,
        publish_agent_details=False, mark_inactive_on_shutdown=False, report_events=False,
        store_message_history=False, shutdown_timeout=5)

    @agent.on_message(model=VerifyRequest, replies=VerifyResponse)
    async def verify(ctx: Context, sender: str, message: VerifyRequest):
        def work():
            with MongoArchive() as archive:
                receipt = evaluate_request(message, sender, archive)
                evidence_id = digest(receipt)
                signed = VerifyResponse(receipt_json=json.dumps(receipt, sort_keys=True),
                                        signer=agent.address, signature=agent.sign_digest(bytes.fromhex(evidence_id)))
                proof = {"_id": evidence_id, "request": message.model_dump(), "response": signed.model_dump(),
                         "verdict": receipt["verdict"], "campaign_id": message.campaign_id}
                try:
                    result = archive.db.verifications.update_one({"_id": evidence_id}, {"$setOnInsert": proof}, upsert=True)
                    if not result.acknowledged:
                        raise StorageError("Verification evidence write was not acknowledged")
                except archive.driver_error:
                    raise StorageError("Verification evidence could not be stored") from None
                folder = output / "verifications"
                folder.mkdir(exist_ok=True)
                (folder / f"{evidence_id}.json").write_text(json.dumps(proof, indent=2))
                return signed
        try:
            response = await asyncio.to_thread(work)
        except (StorageError, ValueError, RuntimeError, OSError):
            receipt = {"schema": 1, "request_id": message.request_id, "requester": sender,
                       "campaign_id": message.campaign_id, "candidate_sha256": digest(message.files),
                       "verdict": "ERROR", "error": "Verification could not complete; check the campaign, candidate, sandbox, and database"}
            response = VerifyResponse(receipt_json=json.dumps(receipt, sort_keys=True), signer=agent.address,
                                      signature=agent.sign_digest(bytes.fromhex(digest(receipt))))
        await ctx.send(sender, response)

    info = {"provider": "Fetch.ai uAgents", "address": agent.address,
            "endpoint": f"http://127.0.0.1:{port}/submit", "transport": "local HTTP",
            "request_schema_digest": Model.build_schema_digest(VerifyRequest),
            "response_schema_digest": Model.build_schema_digest(VerifyResponse),
            "agentverse_registered": False}
    (output / "agent-info.json").write_text(json.dumps(info, indent=2))
    return agent, info


def serve_agent(output, port):
    inspect_sandbox()
    with MongoArchive():
        pass
    agent, info = make_agent(output, port)
    print(json.dumps(info, indent=2), flush=True)
    agent.run()


def validate_response(response, message, address, requester):
    if not isinstance(response, VerifyResponse) or response.signer != address:
        raise RuntimeError("Verification response has an unexpected signer")
    receipt = json.loads(response.receipt_json)
    try:
        valid = Identity.verify_digest(address, bytes.fromhex(digest(receipt)), response.signature)
    except Exception:
        valid = False
    if not valid:
        raise RuntimeError("Verification receipt signature is invalid")
    if (receipt.get("request_id") != message.request_id or receipt.get("requester") != requester
            or receipt.get("campaign_id") != message.campaign_id or receipt.get("candidate_sha256") != digest(message.files)):
        raise RuntimeError("Verification receipt does not match this request")
    return {"evidence_id": digest(receipt), "signature_verified": True, "response": response.model_dump(), "receipt": receipt}


async def request_verification(candidate, campaign_id, address, endpoint, output):
    files = {name: (Path(candidate) / name).read_text() for name in ("service.py", "cache.py")}
    message = VerifyRequest(request_id=uuid.uuid4().hex, campaign_id=campaign_id, files=files)
    sender = Identity.generate()
    response = await send_sync_message(destination=address, message=message, response_type=VerifyResponse,
                                       sender=sender, resolver=RulesBasedResolver({address: endpoint}), timeout=45)
    proof = validate_response(response, message, address, sender.address)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2))
    return proof
