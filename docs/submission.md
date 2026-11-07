# CrossExam submission

**Team:** CrossExam

**Member:** Kaushik Sivakumar (`kaushik07`)

**Project description** (2336/3,000 characters)

CrossExam asks a question every coding-agent team should fear: can broken software still get a perfect score on our tests?

It puts evaluations on trial. An attacker proposes a faulty implementation. An OS sandbox runs it against an independent contract model. A fault only counts when the original tests pass and an executable counterexample proves the violation.

In our live demo, OpenAI generates an inventory optimization that passes all four existing tests. But reserving two units for one customer also reduces another customer's stock. CrossExam proves it with two requests.

A fresh model context then writes input-only tests from the contract and observed failures. It cannot see the implementation, attacker reasoning, oracle, or held-out variants. The oracle supplies expected outcomes. Each proposal is frozen and hashed before evaluation. Promotion requires additional validation detections, no lost coverage, and no false rejection of correct code. Prior aggregate feedback guides the next proposal.

One real 25-second campaign improved validation detection from 1 to 4 to 5 to 6 to 7 of 8 defects across four model-generated proposals. All four earned promotion; no rejection was staged. A separate final audit improved from 1/8 to 6/8, with 0/4 correct controls rejected. Both misses are published. This public synthetic corpus is withheld from model prompts, not previously unseen by the authors; these are not production accuracy claims.

Subquadratic's SubQ Snap 1.1 is used live to prioritize risks from the contract, repository, and tests. OpenAI GPT-5.4 mini generates the faulty patch and independent test proposals. Five OpenAI calls used about $0.034 at published token rates, excluding Subquadratic and narration. Every request, response, suite, hash, and decision is archived. Meta's optional adapter remains available but is not claimed as a successful integration.

A monochrome React/Three.js/Motion landing page and OpenUI evidence explorer make the results inspectable. OpenUI reads metrics directly from the report. The dependency-free Python engine enforces sandbox boundaries and runs in Docker CI. Its gate also has explicit tests for no-gain proposals, lost coverage, and false rejections.

Primary track: Trust but Verify. The versioned evaluation loop also addresses The System That Gets Better.

**Public GitHub:** https://github.com/KaushikSiva/crossexam

**One-minute demo:** https://kaushiksiva.github.io/crossexam/demo.html

**Direct MP4:** https://kaushiksiva.github.io/crossexam/assets/crossexam-demo.mp4

**Partner products:** Subquadratic. OpenAI and OpenUI are also used; select them only if the form offers them. Do not select Meta as a successful live integration.

**Cerebral Valley feedback:** Publish prize-stacking rules and a precise judging rubric alongside the participant guide.

**Partner feedback:** SubQ’s typed risk decisions were useful and fast. Clearer credit activation would help teams resolve Meta billing restrictions.
