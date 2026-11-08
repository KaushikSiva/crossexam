# CrossExam submission

**Team name:** CrossExam

**Team member:** Kaushik Sivakumar (`kaushik07`)

**Project description** (1,706/3,000 characters)

Your coding agent says the patch is ready. Every test is green. What did those tests miss?

CrossExam challenges the evaluation itself. Its architecture centers on Meta's Muse Spark as the primary code-generation integration, with Subquadratic prioritizing risks and Google DeepMind's Gemini independently writing stronger tests. The test author never sees the candidate implementation. An independent specification oracle and OS sandbox determine whether a failure is real.

CrossExam turns demonstrated failures into short, reproducible counterexamples. Proposed tests earn promotion only when they catch additional faulty implementations, preserve existing coverage, and accept every correct control. After learning stops, a separate final audit measures the accepted suite.

On our expanded public synthetic benchmark, Gemini grows the suite from 4 to 34 scenarios. Validation improves from 1/30 to 23/30; the separate final audit improves from 5/30 to 24/30, with all four correct implementations accepted. Every result, including six audit misses, is inspectable. This recorded run uses Fetch.ai's ASI:One for code generation while Muse API credit access is pending.

Fetch.ai also makes the evaluation callable by other coding agents. A Fetch uAgents verifier retrieves the frozen suite from MongoDB, executes a submitted patch, and returns a cryptographically signed verdict bound to the exact code and tests. The recorded exchange blocks faulty code and accepts correct code. MongoDB preserves 40 campaign artifacts with verified hashes; OpenUI makes the evidence inspectable. The database and agent exchange run locally.

Built for Trust but Verify. CrossExam makes passing tests earn your trust.

**Public GitHub repository:** https://github.com/KaushikSiva/crossexam

**One-minute demo video:** https://kaushiksiva.github.io/crossexam/demo.html

**Direct MP4:** https://kaushiksiva.github.io/crossexam/assets/crossexam-demo.mp4

**Partner products:** Meta Muse Spark (primary code-generation integration; adapter implemented, API currently returns HTTP 402), Google DeepMind / Gemini, Fetch.ai / ASI:One and uAgents, MongoDB, Subquadratic, and OpenUI. The measured campaign uses ASI:One as the code generator. OpenAI was used in earlier recorded campaigns.

**Primary track:** Trust but Verify. The versioned evaluation improvements also address The System That Gets Better.

**Proof to show judges:** 5/30 → 24/30 final-audit detections; 1/30 → 23/30 validation detections; 0/4 correct controls rejected; four measured promotions; 34 active scenarios; signed Fetch agent BLOCKED/PASS receipts; 40 MongoDB artifact hashes verified; 45 passing tests; all previous campaigns preserved.

**Scope:** Synthetic sequential reservation API. Local MongoDB Community and local Fetch uAgents transport. No general production accuracy or autonomous deployment claims.

**Feedback for Cerebral Valley:** A single page with deadlines, judging criteria, and credit setup would make the event easier to navigate.

**Feedback for partner products:** Typed risk decisions and structured model outputs made evidence collection straightforward. Clearer prepaid-credit and database-connection setup would help teams get started faster.
