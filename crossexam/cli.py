import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .benchmark import ROOT
from .doctor import inspect_sandbox
from .engine import Campaign
from .providers import load_env, readiness
from .runner import check


def main():
    parser = argparse.ArgumentParser(description="CrossExam: find broken software your evals accept")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Execute a complete evaluation campaign")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Generate real attacks/tests with OpenAI and route with Subquadratic; no silent fallback")
    mode.add_argument("--subq-only", action="store_true", help="Live Subquadratic risk routing with explicitly local attacks and proposals")
    run.add_argument("--out", type=Path)
    run.add_argument("--generator", choices=("openai", "meta"), default="openai", help="Live generation provider (default: OpenAI)")
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
            inspection = inspect_sandbox()
            print(f"Sandbox: {inspection['runtime']} — all enforcement probes passed", flush=True)
            if args.live and not (readiness()[args.generator] and readiness()["subquadratic"]):
                raise RuntimeError(f"Live mode needs the {args.generator} key and SUBQ_API_KEY with usable credits")
            if args.subq_only and not readiness()["subquadratic"]:
                raise RuntimeError("Subquadratic mode needs SUBQ_API_KEY with usable credits")
            out = args.out or ROOT / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            def emit(e):
                print(f"[{e['kind']}] {e['message']}", flush=True)
            report = Campaign(out, args.live, emit, subq_only=args.subq_only, generator=args.generator).run()
            print(f"\nAudit: {report['audit_before']['detected']}/{report['audit_before']['total']} → {report['audit_after']['detected']}/{report['audit_after']['total']} defects detected")
            print(f"Correct controls rejected: {report['audit_after']['false_rejections']}/{report['audit_after']['controls']}")
            print(f"Evidence: {out.resolve() / 'report.json'}")
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
