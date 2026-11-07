"""Execute candidate code away from credentials, expected values, and benchmark.

macOS: deny-by-default Seatbelt profile with a bounded temporary workspace.
Linux/other: Docker with no network, read-only filesystem, capability drop,
non-root UID, pids/memory/CPU limits. No unsandboxed fallback.
"""

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

from .oracle import evaluate

WORKER = Path(__file__).with_name("worker.py")


class SandboxUnavailable(RuntimeError):
    pass


def runtime():
    if platform.system() == "Darwin" and shutil.which("sandbox-exec"):
        return "macOS Seatbelt"
    if shutil.which("docker"):
        p = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, timeout=5)
        if p.returncode == 0:
            return "Docker"
    raise SandboxUnavailable("No supported sandbox. Start Docker and pull python:3.12-slim. There is no host-execution fallback.")


def profile(folder):
    # JSON string escaping also suits the quoted strings of Seatbelt's syntax.
    paths = [str(folder), str(Path(sys.base_prefix).resolve()), "/System", "/usr/lib", "/usr/share", "/Library/Apple", "/opt/homebrew/Cellar", "/opt/homebrew/opt"]
    reads = " ".join(f"(subpath {json.dumps(p)})" for p in paths)
    return f'''(version 1)
(deny default)
(allow file-read-metadata)
(allow file-read* {reads} (literal "/") (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))
(allow file-write* (subpath {json.dumps(str(folder))}) (literal "/dev/null"))
(allow process-exec (subpath {json.dumps(str(Path(sys.base_prefix).resolve()))}))
(allow sysctl-read)
(allow mach-lookup)
'''


def execute(files, scenarios, backend=None):
    backend = backend or runtime()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="crossexam-") as tmp:
        folder = Path(tmp).resolve()
        folder.chmod(0o755)
        if set(files) != {"service.py", "cache.py"}:
            raise ValueError("Candidate must contain exactly service.py and cache.py")
        for name, content in files.items():
            if not isinstance(content, str) or len(content) > 64000:
                raise ValueError("Candidate file is invalid or too large")
            (folder / name).write_text(content)
        (folder / "worker.py").write_text(WORKER.read_text())
        payload = "".join(json.dumps(c["actions"], allow_nan=False) + "\n" for c in scenarios).encode()
        env = {"PATH": "/usr/bin:/bin", "HOME": str(folder), "LANG": "en_US.UTF-8", "PYTHONHASHSEED": "0"}
        if backend == "macOS Seatbelt":
            command = ["sandbox-exec", "-p", profile(folder), str(Path(sys.executable).resolve()), "-I", "-B", str(folder / "worker.py")]
        else:
            command = ["docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
                       "--security-opt=no-new-privileges", "--pids-limit=16", "--memory=128m", "--cpus=1",
                       "--user=65534:65534", "--ulimit=fsize=1048576:1048576", "-i",
                       "-v", f"{folder}:/app:ro", "-w", "/app", "python:3.12-slim", "python", "-I", "-B", "/app/worker.py"]
        with (folder / "stdout").open("wb") as out, (folder / "stderr").open("wb") as err:
            try:
                p = subprocess.run(command, input=payload, stdout=out, stderr=err,
                                   cwd=folder, env=env if backend == "macOS Seatbelt" else None,
                                   timeout=12)
                code = p.returncode
            except subprocess.TimeoutExpired:
                code = -124
        raw = (folder / "stdout").read_bytes()[:1048576]
        stderr = (folder / "stderr").read_text(errors="replace")[:2000]
        if code != 0:
            return {"outputs": None, "error": f"Candidate exited {code}: {stderr}", "seconds": time.perf_counter() - started}
        try:
            output = [json.loads(line) for line in raw.splitlines()]
            if len(output) != len(scenarios):
                raise ValueError("Wrong number of scenario results")
            for result, scenario in zip(output, scenarios):
                if not isinstance(result, list) or len(result) != len(scenario["actions"]):
                    raise ValueError("Wrong number of action results")
        except (ValueError, UnicodeError) as exc:
            return {"outputs": None, "error": f"Invalid candidate protocol: {exc}", "seconds": time.perf_counter() - started}
        return {"outputs": output, "error": None, "seconds": time.perf_counter() - started}


def check(files, suite, backend=None):
    execution = execute(files, suite, backend)
    results = []
    if execution["error"]:
        return {"passed": False, "error": execution["error"], "checks": [], "seconds": execution["seconds"], "failure": None}
    for scenario, actual in zip(suite, execution["outputs"]):
        expected = evaluate(scenario["actions"])
        same = json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
        results.append(dict(name=scenario["name"], family=scenario["family"], passed=same,
                            actions=scenario["actions"], expected=expected, actual=actual))
    return {"passed": all(r["passed"] for r in results), "error": None, "checks": results,
            "seconds": execution["seconds"], "failure": next((r for r in results if not r["passed"]), None)}


def minimize(files, scenario, backend=None):
    """Find a 1-minimal failing action subsequence; not a globally minimal proof."""
    current = dict(scenario, actions=list(scenario["actions"]))
    changed = True
    while changed and len(current["actions"]) > 1:
        changed = False
        for i in range(len(current["actions"])):
            candidate = dict(current, actions=current["actions"][:i] + current["actions"][i + 1:])
            result = check(files, [candidate], backend)
            if not result["passed"] and not result["error"]:
                current = candidate
                changed = True
                break
    return check(files, [current], backend)["failure"]
