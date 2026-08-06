---
license: cc-by-nc-4.0
task_categories:
  - automatic-speech-recognition
language:
  - en
  - tw
  - pcm
tags:
  - code-switching
  - ghana
  - twi
  - ghanaian-pidgin
  - healthcare
  - low-resource
pretty_name: VeloxaCare Ghanaian Code-Switch Clinical Speech
size_categories:
  - n<1K
---

# VeloxaCare Ghanaian Code-Switch Clinical Speech

A small, consented, de-identified benchmark of **code-switched Ghanaian clinical
speech** — Twi–English and Pidgin–English — recorded for the MLC (Africa) ×
Intron Agentic Voice AI Challenge, Deep Learning Indaba 2026.

> **Do not upload this dataset until per-speaker release consent is verified.**
> The `release_consent` column in `metadata.csv` must read `yes` for every
> speaker included. See *Consent* below.

## What makes it different

Ghanaian patients do not switch language cleanly. They speak a Twi or Pidgin
matrix sentence with the **clinically load-bearing tokens — numerals and drug
names — in English**:

> *"Sika nni hɔ nti — I can't afford the lisinopril this month."*
> *"Me BP yɛ one-sixteen over seventy-eight."*

That boundary is where recognition fails consequentially, and it is what this
corpus is built to probe. It includes a deliberate **minimal pair**:
*"one-sixteen"* (116/78, clinically routine) against *"one-sixty"* (160/100,
immediate escalation). One vowel decides the clinical outcome.

## Contents

| | |
|---|---|
| Recordings | 57 |
| Total duration | 5.3 minutes (mean utterance 5.6 s) |
| Speakers | 3 (28 / 19 / 10 recordings) |
| Languages | English control 15 · Twi–English 27 · Pidgin–English 15 |
| Conditions | 48 quiet · 9 with ambient noise |
| Format | 16 kHz mono AAC (`.m4a`), transcoded from mixed handset encodings |

Filenames follow `{speaker}_{scenario}_{noise}.m4a`, e.g. `S01_T06_quiet.m4a`.

Scenario sets: **E** = Ghanaian-accented English control, **T** = Twi–English,
**P** = Pidgin–English.

## Fields in `metadata.csv`

`file_name`, `speaker_id`, `scenario_id`, `language_pair`, `noise_condition`,
`duration_s`, `intent`, `bp_reference`, `transcript`, `sample_rate_hz`,
`channels`, `age_band`, `gender`, `home_language`, `accent_region`,
`device_type`, `release_consent`.

`transcript` is the **scripted reference** the speaker read, not a hand
transcription of what they said. Speakers occasionally deviated; where they did,
the reference was corrected to match the actual utterance.

## Intended use

Evaluating ASR on code-switched Ghanaian clinical speech, and specifically
evaluating **downstream task success** rather than word error rate alone: whether
a blood pressure survives transcription, whether the correct clinical escalation
is produced, whether the right intent is detected.

Full results and methodology: see the accompanying benchmark report.

## Limitations

- **Small.** Three speakers and 5.3 minutes. Suitable for controlled comparison
  between systems on identical audio; not for general claims about Ghanaian ASR.
- **Uneven coverage.** 28/19/10 recordings per speaker, so aggregates weight one
  speaker more heavily.
- **Scripted, not spontaneous.** Read speech differs from real patient speech in
  fluency and prosody.
- **Twi scripts drafted by non-native speakers**, revised once, with outstanding
  review questions on specific constructions. Native-speaker sign-off is required
  before these recordings support general claims about Twi ASR.

## Consent and ethics

- All utterances are **scripted**. No real patient data appears anywhere.
- **Written consent per speaker** was obtained before recording.
- Public release of the audio was a **separate, optional opt-in** on the consent
  form. Only speakers who ticked *"my de-identified recordings may be included in
  the submitted audio dataset"* may appear here.
- Speakers are identified **only by code** (`S01`, `A01`, `G01`) — never by name.
  Demographic fields are coarse (age band, not age) and non-identifying.
- Speakers may withdraw their recordings; contact the maintainer and they will be
  removed.

## Citation

> Okyere, J. E. (2026). *VeloxaCare Ghanaian Code-Switch Clinical Speech.*
> Veloxa Technology Limited, Accra, Ghana.
