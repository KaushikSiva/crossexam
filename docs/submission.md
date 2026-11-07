# CrossExam — hackathon submission

Status: working engine, local and live-Subquadratic campaigns, published landing page, OpenUI evidence renderer, narrated video, and reproducible evidence. Meta's current request returns HTTP 402; do not count an unverified Meta run as a result.

## Team Name

CrossExam

## Team Members

Kaushik Sivakumar — participant handle `kaushik07`; GitHub `KaushikSiva`.

## Project Description

CrossExam asks a question every coding-agent team should fear: can broken software still get a perfect score on our tests?

It challenges an evaluation with plausible faulty implementations, executes them in an OS sandbox, and checks their behavior against a separate contract model. A fault counts as a blind spot only when the original tests pass and an independent check reproduces the violation. CrossExam minimizes the failure into an executable counterexample.

The demo exposes a one-line cache optimization that passes every existing test but returns one customer's reservation to another. Two requests prove the bug.

CrossExam then improves the evaluation itself. Each proposed suite is versioned and hashed before validation. Promotion requires additional defects caught, no lost coverage, and no incorrect rejection of correct implementations. A deliberately weakened proposal is rejected, preserving the stronger suite. A separate final audit opens only after learning ends.

On our small synthetic benchmark, final-audit detection improves from 1/8 seeded defects to 7/8, with 0/4 correct controls rejected. We publish the remaining miss, every suite version, source hashes, execution traces, and the methodology. These are results on particular seeded defects, not a claim about production accuracy.

Subquadratic is used live to prioritize contract risks from repository context. Its recorded routing call consumed 1,898 input tokens and changed the exploration order. The current measured run uses explicitly labeled local attack/test fixtures. A Meta Model API adapter for adversarial patch generation and independent test authoring is implemented; its live run is pending credited access and is not included in our measured results.

The monochrome React/Three.js/Motion landing page and OpenUI evidence explorer turn the report into an interactive explanation. OpenUI components read their metrics directly from recorded evidence. The Python engine has no third-party dependencies and is reproduced in Docker by GitHub Actions.

Primary track: Trust but Verify. Versioned evaluation improvements and rejection of regressions also address The System That Gets Better.

## Public GitHub Repository

https://github.com/KaushikSiva/crossexam

## 1-Minute Demo Video

Watch page: https://kaushiksiva.github.io/crossexam/demo.html

Direct MP4: https://kaushiksiva.github.io/crossexam/assets/crossexam-demo.mp4

Verified video duration: 59.7 seconds. 1600×900 H.264 video, AAC narration, subtitles. The narration uses ElevenLabs V4 with the premade Brian voice.

## Which partner products did you use?

- **Subquadratic:** verified live API use in a completed campaign.
- **Meta Model API:** adapter implemented, but the current request returns HTTP 402. Select Meta as a demonstrated integration only after a successful live campaign is recorded; update the description and evidence accordingly.
- Do not select Fetch.ai, Google DeepMind, or MongoDB: no use is claimed by this project.

OpenUI is an additional open-source integration, not one of the listed prize sponsors.

## Feedback for Cerebral Valley

Publish prize-stacking rules and a precise judging rubric alongside the participant guide.

## Feedback for partner products

SubQ's typed decisions made risk routing simple. Clearer credit activation and billing status would help teams unblock Meta testing.

## Judge's walkthrough

1. Open the investigation: the original suite passes, but the two-request tenant leak violates the contract.
2. Show the validation curve and the rejected weaker proposal.
3. Open the final audit: 1/8 to 7/8 detections, zero correct controls rejected, with the missed case visible.
4. Show the real Subquadratic request/response and the information withheld from the test author.
5. Offer the replay command and public evidence archive.

## Before submitting

- Use the final video and report versions if live partner access changes.
- Confirm all team members in the event's submission form.
- The public repository, watch page, direct video, and evidence page must open without signing in.
- Submit before 5:00 PM Pacific on November 7, 2026 (6:30 AM IST on November 8).
- Prize stacking has not been confirmed; do not assume the listed awards can be combined.
