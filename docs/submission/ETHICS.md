# Ethics, Safety & Inclusion Statement

**VeloxaCare · MLC (Africa) × Intron Agentic Voice AI Challenge**
**Track:** Health

Health data and patient voices are the two most sensitive things this system
touches. This states what we did, and — where we fell short of what a production
deployment would require — says so plainly.

---

## 1. Consent

Every speaker in the benchmark corpus signed a written consent form
([`benchmark/recording/consent_form.md`](../../benchmark/recording/consent_form.md))
**before** recording. It states in plain English:

- what the recordings are for
- **which named third parties receive the audio** — Intron Health, Cartesia,
  OpenAI — and that faster-whisper runs locally and transmits nothing
- that participation is voluntary and unpaid, and can stop at any time
- that recordings may be withdrawn any time before the dataset is submitted

**Publishing the audio is a separate, explicit opt-in.** The challenge invites an
optional audio dataset; a speaker consenting to *testing* has not thereby
consented to *publication*. Only recordings where that second box is ticked are
included in any submitted dataset.

We corrected the form during the project: an earlier version named only Intron,
OpenAI and "an open-source model", omitting Cartesia. Since audio is in fact sent
to Cartesia, that made the disclosure incomplete, and consent obtained against an
incomplete list is not informed consent. The form now names every recipient.

## 2. Data minimisation and de-identification

- **The scripts are fictional.** Speakers read prepared clinic lines. No speaker
  discloses their own health information, medication, or blood pressure.
- **Speaker codes, never names.** Files are named `S01_T06_quiet.m4a`. The
  metadata sheet records only age band, gender, region/accent, phone type and
  noise condition — enough to describe corpus diversity, not enough to identify.
- **No audio in version control.** `benchmark/audio/` and
  `backend/voice_notes/` are git-ignored. Consent-bound audio is shared by a
  deliberate act, never by an accidental commit.
- **Generated filenames for patient voice notes.** Inbound WhatsApp audio is
  stored under a random identifier, never a patient-supplied filename or phone
  number.
- **Phone numbers are masked in logs** (`+2335…28`). Operational logs should not
  become a second, unmanaged patient database.

Voice is inherently biometric — it identifies the speaker even when the words do
not. That is why the audio is treated as identifying data throughout, despite the
scripts being fictional.

## 3. Clinical safety

**No language model makes a clinical decision.** This is the boundary the whole
design is built around:

| Component | Who decides |
|---|---|
| Blood-pressure thresholds, escalation to red/amber/green | **Deterministic rules** in `backend/services/ai.py` |
| Reason classification (cost / forgot / side-effect / ran out) | LLM, with a rule-based keyword fallback |
| Transcription | Speech models |
| Diagnosis, prescription, treatment change | **Licensed humans, always** |

An LLM can misclassify why a patient stopped their medication; the cost is a task
routed to the wrong queue, which a human sees and corrects. An LLM deciding
whether 160/100 is urgent is a different category of risk, and we do not allow it.
If asked to add "AI triage", the answer is no.

The agent's role is to **structure, classify, summarise and route**. Humans close
every loop.

**No auto-enrolment.** A message from an unrecognised number receives a polite
"please contact your care team" — never an automatic account. Enrolling someone
into a health service is a consented clinical act, not a side effect of sending a
message.

**Failure is safe by construction.** If speech recognition fails, the patient is
asked to resend or type, and no reading is recorded. The system never guesses a
blood pressure. Missing keys or a dead network degrade to local, offline
recognition rather than silent failure.

## 4. Inclusion

The premise of this work is that systems built for clean monolingual English
exclude the people who most need them.

- **Voice-first, not literacy-first.** Patients who cannot read fluently in
  English can speak instead — in whatever mix of Twi, Pidgin, Ga and English they
  actually use.
- **WhatsApp, not an app.** No download, no smartphone assumption beyond what
  patients already carry, no data cost barrier of a new install.
- **Language coverage is measured, not assumed.** We tested which language codes
  each provider accepts rather than trusting documentation. Cartesia returns
  `HTTP 400: invalid language: tw` for Twi, Akan, Ga and Pidgin; Whisper's ~99
  languages contain none of them. Only the African-built model can be told what
  language a Ghanaian patient is speaking. Naming that gap precisely is the point
  of the benchmark.
- **Offline capability.** Local open-weights recognition runs with no key and no
  internet, so a district clinic on an unreliable connection retains the
  escalation logic that matters most.

### Bias we can name

- **Accent and dialect coverage is thin.** A small number of speakers, drawn from
  a narrow social network, cannot represent Ghanaian speech. Results are
  indicative, not general. More speakers across more regions is the first thing
  more time would buy.
- **Scripted speech is not natural speech.** Reading a line removes the
  disfluency, hesitation and self-correction of a real patient under stress. A
  spontaneous set partially mitigates this; it does not eliminate it.
- **Our own metric was biased and we found it.** Word error rate initially ranked
  Intron Sahara worst because it wrote `142/95` where others wrote `142 over 95` —
  penalising the model that had *understood* the reading as a blood pressure. We
  corrected the normaliser and the ranking inverted. A benchmark that quietly
  disadvantages the African-built system would have produced a confidently wrong
  conclusion, and we report the correction rather than only the corrected number.

## 5. What a real deployment still needs

We are not claiming production readiness. Before any patient depends on this:

- **Ethics approval and a data-protection assessment** under Ghana's Data
  Protection Act, with a named data controller.
- **A real database with encryption at rest**, access controls and audit logging.
  SQLite on an ephemeral filesystem is a demo artefact.
- **Patient-facing consent and withdrawal in the product itself** — patients
  should see what is held about them and be able to leave, not only benchmark
  speakers.
- **Per-action audit records** — reason, confidence, permission boundary — on
  every automated action, not just the message provenance recorded today.
- **Clinical governance**: a named clinician accountable for the escalation
  thresholds, and a documented review cycle for them.
- **Data residency**: sending patient voice to overseas APIs is a decision a
  Ghanaian facility must make knowingly. The offline model exists partly so that
  choice is available.

## 6. Environmental note

Model choice has a cost beyond accuracy. Running a small local model for routine
transcription, and reserving API calls for cases that need them, is both cheaper
and less energy-intensive than defaulting every utterance to a frontier model.
Our provider abstraction makes that policy a configuration choice rather than a
rewrite.

---

**Contact:** John Evans Okyere · okyerevansjohn@gmail.com · Veloxa Technology
Limited, Ghana
