# CrossExam submission

**Team name:** CrossExam

**Team member:** Kaushik Sivakumar (`kaushik07`)

**Project description** (1584/3,000 characters)

Your coding agent says the patch is ready. Every test is green. What did the tests miss?

CrossExam tries to answer that before the code ships. In our demo, OpenAI writes an inventory optimization that passes all four existing tests. But reserving two units for one customer also reduces another customer's stock. CrossExam proves the bug with just two requests.

It then asks a fresh model session to write better tests without showing it the faulty code. Every proposed suite is saved before evaluation. It only earns promotion if it catches more faulty implementations, preserves previous detections, and keeps correct code passing. A separate executable contract model decides whether the behavior is right.

In one 25-second live run, the suite grew from 4 to 29 test scenarios. Validation detection improved from 1/8 to 7/8 faulty implementations. A separate final audit improved from 1/8 to 6/8, while all four correct implementations passed. Two bugs were still missed, and we publish them. This is a small, public synthetic benchmark; the audit implementations stay out of model prompts.

Subquadratic helps choose where to look. OpenAI generates the faulty patch and new tests. OpenUI lets you inspect the results, and candidate code runs in an OS sandbox. The repo includes the improvement curves, every model call, frozen test suites, and runnable counterexamples.

CrossExam improves the evaluation itself, so passing tests come with evidence you can inspect. Built for Trust but Verify, with versioned evaluation improvements also addressing The System That Gets Better.

**Public GitHub repository:** https://github.com/KaushikSiva/crossexam

**One-minute demo video:** https://kaushiksiva.github.io/crossexam/demo.html

**Direct MP4 (52.1 seconds):** https://kaushiksiva.github.io/crossexam/assets/crossexam-demo.mp4

**Partner products:** Select Subquadratic. If OpenAI or OpenUI are offered as additional options, both are used. Meta was not used successfully in the published run.

**Feedback for Cerebral Valley:** A single page with deadlines, judging criteria, and credit setup would make the event easier to navigate.

**Feedback for partner products:** SubQ’s typed risk decisions were easy to use. Clearer credit activation and billing errors would help teams get started faster.
