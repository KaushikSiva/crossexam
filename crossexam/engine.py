"""Versioned evaluation improvement with a separate final audit."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

from .benchmark import ROOT, FIXTURE, Variant, corpus, source
from .providers import Partners
from .runner import check, minimize, runtime
from .scenarios import baseline, strengthened, digest, validate_suite, audit_scenarios


def promotion_decision(previous, proposed):
    before = {r["id"] for r in previous["rows"] if r["detected"] and not r["correct"]}
    after = {r["id"] for r in proposed["rows"] if r["detected"] and not r["correct"]}
    accepted = proposed["false_rejections"] == 0 and before < after
    return accepted, ("Promoted: new validation defects caught, no regressions or false rejections" if accepted
                      else "Rejected: no strict validation gain or a correctness regression")


class Campaign:
    def __init__(self, output, live=False, emit=None, subq_only=False, generator="openai", test_author=None):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.live = live
        self.use_subq = live or subq_only
        self.callback = emit or (lambda e: None)
        self.events = []
        self.partner = Partners(self.output / "provider-calls", generator=generator, test_author=test_author) if self.use_subq else None
        self.backend = runtime()
        self.cache = {}
        self.versions = []

    def event(self, kind, message, **data):
        previous = self.events[-1]["sha256"] if self.events else "0" * 64
        event = dict(sequence=len(self.events), timestamp=datetime.now(timezone.utc).isoformat(),
                     kind=kind, message=message, data=data, previous=previous)
        event["sha256"] = digest(event)
        self.events.append(event)
        with (self.output / "events.jsonl").open("a") as f:
            f.write(json.dumps(event) + "\n")
        self.callback(event)

    def measure(self, variants, suite):
        def one(v):
            key = digest(v.files) + digest(suite)
            if key not in self.cache:
                self.cache[key] = check(v.files, suite, self.backend)
            result = self.cache[key]
            return {"id": v.id, "title": v.title, "family": v.family, "split": v.split,
                    "correct": v.correct, "detected": not result["passed"],
                    "error": result["error"], "seconds": round(result["seconds"], 4),
                    "failure": result["failure"]}
        # Host threads orchestrate separate OS sandboxes. This is not agent delegation.
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(one, variants))
        bad = [r for r in rows if not r["correct"]]
        controls = [r for r in rows if r["correct"]]
        return {"detected": sum(r["detected"] for r in bad), "total": len(bad),
                "false_rejections": sum(r["detected"] for r in controls), "controls": len(controls),
                "seconds": round(sum(r["seconds"] for r in rows), 4), "rows": rows}

    def freeze(self, number, suite, rationale, origin):
        suite = validate_suite(suite)
        record = {"version": number, "suite": suite, "suite_sha256": digest(suite),
                  "rationale": rationale, "origin": origin}
        (self.output / f"suite-v{number}.json").write_text(json.dumps(record, indent=2))
        self.event("suite_frozen", f"Suite v{number} frozen before evaluation", version=number, sha256=record["suite_sha256"], scenarios=len(suite))
        return record

    def run(self):
        started = time.perf_counter()
        variants = corpus()
        discovery = [v for v in variants if v.split == "discovery"]
        validation = [v for v in variants if v.split in ("validation", "control")]
        audit = [v for v in variants if v.split in ("audit", "control")]
        base = baseline()
        current = base
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        generation_label = self.partner.label if self.partner else "fixtures"
        if self.live and self.partner.test_author != self.partner.generator:
            generation_label += f" attacker + {self.partner.test_author_label} test author"
        manifest = {"schema": 2, "mode": f"live {generation_label} + Subquadratic" if self.live else "live Subquadratic + local proposals" if self.use_subq else "local fixtures",
                    "created_at": datetime.now(timezone.utc).isoformat(), "commit": commit,
                    "benchmark_revision": "relay-reservations-v2-30-per-split",
                    "python_version": sys.version, "platform": platform.platform(),
                    "runtime": self.backend, "contract_sha256": digest((FIXTURE / "contract.txt").read_text()),
                    "oracle_sha256": digest((ROOT / "crossexam" / "oracle.py").read_text()),
                    "engine_sources": {p.name: digest(p.read_text()) for p in sorted((ROOT / "crossexam").glob("*.py"))},
                    "corpus_sha256": digest([asdict(v) for v in variants]),
                    "audit_input_sha256": digest(audit_scenarios()),
                    "proposal_protocol": {"rounds": 4 if self.live else 3, "generator": self.partner.generator if self.live else "fixtures",
                        "test_author": self.partner.test_author if self.live else "fixtures",
                        "feedback": "aggregate validation counts and decisions only" if self.live else "none",
                        "discovery_probes": "hand-authored contract probes", "injected_rollback": not self.live,
                        "audit_scope": "Public synthetic corpus; withheld from model prompts, previously observed by project authors"},
                    "split_counts": {s: sum(v.split == s for v in variants) for s in ("discovery", "validation", "audit", "control")}}
        (self.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
        self.event("start", "Manifest sealed. Final audit is withheld from proposal generation.", **manifest)
        initial = self.freeze(0, base, "Existing happy-path tests", "hand-authored baseline")
        base_score = self.measure(validation, base)
        initial.update(accepted=True, validation=base_score, active_version=0, decision="Baseline")
        self.versions.append(initial)
        current_score = base_score
        active_version = 0

        if self.use_subq:
            self.event("routing", "Subquadratic is prioritizing contract risks from repository context")
            routing = self.partner.route(base)
        else:
            routing = {"order": ["tenant_isolation", "idempotency", "payload_binding", "inventory", "validation"],
                       "scores": {}, "origin": "fixed local order", "note": "No API calls made in this mode."}
        if self.live:
            self.event("attack", f"{self.partner.label} is proposing an adversarial implementation in a separate context")
            proposed = self.partner.attack(base, routing["order"][0])
            generated = Variant("M01", proposed["title"], proposed["family"], "discovery", proposed["files"], origin=f"live {self.partner.label}")
            discovery = [generated] + discovery
            (self.output / "generated-attack.json").write_text(json.dumps(asdict(generated), indent=2))
        self.event("routing_complete", "Risk exploration order selected", **routing)

        counterexamples = []
        for v in discovery:
            old = check(v.files, base, self.backend)
            probe = check(v.files, strengthened(), self.backend)
            if old["passed"] and probe["failure"]:
                failure = minimize(v.files, probe["failure"], self.backend)
                diff = "\n".join("\n".join(difflib.unified_diff(source()[name].splitlines(), v.files[name].splitlines(), fromfile=f"a/{name}", tofile=f"b/{name}", lineterm="")) for name in source() if source()[name] != v.files[name])
                item = {"id": v.id, "title": v.title, "family": v.family, "origin": v.origin,
                        "baseline_passed": True, "baseline_checks": len(base), "witness": failure,
                        "diff": diff, "source_sha256": digest(v.files)}
                counterexamples.append(item)
                folder = self.output / "counterexamples" / v.id
                folder.mkdir(parents=True)
                for name, content in v.files.items():
                    (folder / name).write_text(content)
                (folder / "scenario.json").write_text(json.dumps(failure, indent=2))
                self.event("counterexample", f"{v.id}: existing tests pass; contract fails", **item)
            else:
                self.event("attack_rejected", f"{v.id}: not a demonstrated blind spot", baseline_passed=old["passed"], reproduced=bool(probe["failure"]), origin=v.origin)

        order = routing["order"]
        groups = [order] * 4 if self.live else [order[:1], order[1:3], order[3:]]
        feedback = []
        for n, group in enumerate(groups, 1):
            visible = [{"family": c["family"], "witness": c["witness"]} for c in counterexamples if c["family"] in group]
            if self.live:
                # Adapt priorities to executable discovery results; no validation/audit source enters context.
                unresolved = {v.family for v in discovery if check(v.files, current, self.backend)["passed"]}
                group = sorted(order, key=lambda family: family not in unresolved)
                self.event("proposal", f"{self.partner.test_author_label} is independently generating test proposal {n}", families=group)
                added, rationale = self.partner.propose(current, visible, group, n, feedback=feedback)
                origin = f"live {self.partner.test_author_label}; fresh context, implementation withheld"
            else:
                added = [c for c in strengthened()[len(base):] if c["family"] in group]
                rationale = "Exercise " + ", ".join(f.replace("_", " ") for f in group)
                origin = "hand-authored local proposal"
            seen = {digest(c["actions"]) for c in current}
            candidate = list(current)
            for item in added:
                key = digest(item["actions"])
                if key not in seen:
                    candidate.append(item)
                    seen.add(key)
            record = self.freeze(n, candidate, rationale, origin)
            score = self.measure(validation, candidate)
            accepted, decision = promotion_decision(current_score, score)
            if accepted:
                current, current_score, active_version = candidate, score, n
            record.update(accepted=accepted, validation=score, active_version=active_version, decision=decision)
            self.versions.append(record)
            self.event("promotion" if accepted else "rejection", decision, version=n, active_version=active_version,
                       detected=score["detected"], total=score["total"], false_rejections=score["false_rejections"])
            feedback.append({"round": n, "accepted": accepted, "detected": score["detected"], "total": score["total"],
                             "false_rejections": score["false_rejections"], "decision": decision,
                             "proposed_inputs": added})

        if not self.live:
            # Fixture mode only: never count this as a real model mistake.
            regression = self.freeze(4, base, "Regression challenge: reduce execution cost by returning to the smoke suite", "system-injected rollback demonstration")
            regression_accepted, regression_decision = promotion_decision(current_score, base_score)
            regression.update(accepted=regression_accepted, validation=base_score, active_version=active_version,
                              decision=regression_decision)
            self.versions.append(regression)
            self.event("rejection", regression["decision"], version=4, active_version=active_version,
                       detected=base_score["detected"], total=base_score["total"], false_rejections=base_score["false_rejections"])

        self.event("audit_opened", "Learning finished. Opening the final audit once; no further proposals are allowed.", active_version=active_version)
        audit_before = self.measure(audit, base)
        audit_after = self.measure(audit, current)
        input_audit = self.measure([v for v in variants if v.correct], audit_scenarios())
        report = {"schema": 2, "manifest": manifest, "routing": routing, "versions": self.versions,
                  "active_version": active_version, "counterexamples": counterexamples,
                  "validation_before": base_score, "validation_after": current_score,
                  "audit_before": audit_before, "audit_after": audit_after,
                  "fresh_input_controls": input_audit, "provider_calls": self.partner.calls if self.partner else [],
                  "elapsed_seconds": round(time.perf_counter() - started, 3),
                  "limitations": ["Synthetic, hand-authored benchmark; these are not real-world defect detection rates.",
                                  "Public audit variants were previously observed by project authors; withheld from model prompts, not a new secret benchmark.",
                                  "Repeated aggregate validation feedback can overfit this small validation set.",
                                  "Discovery combines seeded defects and, in live mode, one generated patch; discovery probes remain hand-authored.",
                                  "Held-out variants exercise familiar defect families, not wholly new classes of bugs.",
                                  "Separate contexts and different model providers can still share correlated blind spots.",
                                  "The specification and independent oracle remain trusted assumptions.",
                                  "This prototype verifies a fixed sequential reservation API; it is not a universal repository verifier."]}
        self.event("complete", "Final audit complete. Evidence and suite versions saved.", audit_detected=audit_after["detected"],
                   audit_total=audit_after["total"], false_rejections=audit_after["false_rejections"])
        report["events"] = self.events
        report["event_root_sha256"] = self.events[-1]["sha256"]
        (self.output / "report.json").write_text(json.dumps(report, indent=2))
        return report
