# Security boundary

CrossExam intentionally executes potentially faulty Python in an operating-system sandbox. It never falls back to running candidates directly on the host.

Use `python3 -m crossexam doctor` before a campaign. A failed enforcement probe stops execution. The local UI binds to loopback and checks mutation requests for its expected host, origin, and custom header. Do not expose this development server to the public internet.

The publicly published viewer is read-only. It contains saved synthetic evidence and cannot execute visitor-supplied code or call paid APIs.

The reference oracle, contract, host orchestrator, operating system, and container runtime are trusted. The prototype is not a hardened multi-tenant code-execution service. See `docs/methodology.md` for the limits of the sandbox and evaluation claims.

Report a vulnerability through GitHub's private vulnerability reporting if available; otherwise open an issue describing the affected component without posting secrets or a destructive exploit.
