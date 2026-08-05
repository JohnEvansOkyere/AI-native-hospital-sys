# Submission checklist — MLC (Africa) × Intron Agentic Voice AI Challenge

**Deadline: 6 August 2026.** Finalists announced 7 August at the workshop.
Submissions then carry into Intron's full Sahara CodeSwitch Africa Challenge
(mid-September).

| # | Deliverable | Where | Status |
|---|---|---|---|
| 1 | Solution description | [`SOLUTION.md`](SOLUTION.md) | drafted — needs Twi/Pidgin numbers |
| 2 | Demo video (unlisted YouTube) | — | **not recorded** |
| 3 | Code / technical docs | [repo root](../../README.md) | ✅ done |
| 4 | Benchmark report | [`benchmark/results/REPORT.md`](../../benchmark/results/REPORT.md) | generator built — needs the audio |
| 5 | Ethics & inclusion statement | [`ETHICS.md`](ETHICS.md) | ✅ drafted |
| 6 | Benchmark audio *(optional, bonus)* | `benchmark/audio/` | needs recording + opt-in consent |

Also required: **team registration** → https://forms.gle/RV43DXHAJCTYr98U7

## The blocking path

Everything below #4 depends on one thing:

1. Sign off the six Twi wording questions at the bottom of
   [`benchmark/recording/scenarios.md`](../../benchmark/recording/scenarios.md)
2. `cd benchmark && python sync_scenarios.py`
3. Record T01–T09 (Twi) and P01–P05 (Pidgin), plus ~5 lines in noise.
   Signed consent per speaker first.
4. `python make_manifest.py --dry-run` → fix any flagged clips → `python make_manifest.py`
5. `python run_benchmark.py --manifest manifest.csv --audio-dir audio --out results --providers sahara,cartesia,local`
6. `python make_report.py`
7. Fill the `‹›` placeholders in `SOLUTION.md` from the report

## Demo video — suggested shot list

Keep it under three minutes. Show the dashboard reacting, not just the phone.

1. **The problem, 20s.** Cost is the #1 reason patients stop, not forgetting. And
   patients code-switch — "one-sixteen" vs "one-sixty" decides an escalation.
2. **Real WhatsApp, 60s.** Your phone beside the clinic dashboard. Send a voice
   note in Twi–English reporting a high BP. Show the transcript arriving, the
   model that heard it, and the dashboard flipping to red with the alert queued.
3. **The cost path, 30s.** "I can't afford it this month" → NHIS-alternative
   workflow, escalation to the care team.
4. **The benchmark, 45s.** Same utterance through two models side by side.
   Sahara can be told the patient speaks Twi; the others return
   `400 invalid language: tw`.
5. **Close, 15s.** Offline capability, no LLM clinical decisions, humans in the
   loop.

Record with the **Clinic** view, not Demo mode. Keep Demo mode available as a
fallback if the live webhook fails mid-take.

## Do not claim

- Production readiness — see the limitations sections in both documents.
- General model performance from a small corpus. The comparison is fair; the
  absolute numbers are indicative.
- That Cartesia's `ink-whisper` is architecturally independent of Whisper. It
  isn't, and the report says so.
