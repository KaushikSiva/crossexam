# What the numbers mean

CrossExam currently verifies one synthetic, sequential reservation API. Its test subject contains two Python modules with coupled tenant, idempotency, inventory, and input-validation behavior. This is a working research prototype, not a universal PR reviewer.

## Four disjoint implementation partitions

| Partition | Size | Use |
| --- | ---: | --- |
| Discovery | 5 seeded faulty implementations, plus a model-generated attempt in live mode | Find contract violations that the original suite accepts |
| Validation | 30 faulty implementations | Decide whether to promote a proposed suite |
| Final audit | 30 separate faulty implementations | Measure the original and final suites after all proposals finish |
| Correct controls | 4 implementations | Reject suites that incorrectly block correct behavior |

All seeded variants are hand-authored and public. They are withheld from model prompts, not secret from the repository's authors or readers. Audit variants exercise familiar defect families through different code changes; we do not claim generalization to wholly unseen bug classes. The audit is opened once **per campaign**. Repeated development runs on a public corpus do not create a fresh scientific holdout each time.

Validation is reused across four live proposal rounds (three in fixture mode) and is therefore a development signal. The final audit is kept out of proposal generation. We publish both denominators and the missed cases, rather than presenting validation performance as final generalization.

## Scenarios versus implementations

The current expanded run grows from 4 to 34 active input scenarios. Each scenario is a sequence of API requests. The suite is executed against 30 faulty validation implementations and four correct controls; a separate final audit uses another 30 faulty implementations. A score such as 24/30 counts faulty implementations detected, not scenarios passed. Earlier 8-case reports retain their original corpus hashes and denominators.

Revision `relay-reservations-v2-30-per-split` adds 22 faults to each split while retaining all previous variants. Every source is distinct and compiles. Tests reproduce each added defect with an explicit contract witness and verify all four correct controls on all 44 witnesses. These qualification inputs live only in the test suite and are not passed to models or substituted for their proposals. Five familiar contract families remain; a larger case count does not add production realism. The corpus was fixed before the new live run and was not edited after its final audit.

## Independence boundaries

The attacker sees the contract, original implementation, and baseline scenarios. The test author receives a fresh context containing the contract, the current input scenarios, and observed counterexamples. In live mode it also receives prior aggregate validation counts, gate decisions, and its previously proposed inputs. It receives no implementation, attacker reasoning, reference-model code, validation variants, or audit variants.

The current run uses Fetch.ai / ASI:One for the attacker and Gemini 3.8 Flash for the test author. The earlier published run used OpenAI for both roles. Meta, OpenAI, Gemini, and ASI:One all use the same context separation boundaries. Separate contexts and different providers reduce direct contamination; they do not eliminate correlated blind spots.

The model emits JSON inputs, never expected answers or executable assertion code. An independent event-ledger oracle computes the expected responses. The candidate receives only its two modules, a minimal input/output worker, and scenario inputs. Model confidence never overrides execution.

The implementation updates mutable balances. The oracle recomputes balances from successful reservation events and releases. Different structures reduce a specific source of correlated implementation mistakes, but both are still authored from the same specification. The specification and oracle remain trusted assumptions.

## What improves

The **evaluation suite** improves. Model weights are unchanged. Every candidate suite is saved and hashed before validation. Promotion requires all of:

1. At least one additional validation implementation is detected.
2. Every previously detected validation implementation remains detected.
3. No correct control is rejected.

Fixture mode includes a labeled system-injected regression challenge that proposes reverting to the smoke suite. **Live mode never injects this challenge.** In the published OpenAI run all four proposals earned promotion; there were no rejections. Rejection behavior is tested separately with no-gain, lost-coverage, and false-rejection cases.

Local mode uses hand-authored attacks and test proposals to reproduce the mechanism without credentials. Live mode defaults to Subquadratic risk routing and OpenAI attack/test generation. Each round prioritizes discovery families still undetected by the active suite, then asks for new tests using aggregate validation feedback. All four rounds are budgeted before the run starts. One generated attack is combined with five labeled seeded defects. Hand-authored contract probes discover witnesses; the new evaluation proposals are model-generated. `--generator` selects the attacker; `--test-author` optionally selects a different proposal provider. The proposal prompt now asks for systematic coverage of every contract clause and previously untested input partitions. Invalid generated action JSON receives at most one new model repair call per proposal, within the shared eight-call limit; both responses remain in the evidence. API responses, token usage, latency, and request/response hashes are saved. Live failures are reported instead of silently substituting fixtures.

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

Execution-time charts sum the measured wall duration of each candidate execution. They are not CPU utilization or end-to-end API latency. Reused score records retain their original execution durations. Provider token usage comes from API responses. The README separately reports a transparent estimate using the published OpenAI token rates; it excludes other providers and is not a billing receipt.

Concurrency, persistence, arbitrary language support, real production repositories, and automatic merging are outside this prototype's current scope.

## First live OpenAI campaign

The immutable archive is [openai-live-001](evidence/openai-live-001/report.json), engine commit `8161ddb`. It completed in 25.456 seconds: one live Subquadratic call, one OpenAI attack, and four OpenAI test proposals. Validation detection was 1, 4, 5, 6, and 7 of 8. The final audit improved from 1/8 to 6/8, with 0/4 correct controls rejected. Both misses remain in the published report. No prompt or suite was revised after opening this audit, and no follow-up run was selected for a better score.

The older fixture campaign achieved 7/8 on this audit. We retain it as historical evidence, rather than presenting it as a live model result. The public audit is not a new scientific holdout: it was already available to the project authors before this campaign.


## Earlier partner expansion (8-case corpus)

The earlier immutable report is [gemini-fetchai-live-004](evidence/gemini-fetchai-live-004/report.json). Fetch.ai / ASI:One generated the delimiter-collision attack; four fresh Gemini contexts proposed tests. The active validation curve is **1 → 6 → 7 → 8 → 8 / 8**. Three proposals were promoted, and the fourth was rejected for no new detections. The active suite has 25 input scenarios. Only after all four proposals finished, the final audit caught 8/8 with 0/4 correct controls rejected. The full run took 257.704 seconds.

That revision included four development attempts, all retained in [campaigns.json](campaigns.json). The first completed at 4/8 audit detections; the second stopped before audit on malformed action JSON; the third completed at 5/8; the fourth completed at 8/8. Prompt instructions and provider choices changed between attempts. Results from a repeatedly observed public corpus are development outcomes, not an untouched scientific holdout or a controlled provider comparison. The historical OpenAI campaign remains available at 6/8.

## MongoDB and Fetch verification receipts

A real local MongoDB Community 8.0.13 server stores 40 artifacts from the current campaign. Content-addressed artifacts upload before the campaign record. An independent readback verifies all 40 hashes. The connection string and agent identity seed are excluded from evidence exports. MongoDB Atlas connectivity is not claimed.

The Fetch uAgents verifier accepts signed requests over loopback HTTP. It retrieves the exact archived report by content hash, selects its accepted active suite, verifies the suite hash, and executes candidate code using the existing sandbox and oracle. It signs a receipt binding the request ID, requester, candidate hash, campaign ID, suite hash, and verdict. The client checks the signer, signature, and request binding. Verdicts and proof records are stored in MongoDB separately from the frozen campaign.

Two real recorded requests demonstrate BLOCKED for the ASI:One-generated faulty patch and PASS for the correct implementation. These are post-campaign verification requests, not extra validation or audit cases and not additional model calls. The transport is local; no Agentverse deployment, discovery, payment, or remote service availability is claimed.


## Expanded 30-case campaign

The current immutable report is [expanded30-live-005](evidence/expanded30-live-005/report.json), with benchmark revision `relay-reservations-v2-30-per-split`. The live campaign took 156.654 seconds. Validation improved **1 → 12 → 18 → 22 → 23 / 30**; all four proposals earned promotion. The active suite contains 34 scenarios. The separate final audit improved **5/30 → 24/30**, with **0/4** correct controls rejected. Audit misses are A01, A02, A10, A14, A17, and A28; no post-audit proposal or score-based rerun was made.

The 24/30 result is not directly comparable to the earlier 8/8: the denominator and fault mix changed. Every prior run remains unchanged. Muse Spark is positioned as the primary code-generation integration; a fresh access probe still returned HTTP 402. Actual successful calls in this campaign are ASI:One for the adversarial patch, Gemini for four test proposals, and Subquadratic for routing.

The expanded campaign's 40 MongoDB artifacts were independently read back and hashed. A new pair of signed Fetch uAgents requests verified the 34-scenario frozen suite: generated faulty code BLOCKED, reference implementation PASS. These receipts bind to the new campaign hash and are retained in [fetch-agent-30](evidence/fetch-agent-30/), separately from the earlier agent exchange.
