import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .benchmark import ROOT
from .doctor import inspect_sandbox
from .engine import Campaign
from .providers import GENERATORS, load_env, readiness
from .runner import check


def main():
    parser = argparse.ArgumentParser(description="CrossExam: find broken software your evals accept")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Execute a complete evaluation campaign")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Generate real attacks/tests with the selected providers and route with Subquadratic; no silent fallback")
    mode.add_argument("--subq-only", action="store_true", help="Live Subquadratic risk routing with explicitly local attacks and proposals")
    run.add_argument("--out", type=Path)
    run.add_argument("--generator", choices=GENERATORS, default="openai", help="Live attack provider (default: OpenAI); also authors tests unless --test-author is set")
    run.add_argument("--test-author", choices=GENERATORS, help="Independent test author (default: same provider as --generator, fresh context)")
    run.add_argument("--mongo", action="store_true", help="Archive completed evidence to the configured MongoDB database")
    archive = sub.add_parser("archive", help="Archive an existing completed campaign to MongoDB; safe to retry")
    archive.add_argument("folder", type=Path)
    verify_archive = sub.add_parser("verify-archive", help="Read archived artifacts back from MongoDB and verify every SHA-256")
    verify_archive.add_argument("folder", type=Path)
    agent = sub.add_parser("agent", help="Run the Fetch uAgents verification service against MongoDB")
    agent.add_argument("--port", type=int, default=8868)
    agent.add_argument("--out", type=Path, default=ROOT / "runs" / "fetch-agent")
    agent_verify = sub.add_parser("agent-verify", help="Ask a Fetch verifier agent to check a patch and verify its signed receipt")
    agent_verify.add_argument("candidate", type=Path)
    agent_verify.add_argument("--campaign", required=True)
    agent_verify.add_argument("--address", required=True)
    agent_verify.add_argument("--endpoint", default="http://127.0.0.1:8868/submit")
    agent_verify.add_argument("--out", type=Path, required=True)
    sub.add_parser("doctor", help="Probe sandbox boundaries and report provider readiness")
    serve = sub.add_parser("serve", help="Start the local evidence workspace")
    serve.add_argument("--port", type=int, default=8847)
    replay = sub.add_parser("replay", help="Replay a saved counterexample in the sandbox")
    replay.add_argument("folder", type=Path)
    verify = sub.add_parser("verify", help="Gate an implementation against a frozen suite; exits 1 on failure")
    verify.add_argument("candidate", type=Path)
    verify.add_argument("--suite", required=True, type=Path)
    args = parser.parse_args()
    load_env(ROOT / ".env")
    try:
        if args.command == "doctor":
            print(json.dumps({**inspect_sandbox(), "providers_configured": readiness()}, indent=2))
        elif args.command == "serve":
            from .server import serve
            serve(args.port)
        elif args.command == "run":
            if args.test_author and not args.live:
                raise ValueError("--test-author requires --live")
            required = {args.generator, args.test_author or args.generator, "subquadratic"} if args.live else {"subquadratic"} if args.subq_only else set()
            missing = sorted(provider for provider in required if not readiness()[provider])
            if missing:
                raise RuntimeError(f"Configure credited provider keys for: {', '.join(missing)} (see .env.example)")
            if args.mongo:
                from .storage import MongoArchive
                with MongoArchive():
                    pass  # Fail before any paid generation if storage is unavailable.
            inspection = inspect_sandbox()
            print(f"Sandbox: {inspection['runtime']} — all enforcement probes passed", flush=True)
            out = args.out or ROOT / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            def emit(e):
                print(f"[{e['kind']}] {e['message']}", flush=True)
            report = Campaign(out, args.live, emit, subq_only=args.subq_only, generator=args.generator, test_author=args.test_author).run()
            print(f"\nAudit: {report['audit_before']['detected']}/{report['audit_before']['total']} → {report['audit_after']['detected']}/{report['audit_after']['total']} defects detected")
            print(f"Correct controls rejected: {report['audit_after']['false_rejections']}/{report['audit_after']['controls']}")
            print(f"Evidence: {out.resolve() / 'report.json'}")
            if args.mongo:
                from .storage import archive_campaign
                print(json.dumps(archive_campaign(out), indent=2))
        elif args.command == "archive":
            from .storage import archive_campaign
            print(json.dumps(archive_campaign(args.folder), indent=2))
        elif args.command == "verify-archive":
            from .storage import MongoArchive
            with MongoArchive() as archive:
                print(json.dumps(archive.verify(args.folder), indent=2))
        elif args.command == "agent":
            from .agent import serve_agent
            serve_agent(args.out, args.port)
        elif args.command == "agent-verify":
            import asyncio
            from .agent import request_verification
            proof = asyncio.run(request_verification(args.candidate, args.campaign, args.address, args.endpoint, args.out))
            print(json.dumps({"verdict": proof["receipt"]["verdict"], "signature_verified": proof["signature_verified"],
                              "evidence_id": proof["evidence_id"], "receipt": str(args.out)}, indent=2))
            return {"PASS": 0, "BLOCKED": 1, "ERROR": 2}[proof["receipt"]["verdict"]]
        elif args.command == "replay":
            inspect_sandbox()
            scenario = json.loads((args.folder / "scenario.json").read_text())
            files = {name: (args.folder / name).read_text() for name in ("service.py", "cache.py")}
            result = check(files, [scenario])
            print(json.dumps(result, indent=2))
            return 1 if result["passed"] or result["error"] else 0
        elif args.command == "verify":
            inspect_sandbox()
            record = json.loads(args.suite.read_text())
            suite = record["suite"] if isinstance(record, dict) else record
            from .scenarios import validate_suite
            suite = validate_suite(suite)
            files = {name: (args.candidate / name).read_text() for name in ("service.py", "cache.py")}
            result = check(files, suite)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"CrossExam: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
