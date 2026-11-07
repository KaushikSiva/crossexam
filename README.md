# CrossExam

**Your tests passed. Your software failed. Here is the evidence.**

CrossExam challenges an evaluation suite with faulty implementations that still pass its tests, produces executable counterexamples, and admits stronger tests only after checking unseen defects and correct implementations.

Built for the **AIE Code Summit Hackathon, November 7, 2026** — Trust but Verify / The System That Gets Better.

## Build status

Active development. This first commit establishes the public repository. Working code, reproducible results, demo video, and submission materials will land throughout the build. Planned capabilities are not measured results.

## Intended workflow

1. Run the existing suite against a reservation service.
2. Challenge it with plausible faulty patches.
3. Independently reproduce contract violations.
4. Propose additional tests from the specification and discovered counterexamples.
5. Promote a versioned suite only when it improves detection on a separate validation set without rejecting correct controls.
6. Report a final untouched audit set separately from the validation used for promotion.

## Partner roles

- **Meta Model API:** generate candidate patches and test scenarios in separate contexts.
- **Subquadratic:** prioritize contract risks using repository context.
- **Executable checks:** determine the outcome; model confidence cannot override a failed check.

Live partner integrations and local fixtures will be labeled separately. API keys must never be committed.

## Author

[Kaushik Sivakumar](https://github.com/KaushikSiva)

MIT license.
