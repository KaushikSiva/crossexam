"""Opt-in MongoDB evidence archive; local artifacts remain the source of truth."""

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


class StorageError(RuntimeError):
    pass


class MongoArchive:
    def __init__(self):
        uri = os.environ.get("MONGODB_URI")
        if not uri:
            raise StorageError("MongoDB archive needs MONGODB_URI in .env")
        try:
            from pymongo import MongoClient
            from pymongo.errors import PyMongoError
        except ImportError:
            raise StorageError("MongoDB archive needs the optional driver: pip install -r requirements-mongodb.txt") from None
        self.driver_error = PyMongoError
        self.client = None
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000,
                                      socketTimeoutMS=10000, timeoutMS=15000, appname="CrossExam")
            self.database_name = os.environ.get("MONGODB_DATABASE") or "crossexam"
            self.deployment = "local" if urlsplit(uri).hostname in ("127.0.0.1", "localhost", "::1") else "remote"
            self.db = self.client[self.database_name]
            self.client.admin.command("ping")
        except (PyMongoError, ValueError):
            self.close()
            # Driver errors can contain connection strings and credentials.
            raise StorageError("MongoDB connection failed; check MONGODB_URI, access rules, and database name") from None

    def close(self):
        if self.client is not None:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def archive(self, folder):
        folder = Path(folder)
        report_path = folder / "report.json"
        report = json.loads(report_path.read_text())
        if not isinstance(report, dict) or report.get("schema") != 2 or not report.get("event_root_sha256"):
            raise StorageError("Archive requires a completed CrossExam schema-2 report")
        # Explicit artifact patterns exclude .env, arbitrary files, and credentials.
        paths = {report_path}
        for pattern in ("manifest.json", "events.jsonl", "suite-v*.json", "generated-attack.json",
                        "provider-calls/*.json", "counterexamples/*/scenario.json",
                        "counterexamples/*/service.py", "counterexamples/*/cache.py"):
            paths.update(folder.glob(pattern))
        artifacts = []
        for path in sorted(paths):
            if not path.is_file() or not path.resolve().is_relative_to(folder.resolve()):
                raise StorageError("Evidence artifacts must be files within the campaign folder")
            # Leave room under MongoDB's 16 MiB document limit; reject before writes.
            if path.stat().st_size > 15_000_000:
                raise StorageError("An evidence artifact exceeds the 15 MB archive limit; local evidence is intact")
            data = path.read_bytes()
            artifacts.append({"path": path.relative_to(folder).as_posix(),
                              "sha256": hashlib.sha256(data).hexdigest(), "content": data.decode("utf-8")})
        report_sha = next(a["sha256"] for a in artifacts if a["path"] == "report.json")
        manifest = report["manifest"]
        record = {"_id": report_sha, "schema": 1, "mode": manifest["mode"],
                  "created_at": manifest["created_at"], "event_root_sha256": report["event_root_sha256"],
                  "audit_detected": report["audit_after"]["detected"], "audit_total": report["audit_after"]["total"],
                  "false_rejections": report["audit_after"]["false_rejections"],
                  "artifacts": [{"path": a["path"], "sha256": a["sha256"]} for a in artifacts]}
        try:
            # Content-addressed upserts make retries safe. The campaign record is
            # committed last, so a visible campaign references uploaded artifacts.
            for artifact in artifacts:
                result = self.db.artifacts.update_one({"_id": artifact["sha256"]},
                    {"$setOnInsert": {"content": artifact["content"]}}, upsert=True)
                if not result.acknowledged:
                    raise StorageError("MongoDB archive requires acknowledged writes; local evidence is intact")
            result = self.db.campaigns.update_one({"_id": report_sha}, {"$setOnInsert": record}, upsert=True)
            if not result.acknowledged:
                raise StorageError("MongoDB archive requires acknowledged writes; local evidence is intact")
        except self.driver_error:
            raise StorageError("MongoDB archive failed; local evidence is intact. Retry with the archive command") from None
        receipt = {"provider": "mongodb", "database": self.database_name, "campaign_id": report_sha,
                   "artifacts": len(artifacts), "status": "complete", "deployment": self.deployment,
                   "event_root_sha256": report["event_root_sha256"]}
        (folder / "mongodb-receipt.json").write_text(json.dumps(receipt, indent=2))
        return receipt

    def verify(self, folder):
        """Read every archived artifact back and check its content hash."""
        folder = Path(folder)
        report_sha = hashlib.sha256((folder / "report.json").read_bytes()).hexdigest()
        try:
            record = self.db.campaigns.find_one({"_id": report_sha})
            if not record:
                raise StorageError("This report has no completed MongoDB archive")
            for reference in record["artifacts"]:
                artifact = self.db.artifacts.find_one({"_id": reference["sha256"]})
                if not artifact or hashlib.sha256(artifact["content"].encode()).hexdigest() != reference["sha256"]:
                    raise StorageError("MongoDB evidence verification failed: missing or changed artifact")
            if not any(a["path"] == "report.json" and a["sha256"] == report_sha for a in record["artifacts"]):
                raise StorageError("MongoDB archive does not reference the exact local report")
        except self.driver_error:
            raise StorageError("MongoDB readback failed; check database connectivity") from None
        result = {"provider": "mongodb", "status": "verified", "deployment": self.deployment,
                  "campaign_id": report_sha, "artifacts_verified": len(record["artifacts"]),
                  "event_root_sha256": record["event_root_sha256"]}
        (folder / "mongodb-verification.json").write_text(json.dumps(result, indent=2))
        return result

    def read_report(self, campaign_id):
        """Retrieve the exact content-addressed report, never a caller-supplied suite."""
        import re
        if not isinstance(campaign_id, str) or not re.fullmatch(r"[a-f0-9]{64}", campaign_id):
            raise StorageError("Invalid campaign ID")
        try:
            record = self.db.campaigns.find_one({"_id": campaign_id})
            if not record or not any(a["path"] == "report.json" and a["sha256"] == campaign_id for a in record["artifacts"]):
                raise StorageError("Unknown archived campaign")
            artifact = self.db.artifacts.find_one({"_id": campaign_id})
            if not artifact or hashlib.sha256(artifact["content"].encode()).hexdigest() != campaign_id:
                raise StorageError("Archived report hash verification failed")
            return json.loads(artifact["content"])
        except self.driver_error:
            raise StorageError("MongoDB report retrieval failed") from None


def archive_campaign(folder):
    with MongoArchive() as archive:
        return archive.archive(folder)
