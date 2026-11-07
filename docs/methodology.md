# What the numbers mean

CrossExam currently verifies one synthetic, sequential reservation API. Its test subject contains two Python modules with coupled tenant, idempotency, inventory, and input-validation behavior. This is a working research prototype, not a universal PR reviewer.

## Four disjoint implementation partitions

| Partition | Size | Use |
| --- | ---: | --- |
| Discovery | 5 seeded faulty implementations, plus a model-generated attempt in live mode | Find contract violations that the original suite accepts |
| Validation | 8 other faulty implementations | Decide whether to promote a proposed suite |
| Final audit | 8 other faulty implementations | Measure the original and final suites after all proposals finish |
| Correct controls | 4 implementations | Reject suites that incorrectly block correct behavior |

All seeded variants are hand-authored and public. They are withheld from model prompts, not secret from the repository's authors or readers. Audit variants exercise familiar defect families through different code changes; we do not claim generalization to wholly unseen bug classes. The audit is opened once **per campaign**. Repeated development runs on a public corpus do not create a fresh scientific holdout each time.

Validation is reused across three proposal rounds and is therefore a development signal. The final audit is kept out of proposal generation. We publish both denominators and the missed cases, rather than presenting validation performance as final generalization.

## Independence boundaries

The attacker sees the contract, original implementation, and baseline scenarios. The test author receives a fresh context containing the contract, the current input scenarios, and observed counterexamples. It receives no implementation, attacker reasoning, reference-model code, validation variants, or audit variants.

Both contexts may use the same Meta model. Separate contexts reduce direct contamination; they do not eliminate correlated model blind spots.

The model emits JSON inputs, never expected answers or executable assertion code. An independent event-ledger oracle computes the expected responses. The candidate receives only its two modules, a minimal input/output worker, and scenario inputs. Model confidence never overrides execution.

The implementation updates mutable balances. The oracle recomputes balances from successful reservation events and releases. Different structures reduce a specific source of correlated implementation mistakes, but both are still authored from the same specification. The specification and oracle remain trusted assumptions.

## What improves

The **evaluation suite** improves. Model weights are unchanged. Every candidate suite is saved and hashed before validation. Promotion requires all of:

1. At least one additional validation implementation is detected.
2. Every previously detected validation implementation remains detected.
3. No correct control is rejected.

A system-injected regression challenge proposes reverting to the original smoke suite. It passes through the same gate and is rejected. This is explicitly labeled; it is not portrayed as a spontaneous model mistake.

Local mode uses hand-authored attacks and test proposals to reproduce the mechanism without credentials. Live mode uses Subquadratic risk routing and Meta attack/test generation. API responses, token usage, latency, and request/response hashes are saved. Live failures are reported instead of silently substituting fixtures.

## Execution and reproducibility

- macOS uses a deny-by-default Seatbelt profile. Linux uses Docker with no network, a read-only mount, a non-root user, dropped capabilities, and CPU/memory/process limits.
- Candidate environments exclude API credentials. A startup probe checks private-file reads, outside writes, network access, and credential absence.
- The worker enforces CPU, descriptor, and file-size limits. Host readers cap output; wall-time deadlines terminate stalled candidates. Docker containers are explicitly removed on abnormal termination.
- Sandboxes are practical containment, not a proof against every operating-system exploit. The macOS profile permits installed runtime libraries and system metadata; it is not a general production sandbox service.
- Evidence contains source hashes, corpus and contract hashes, frozen suites, full test outcomes, API usage, minimized counterexamples, and a hash-chained event journal.
- The hash chain exposes changes relative to a trusted published root. It does not establish independent authorship or prevent someone from rewriting the entire unpublished chain.
- Reproducer minimization yields a 1-minimal action subsequence, not necessarily the globally smallest possible example.

## Measurement caveats

The corpus is small and synthetic. A result such as 7/8 means seven particular seeded defects were caught; it is not an estimate of production detection accuracy. Four correct controls provide a useful sanity check, not a precise false-positive-rate estimate.

Execution-time charts sum the measured wall duration of each candidate execution. They are not CPU utilization or end-to-end API latency. Reused score records retain their original execution durations. Provider token usage comes from API responses; dollar costs are not inferred.

Concurrency, persistence, arbitrary language support, real production repositories, and automatic merging are outside this prototype's current scope.
