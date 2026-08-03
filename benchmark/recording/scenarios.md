# Recording Scenarios — Speaker Scripts

> **⚠️ NATIVE-SPEAKER REVIEW REQUIRED BEFORE RECORDING.**
> The Twi below has been revised once (see *Review notes* at the bottom) but the
> reviser is **not** a fluent Twi speaker either. Evans — or another fluent
> speaker — must still sign these off. The review notes list exactly what
> changed and why, so you can check specific decisions rather than re-reading
> everything.
>
> **This file is the single source of truth.** Edit here, then run:
>
> ```bash
> python sync_scenarios.py
> ```
>
> That regenerates `scenarios.csv`, which `run_benchmark.py` uses as the scoring
> reference. Never hand-edit the CSV — if it drifts from what speakers actually
> read, every WER number in the report is wrong.

Speakers read each line **verbatim** at a natural pace, as if talking to a clinic
nurse on the phone. Don't over-articulate. Numbers are said as written in words.

---

## Set E — English control (Ghanaian-accented English, no code-switching)

| ID | Intent | Script |
|----|--------|--------|
| E01 | adherence_yes | "Yes, I took my medicine this morning after breakfast." |
| E02 | cost | "I haven't bought the medicine yet. It's too expensive for me this month." |
| E03 | bp_report (142/95) | "I checked my blood pressure today. It was one forty-two over ninety-five." |
| E04 | book_appointment | "Please book me an appointment with the doctor for Tuesday morning." |
| E05 | refill_request | "My amlodipine is almost finished. I need a refill before Friday." |

## Set T — Twi–English code-switched

| ID | Intent | Script |
|----|--------|--------|
| T01 | adherence_yes | "Aane, manom aduro no ɛnnɛ anɔpa." |
| T02 | cost | "Sika nni hɔ — I can't afford the lisinopril this month." |
| T03 | forgot | "Me werɛ afi — I forgot to take it yesterday evening." |
| T04 | side_effect | "Sɛ menom aduro no a, me ti pae me. The medicine gives me serious headache." |
| T05 | ran_out | "Aduro no asa — the amlodipine finished since Friday." |
| T06 | bp_report (116/78) | "Me BP yɛ one-sixteen over seventy-eight." |
| T07 | bp_report (160/100) | "Mesusuu me BP ɛnnɛ — it was one-sixty over one hundred." |
| T08 | book_appointment | "Mepɛ sɛ mebook appointment wɔ Dr. Mensah nkyɛn ɔkyena anɔpa." |
| T09 | bp_report (175/110) | "Me BP yɛ one seventy-five over one-ten. Ɛbɔ me hu." |

> T06 vs T07 is deliberate: "one-sixteen" vs "one-sixty" is the classic digit
> confusion, and here it decides a clinical escalation. Do not merge or drop these.
> A commercial API already got this wrong in pre-testing, so these two lines carry
> the benchmark's central claim.

## Set P — Ghanaian Pidgin–English

| ID | Intent | Script |
|----|--------|--------|
| P01 | cost | "I no fit buy the medicine, e cost too much for me this month." |
| P02 | bp_report (138/89) | "I check my BP for house. E be one thirty-eight over eighty-nine." |
| P03 | reschedule | "Abeg, make you move my appointment go next week Tuesday, I travel go Kumasi." |
| P04 | ran_out | "The nifedipine don finish since weekend, I never get chance go pharmacy." |
| P05 | adherence_yes (90/60) | "I take my medicine today, and my pressure be ninety over sixty." |

## Set S — Spontaneous (optional, 1–2 speakers)

No script. Give the speaker the situation, let them say it naturally in whatever
mix of languages they'd really use. **These need hand-transcription afterward**
(put the transcription in the manifest's `transcript_override` column).

| ID | Prompt to speaker |
|----|-------------------|
| S01 | "You stopped taking your BP medicine two weeks ago because it's too expensive. Tell the clinic." |
| S02 | "You want to move your Thursday appointment because of a funeral. Tell the clinic." |

---

## Review notes — what changed and why

Check these specific calls. If any is wrong, fix the table above and re-run
`sync_scenarios.py`. **"It's fine as it was" is a perfectly good answer** — the
originals were not broken, only unidiomatic in places.

| ID | Was | Now | Reasoning — please confirm or reject |
|----|-----|-----|--------------------------------------|
| T01 | "me anom aduro" | "manom aduro" | `me` + vowel-initial verb usually contracts. Is `manom` (perfect, "I have taken") right here, or do you want `menom` (simple past)? |
| T02 | "Sika no nni hɔ" | "Sika nni hɔ" | Dropped the definite `no` — "there's no money" reads more naturally than "the money isn't there". Agree? |
| T04 | "Sɛ me nom" | "Sɛ menom" | Written as one word, consistent with T01. Also: is `me ti pae me` the phrase people actually use for a bad headache, or is `me ti yɛ me ya` more natural on the phone? |
| T07 | "Mesusuw" | "Mesusuu" | Past tense of `susu`. Is `-uu` the form you'd write? |
| T08 | "Me pɛ sɛ me book appointment ne Dr. Mensah" | "Mepɛ sɛ mebook appointment wɔ Dr. Mensah nkyɛn" | `ne` reads as "with" in the comitative sense; `wɔ … nkyɛn` = "at/with Dr. Mensah's". Which is what a patient would actually say? |
| T09 | "Ɛyɛ me hu" | "Ɛbɔ me hu" | Both attested for "it scares me"; `ɛbɔ me hu` felt more common in speech. Your call. |

### Things deliberately left alone

- **Numbers stay in English** ("one-sixteen over seventy-eight") across all sets.
  That's realistic — Ghanaians overwhelmingly say BP figures in English — and it
  is precisely the code-switch point the benchmark is measuring. Do not translate
  them into Twi numerals.
- **Drug names stay in English** (lisinopril, amlodipine, nifedipine). Same reason.
- **Set P was not revised.** The Pidgin reads naturally already; flag anything
  that doesn't ring true to you.

### If a speaker deviates

Don't force them back to the script. If the natural version is better, keep the
recording and write the exact wording into the manifest's `transcript_override`
column. Natural speech is worth more than script fidelity here — the scoring
handles it either way.
