"""Loopback-only UI server. Read-only public evidence can be exported separately."""

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
from urllib.parse import urlparse

from .benchmark import ROOT
from .doctor import inspect_sandbox
from .engine import Campaign
from .providers import load_env, readiness


def serve(port=8847):
    state = {"busy": False, "events": [], "report": None, "error": None}
    lock = threading.Lock()
    candidates = sorted((ROOT / "runs").glob("*/report.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        state["report"] = json.loads(candidates[0].read_text())

    def run_job(mode):
        try:
            inspect_sandbox()
            output = ROOT / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            def emit(event):
                with lock:
                    state["events"].append(event)
            report = Campaign(output, live=mode == "live", emit=emit, subq_only=mode == "subq").run()
            with lock:
                state["report"] = report
        except Exception as exc:
            with lock:
                state["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            with lock:
                state["busy"] = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def send(self, status, body, content_type="application/json"):
            encoded = json.dumps(body).encode() if content_type == "application/json" else body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/state":
                load_env(ROOT / ".env")
                with lock:
                    self.send(200, {**state, "providers": readiness(), "local": True})
            elif path == "/api/report":
                with lock:
                    self.send(200 if state["report"] else 404, state["report"] or {"error": "No completed run"})
            elif path in ("/", "/index.html", "/app.js", "/style.css", "/favicon.svg"):
                file = ROOT / "web" / ("index.html" if path == "/" else path[1:])
                if not file.exists():
                    self.send(404, {"error": "Not found"})
                else:
                    self.send(200, file.read_bytes(), mimetypes.guess_type(str(file))[0] or "text/plain")
            else:
                self.send(404, {"error": "Not found"})

        def do_POST(self):
            if self.path != "/api/run":
                self.send(404, {"error": "Not found"})
                return
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")
            if host not in (f"127.0.0.1:{port}", f"localhost:{port}") or (origin and origin != f"http://{host}") or self.headers.get("X-CrossExam") != "local-workspace":
                self.send(403, {"error": "Local same-origin request required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024:
                    raise ValueError("Invalid payload length")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or payload.get("mode") not in ("local", "subq", "live"):
                    raise ValueError("Mode must be local, subq, or live")
            except (ValueError, TypeError):
                self.send(400, {"error": "Invalid run request"})
                return
            load_env(ROOT / ".env")
            live = payload["mode"] == "live"
            if live and not (readiness()["openai"] and readiness()["subquadratic"]):
                self.send(409, {"error": "Configure OPENAI_API_KEY and SUBQ_API_KEY in .env"})
                return
            if payload["mode"] == "subq" and not readiness()["subquadratic"]:
                self.send(409, {"error": "Configure a credited SUBQ_API_KEY in .env"})
                return
            with lock:
                if state["busy"]:
                    self.send(409, {"error": "A campaign is already running"})
                    return
                state.update(busy=True, events=[], error=None)
            threading.Thread(target=run_job, args=(payload["mode"],), daemon=True).start()
            self.send(202, {"started": True, "mode": payload["mode"]})

    print(f"CrossExam workspace: http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
