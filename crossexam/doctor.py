"""Probe actual sandbox restrictions before trusting execution."""

import json
from pathlib import Path
import tempfile

from .runner import execute, runtime


def inspect_sandbox():
    backend = runtime()
    with tempfile.TemporaryDirectory(prefix="crossexam-private-") as tmp:
        canary = Path(tmp) / "private-canary.txt"
        canary.write_text("not mounted into candidate")
        probe = '''import os, socket
class Service:
    def handle(self, action):
        results = {}
        try:
            open(CANARY).read()
            results["private_files_blocked"] = False
        except (PermissionError, FileNotFoundError):
            results["private_files_blocked"] = True
        try:
            open(OUTSIDE, "w").write("should never be possible")
            results["outside_writes_blocked"] = False
        except (PermissionError, FileNotFoundError, OSError):
            results["outside_writes_blocked"] = True
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(("1.1.1.1", 53))
            results["network_blocked"] = False
        except (PermissionError, OSError):
            results["network_blocked"] = True
        results["credentials_absent"] = not any(os.environ.get(k) for k in ("MODEL_API_KEY", "SUBQ_API_KEY", "GH_TOKEN", "GITHUB_TOKEN"))
        return results
'''.replace("CANARY", repr(str(canary))).replace("OUTSIDE", repr(str(Path(tmp) / "outside.txt")))
        result = execute({"service.py": probe, "cache.py": ""}, [{"actions": [{}]}], backend)
        if result["error"]:
            raise RuntimeError("Sandbox probe could not execute: " + result["error"])
        checks = result["outputs"][0][0]
        if not all(checks.values()) or len(checks) != 4:
            raise RuntimeError("Sandbox enforcement failed: " + json.dumps(checks))
        return {"runtime": backend, "checks": checks, "note": "A practical isolation probe, not a proof against all OS-level escapes."}
