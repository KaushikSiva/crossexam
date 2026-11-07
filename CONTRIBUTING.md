# Contributing

The most valuable contribution is a **new defect the promoted suite misses**, or a **correct implementation it wrongly rejects**.

Start with the reservation API contract in `fixtures/relayqueue/contract.txt`. Add a small implementation variant and a reproducible request sequence. Explain which contract clause establishes the expected result. Do not change the oracle merely to make a candidate pass.

For new campaigns, allocate new final-audit variants before running proposal generation. Once audit feedback has influenced a change, that audit is development data; create a new partition to make a fresh generalization claim.

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m crossexam run
```

UI changes can be checked with `npm ci`, `npx playwright install chromium`, a running local server, and `npm run qa`.

Never include API keys, private repositories, customer traces, or other people's personal data in an issue, pull request, or evidence bundle.
