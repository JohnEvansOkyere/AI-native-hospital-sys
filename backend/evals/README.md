# Conversation evals

Scores what the bot **does** with a patient message — dose logged, case opened,
reading stored, booking started — and only then what it says. A friendly reply
that logs a dose nobody took is a failure.

```bash
cd backend
python evals/run_conversations.py                 # offline: rules only, no keys, free
python evals/run_conversations.py --live          # real models from ../.env (costs money)
python evals/run_conversations.py --live --judge  # also grade replies against rubrics
python evals/run_conversations.py --only pidgin   # one id, program or tag
```

- **Scenarios** live in `conversation_scenarios.py`: one patient message, the
  state it arrives in (flow, chat history, earlier barriers) and what the clinic
  expects. Expectations describe what a clinic wants, not what the code does
  today, so failures are findings.
- **Every message goes through `main.ingest_patient_message()`**, the same choke
  point as WhatsApp, against a throwaway SQLite file. The runner blanks the
  database URLs and WhatsApp credentials, so it can never touch the demo or
  production data or message a real phone.
- **Results** are written to `results/` as JSON. Compare runs before and after a
  change; keep the ones that mark a decision.
- **Exit code 1 when a `safety` scenario fails.**

## Reading the numbers

- **Offline measures the rules, not the AI.** Without keys every reply is a
  template, and rubrics aren't graded. Question scenarios "pass" offline as long
  as nothing is wrongly logged; whether the answer is any good needs `--judge`.
- **The judge is a model too.** Read the failing replies before trusting a score.
- **Tags** group failures by kind: `negation` ("no pain"), `pidgin`,
  `multi_intent`, `red_flag`, `emergency`, `safety`.
- **`needs_clinician_review`** marks clinical expectations a clinician in that
  specialty must confirm. **`twi_unverified`** marks Twi phrasings a Twi speaker
  hasn't checked. Neither is ground truth yet.

## Adding a scenario

Every bug a patient or tester reports becomes a scenario before it is fixed,
tagged `regression`. Use realistic Ghanaian phrasing, including Pidgin and
code-switching, and de-identified names only.
