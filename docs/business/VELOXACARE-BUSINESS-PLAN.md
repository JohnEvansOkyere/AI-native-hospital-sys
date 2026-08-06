# VeloxaCare — Business Plan

**Veloxa Technology Limited** · Accra, Ghana

Prepared for: Axis Sprint 001 (Ideation Axis Group)

Date: August 2026 · Version 1.0

Contact: John Evans Okyere, Founder & CEO · okyerevansjohn@gmail.com · +233 54 495 4643

> **How to read this plan.** Every claim is either *built*, *measured*, or
> *assumed*, and it is labelled as one of the three. The assumptions register in
> Appendix B lists everything we have not yet tested, with the specific event
> that will resolve it. We would rather be caught being uncertain than be caught
> being wrong.

---

## 1. Executive summary

**What we are building.** An AI-native operating system for African clinics — a
shared, permissioned health-and-operations graph worked by a workforce of
specialised agents, with licensed humans holding every clinical decision.

**What is live today.** The first agent: WhatsApp-based care coordination for
chronic patients. A patient replies by text or voice note in Twi-English or
Pidgin-English. The system detects *why* they stopped taking their medicine —
cost, forgot, side effect, ran out — and routes each reason to a different
action. Cost barriers escalate to the care team and open an NHIS-covered
alternative workflow. A clinician dashboard updates in real time.

**Why the wedge is not a reminder bot.** In Ghana, 55% of chronic patients do
not take medication as prescribed, and in one Ghanaian study **96% of
non-compliant patients named cost, not forgetting** (Buabeng et al., 2004). The
entire adherence product category is built on the assumption that patients
forget. In this market that assumption is wrong, which is why detecting the
reason — not the fact — is the product.

**Traction.** Product built and deployed. Veloxa Technology Limited registered.
Five providers approached, three at proposal or meeting stage: Impact Medical &
Diagnostic Centre (proposal requested after an in-person visit), Rivia Clinics
(proposal requested), Sonrisa Dental Clinic (meeting requested). An original
four-model code-switch speech benchmark on consented human Ghanaian recordings.

**What we have not done.** No pilot has run. Nobody has paid. Our price has
never been quoted to a customer. Closing that gap is the purpose of the next
twelve weeks.

**Market.** ~2.3 million diagnosed, unfollowed hypertensive adults in Ghana. At
US$1.50 per active patient per month that is a US$41M annual market in
hypertension alone; ~US$60M with diabetes. Chronic care is the wedge — the same
graph then sells as a facility operating system at an order of magnitude more
per account.

**The ask.** A place in Axis Sprint 001, and specifically: pricing for a product
sold to facilities, a repeatable pilot-to-contract close, a practising Ghanaian
clinician advisor, and investment readiness.

---

## 2. The problem

A Ghanaian patient is diagnosed with hypertension, given a prescription, and
told to come back in three months. Then the health system loses them.

More than half stop taking their medication. They do not call the clinic to say
so — they simply stop. Nobody finds out until the next appointment, if the
patient shows up at all. The clinic records it as non-compliance.

It was usually not non-compliance. It was poverty, and it was solvable: there
was frequently a cheaper NHIS-covered alternative available the entire time.

**The costs of that gap, per party:**

| Party | What the gap costs them |
| --- | --- |
| Patient | Uncontrolled BP → stroke, kidney failure, cardiac events. Preventable. |
| Clinic | A patient who never returns. Retention is felt but never measured. |
| Pharmacy | ~12 refills a year per chronic patient; roughly half drop off after three. |
| Insurer / NHIS | The full cost of every crisis that follow-up would have prevented. |
| Country | Chronic disease treated in emergency rooms rather than in clinics. |

The same coordination failure recurs everywhere in the journey: lost referrals,
lab results that never reach the ordering clinician, medicines that run out
before anyone reorders, claims rejected for missing documentation. Chronic-care
follow-up is simply where it is cheapest to prove and easiest to measure.

---

## 3. The insight

**Adherence is an economics problem that the industry treats as a psychology
problem.**

Nearly every adherence product ever built is a reminder — a push notification, a
pillbox, an SMS nudge — because the design assumption is that patients forget.
That assumption came from health systems where medicine is covered and
forgetting really is the failure mode. Ported to Ghana, it produces software
that tells a person who cannot afford their medicine to take their medicine.

So VeloxaCare does not ask "did you take it?" and log yes or no. It classifies
the reason and routes each one differently:

| Reason | Action |
| --- | --- |
| `cost` | Escalate to care team; open NHIS-covered-alternative workflow |
| `side_effect` | Escalate to a human clinician for review |
| `forgot` | Adjust reminder timing; no escalation |
| `ran_out` | Refill coordination with the pharmacy |
| `other` | Human review |

Three different actions out of one "no." That is the product, and it is the part
a generic reminder tool cannot copy without rebuilding around a different
premise.

---

## 4. Product — what exists today

*Status: built and deployed. A clinic could run patients through it this week.*

**Patient side.** A WhatsApp agent on the Meta Cloud API. Daily medication
check-ins, weekly blood-pressure requests. Patients reply by text or by voice
note in Twi-English or Pidgin-English — the way people actually speak. Nothing
to install; nothing to explain beyond "reply."

**Clinic side.** A live dashboard updating over WebSockets as messages arrive:
patients ranked by risk (green / amber / red), open alerts, full message history
with provenance recorded on every AI action, one-click enrolment, and an
auto-generated weekly report ranking every patient by risk before clinic.

**Safety layer.** All escalation is deterministic — the AI never decides.

- A blood pressure at or above 160/100 escalates immediately.
- Cost or side-effect escalates only after 2+ occurrences in 14 days.
- The language model *structures, classifies and summarises*. It does not
  diagnose, triage, or decide escalation. This is a deliberate medical-safety
  and legal boundary, and it is what makes a medical director willing to sign.

**Speech layer.** Four providers with automatic fallback, ending in a model that
runs entirely offline on CPU — so a district clinic with no internet still gets
transcription and escalation. The system degrades gracefully with no API keys
and no network; it cannot hard-fail on a missing credential.

**Architecture.** FastAPI backend, React clinician dashboard, SQLite/libSQL
storage, native WebSockets. One inbound choke point handles every transport, so
SMS, USSD and voice calls attach later without a parallel code path. Built
deliberately so no increment has to be thrown away.

---

## 5. Evidence and original research

*Status: measured. This is the part almost nobody at our stage has.*

We built a four-model code-switch speech benchmark — Intron Sahara, Cartesia
Ink, OpenAI Whisper, and local faster-whisper — on human Ghanaian recordings.
The benchmark imports the product's own speech code rather than copying it, so
it measures the models actually serving patients.

**What it found:**

- **A major commercial speech API rejects `tw`, `ak`, `pcm` and `gaa` outright**
  with explicit HTTP 400s. The only African language it accepts is Swahili.
  Anyone building African voice health on default infrastructure cannot serve a
  patient who does not speak formal English — and does not know it.
- **A blood pressure of "one sixteen over seventy eight" was transcribed as
  "160 Nova 78."** 116/78 is green; 160/78 is red. The error runs in the
  dangerous direction.
- **On Ghanaian-accented English, the African-built model is the only one that
  transcribes *amlodipine* correctly.** The African model has the pharmaceutical
  vocabulary.
- **Word error rate ranks the most useful model last.** One model heard "one
  forty-two over ninety-five" and wrote `142/95` — recognising it as a blood
  pressure — while the models that "beat" it wrote the words out. Our own
  normaliser scored comprehension as three errors. We caught it, fixed it, and
  now score **downstream task success first** — did the right patient get
  escalated — and word error rate second.

**Ethics by construction:** written consent per speaker, speaker IDs (`S01`)
never names, scripted utterances, no real patient data, and consent-bound audio
never committed to the repository.

This research is a commercial asset, not a vanity project: it determines which
model we route to, it is why our voice layer works where competitors' would not,
and it is the credibility we walk into a medical director's office with.

---

## 6. Market

*Status: modelled from published prevalence data plus one price assumption. See
Appendix A for sources and Appendix B for assumptions.*

**Ghana — the wedge.** ~27% of Ghanaian adults are hypertensive (pooled
prevalence across 85 studies), roughly 5 million people. Fewer than half know
it; only ~24% of those diagnosed have it controlled. That leaves **~2.3 million
diagnosed adults needing lifelong follow-up nobody is providing.**

| Layer | Population | Annual value at US$1.50/patient/month |
| --- | --- | --- |
| TAM — Ghana, hypertension | ~2.3M diagnosed adults | **~US$41M** |
| TAM — Ghana, + diabetes | — | **~US$60M** |
| SAM — private-sector chronic patients under active facility care (~15%) | ~350,000 | **~US$6M** |
| SOM — 3-year target, 40 facilities × 400 patients | 16,000 | **~US$288K ARR** |

The serviceable slice is reachable with the product exactly as it exists today,
through a sales motion already running.

**Where it actually goes.** Chronic care is the wedge, not the business. The
same graph runs documentation, triage, pharmacy, claims and reporting, which
moves us from US$1.50 per patient to a facility operating-system subscription —
an order of magnitude more per account, sold into clinics that already trust us.

**The continent.** Hypertension prevalence across sub-Saharan Africa is
comparable to Ghana's, against ~1.1 billion people, and the same conditions
hold: WhatsApp ubiquity, mobile money, thin clinical staffing, fragmented
records. Ghana is the proving ground, not the market.

---

## 7. Business model

**Who pays: the facility, pharmacy, insurer or programme. Never the patient.**
Essential care interactions must stay free at the point of use or the people
this is built for will not use it.

**Pricing (assumption — untested).** US$1.50 (~GHS 20) per active patient per
month, on a facility subscription. Two structures are live candidates and the
choice is one of the things we most need help deciding:

| Model | For | Risk |
| --- | --- | --- |
| Per active patient / month | Aligns cost with value; scales down for small clinics | Requires the clinic to track enrolment |
| Flat facility subscription by tier | Simpler to sell and budget | Under-prices large facilities |

**Why we price against the pharmacy, not the clinic budget.** Retention has no
line item in a small private clinic's budget — owners feel the drop-off but have
never quantified it. A pharmacy does have that line: a chronic patient is ~12
refills a year, and roughly half drop off after three. Where a single owner sees
both the clinic and the pharmacy, retention has a direct P&L link and the
decision takes weeks rather than quarters. We sell to whoever owns both.

**Later revenue lines**, on the same graph and the same accounts: claims
automation, pharmacy and supply services, premium operational analytics,
and the facility operating-system subscription itself.

**Unit economics (to be measured in pilot).** Variable cost per active patient
per month is dominated by WhatsApp conversation fees, with model inference and
speech-to-text an order of magnitude below that. We have not yet measured it at
volume and will not quote a gross margin until we have.

---

## 8. Go-to-market

**The offer, deliberately frictionless:** a free 60-day pilot. One condition
(hypertension). 30 patients. Weekly report to the clinic. No setup cost, no
software to install, no workflow change, no staff training.

**The one non-negotiable:** the clinic's drop-off baseline is agreed *in their
own numbers, before day one*. Otherwise the result is our marketing rather than
their measurement — and their measurement is what converts.

**Pipeline (current):**

| Provider | Stage |
| --- | --- |
| Impact Medical & Diagnostic Centre (Asylum Down) | Proposal requested after in-person visit |
| Rivia Clinics | Proposal requested |
| Sonrisa Dental Clinic | Meeting requested |
| The Bank Hospital | Outreach ready |
| First American | Outreach ready |

Five approached, three moved forward. A structured discovery script finds the
provider's drop-off number in their own words *before* any demo.

**Ideal first customer.** A private clinic or small hospital group in Accra with
200–600 chronic patients, an owner or medical director who can decide alone, an
attached or partner pharmacy, 5–40 clinical staff, no IT department, already
using WhatsApp with patients informally, and a nurse who has tried follow-up
calls by hand and given up.

**Expansion path.** Private clinics and pharmacies → multi-site hospital groups
and pharmacy chains (same system, sold per branch) → insurers and employer
health plans → NGO programmes → the public system: CHPS compounds, district
hospitals, NHIS-funded chronic care.

**On government.** That is where the scale is and where this ends up. But public
procurement runs on multi-year cycles and will ask what outcomes we produced
elsewhere. Private clinics let us generate that evidence in 60-day increments.
We build the LHIMS and NHIS integration boundary from day one so that when we
go, we are not rewriting the product.

**A demand signal we chose not to chase.** Of the three providers who moved
fastest, none was a chronic-care clinic. A dental clinic's version of the
problem is the six-month recall that never happens; a diagnostics centre's is a
patient who uses one of sixteen services and never learns about the other
fifteen; an employee-health company's is members who never use care their
employer already paid for. Same failure in different clothes. It told us how
large the eventual platform is — but what those buyers want *today* is recall
reminders, and a reminder is the one part of this anyone can copy. We stayed on
chronic care.

---

## 9. Competition and defensibility

**The status quo, and it wins most of the time.** Paper folders, a nurse's
personal handset, and nothing at all. Every deal we lose in the next year will
be lost to "we'll get to it," not to a rival.

| Competitor | Position | Our relationship to them |
| --- | --- | --- |
| **mPharma** (Accra) | Mutti platform: medicine access and affordability via a pharmacy network, plus teleconsultation and diagnostics | Strongest overlap with our cost workflow, approached from drug supply. As plausibly a partner as a rival. |
| **Helium Health** (Nigeria; live in Ghana + 6 countries, 7,000+ clinicians, 300,000+ monthly visits) | Incumbent facility EMR, moving into financing | The benchmark we get compared to in the room |
| **mDoc** (Nigeria) | Digital self-management coaching for chronic disease | Closest to our wedge |
| HMS vendors, Turn.io-style WhatsApp infrastructure, Ghana's LHIMS | Store records or send messages | Neither coordinates the journey |

**Why customers choose us:**

- **Against EMRs:** they manage what happens inside the building. We are the
  only one that keeps working after the patient walks out, which is where the
  outcome and the repeat revenue are actually lost. An EMR records that a
  patient was prescribed amlodipine. We find out that they stopped, why, and get
  them back on it.
- **Against every follow-up tool:** we detect the reason, not the fact.
- **On language:** patients answer by voice note in Twi-English or
  Pidgin-English, on a speech stack we benchmarked rather than assumed.
- **On trust:** escalation is fixed rules, never a model's judgement; a licensed
  human decides everything clinical; every action is audited.
- **On friction:** nothing to install, no workflow change, free 60-day pilot.

**Defensibility, in build order of durability:**

1. The care-and-operations data model and the agent workflow engine.
2. Ghana-specific clinical and administrative protocols.
3. The facility network, and a patient continuity record that moves with the
   patient between CHPS compound, clinic, hospital and pharmacy.
4. **The outcome data** — which follow-up interventions actually changed
   adherence in an African population. Nobody else is collecting it. It is both
   the moat and a public good.

LHIMS, NHIS, labs, mobile money and Ghana Card connect at the boundary; they
never define the core data model.

**Why an incumbent cannot simply retrofit this.** Existing hospital software is
a filing cabinet a human operates. This is designed from the start around agents
doing the work under human supervision, over one shared graph. Adding an agent
to a filing cabinet does not produce this; it produces a chatbot on an EMR.

---

## 10. Roadmap

**The unit of the system is one loop, not any individual agent:**
understand → decide the next step → policy decides act-or-approve → execute →
track the outcome → learn.

**Agent roster, in build order.** Presented as sequence, not inventory — only
the first exists.

| # | Agent | Status |
| --- | --- | --- |
| 1 | Patient access + care coordination (WhatsApp/voice, adherence, cost routing, escalation) | **Shipped** |
| 2 | Clinical documentation — clinician speech → structured note | Next |
| 3 | Triage and routing | Planned |
| 4 | Pharmacy and supply — stockout prediction | Planned |
| 5 | Claims and finance — NHIS-aware | Planned |
| 6 | Facility manager — "which patients need attention today?" in plain language | Planned |

**Milestones:**

| Horizon | Target |
| --- | --- |
| 0–3 months | Two pilots live with real patients; baselines agreed first; pricing tested against five facilities; first signed paying customer; 60 days of retention data written up |
| 3–12 months | 6 paying facilities; onboarding self-serve enough that a clinic goes live without the founder; documentation agent in production; clinician advisor formally engaged |
| 12–24 months | ~18 facilities; pharmacy chain or insurer account; triage and pharmacy agents live; published outcome evidence |
| 24–36 months | ~40 facilities, ~16,000 active patients, ~US$288K ARR; first facility-OS subscription accounts; first market outside Ghana |

**Ghana-first by construction throughout:** offline-first with sync,
WhatsApp/SMS/USSD/voice rather than smartphone-only, mobile money, NHIS-aware
claims, local hosting, full auditability.

---

## 11. Team

| Name | Role | Technical | Full-time |
| --- | --- | --- | --- |
| **John Evans Okyere** | Founder & CEO — product, engineering, clinical-safety boundaries, pricing | Yes | Not yet |
| **Deborah Boluwatife Adeolu** | Co-founder & COO — operations and delivery | Yes | Yes |
| **Asamoah [surname]** | Program Lead, Business Development & Client Delivery (not a co-founder); MBA, Project Management | No | [ ] |

**Why this team.** Deborah and I shipped a company together before VeloxaCare
existed — VeloxaRecruit. We know each other's working rhythm under deadline, and
when we started a third person left and she did not. Most founding teams find
that out at month eight; we found it out before we began. The split is clean: I
build and hold the clinical-safety boundary; Deborah runs delivery — onboarding
and operations, the things that have to work at the twentieth clinic and not
just the first; Asamoah owns prospect → discovery → demo → proposal → pilot →
paying client, with Friday reporting against weekly targets.

**What we do not have: a clinician on the team.** We have designed around it —
all escalation is rule-based and never AI-decided, with a human always in the
loop — but a practising Ghanaian clinician advisor reviewing our escalation
protocols *before* we scale is the single thing we most want from Axis Sprint
001.

---

## 12. Financial model

*Status: modelled. Every figure below follows from the assumptions in
Appendix B. Replace them with measured numbers as the pilots produce them.*

**Revenue projection** at US$1.50 per active patient per month:

| | Year 1 | Year 2 | Year 3 |
| --- | --- | --- | --- |
| Paying facilities | 6 | 18 | 40 |
| Avg. active patients / facility | 250 | 350 | 400 |
| Active patients | 1,500 | 6,300 | 16,000 |
| **ARR (US$)** | **~27,000** | **~113,000** | **~288,000** |

Year 1 assumes the first paying customer signs in Q4 2026, so recognised Year 1
revenue is materially below the exit-run-rate figure shown.

**Cost structure (lean, pre-raise).**

| Line | Basis |
| --- | --- |
| Founder + co-founder compensation | [ ] — currently unpaid / below market |
| BD & client delivery (Program Lead) | [ ] |
| Clinical advisor (retainer) | [ ] — to be engaged |
| WhatsApp conversation fees | Per-conversation, Meta Cloud API — dominant variable cost |
| Model inference (LLM + speech) | Cents per patient per month at current volume |
| Hosting (serverless + managed libSQL) | Low double-digit US$/month at pilot scale |
| Company, legal, data-protection compliance | [ ] — Ghana Data Protection Act registration |

**The honest position on margins.** Gross margin should be high — this is
software with cents-level variable cost per patient — but we have not measured
WhatsApp conversation costs at volume, and we will not publish a margin figure
until a pilot produces one.

**Funding.** Nothing raised to date. Development to date has been founder time
and personal cost. The purpose of the Sprint is investment readiness and a first
paying customer, in that order of dependency: the second is what makes the first
credible.

**Use of funds, if raised (indicative priority order):**

1. Founder full-time — removes the single largest execution constraint.
2. Clinical advisor retainer and protocol review before scale.
3. Second engineer — reduces bus factor, which is currently one person.
4. Pilot deployment costs across 10–15 facilities.
5. Data-protection and regulatory compliance done properly rather than late.

---

## 13. Risks and mitigations

| # | Risk | Severity | Mitigation |
| --- | --- | --- | --- |
| 1 | **Clinics will not pay for retention they have never measured.** A pilot delights everyone and stalls at "come back next quarter." A free pilot also trains people to expect free. | **Highest** | Price against pharmacy refill revenue where the P&L link is direct; agree the drop-off baseline in the clinic's own numbers before day one; keep the pilot narrow (one condition, 30 patients, 60 days) so the decision is small. |
| 2 | **Patient engagement decays.** Week-one reply rates are easy; week six is unmeasured. | High | The 60-day pilot is designed to measure exactly this. If it decays, the answer is fewer, better-timed messages — not more. |
| 3 | **The cost workflow detects but does not resolve.** The NHIS alternative reaching the patient depends on a prescriber signing off and a pharmacy holding stock — both outside our software. | High | Pilot with facilities that own an attached pharmacy, so the whole chain sits inside one decision-maker. Measure resolution rate, not detection rate. |
| 4 | **Bus factor of one.** The system was built by one engineer who is not yet full-time. | Medium-high | Architecture and invariants documented in-repo; Deborah is technical and full-time; second engineer is priority 3 on use of funds. Named here rather than left to be found. |
| 5 | **Clinical liability / regulatory.** Health data under Ghana's Data Protection Act; the boundary between coordination and clinical advice. | Medium | LLM is structurally barred from diagnosis and escalation decisions; all thresholds rule-based and auditable; clinician advisor and legal guidance are explicit asks of the Sprint. |
| 6 | **A well-funded incumbent (mPharma, Helium) ships adjacent.** | Medium | They are as plausibly partners as rivals. Our defensibility is the coordination graph and the outcome data, neither of which is a feature they can ship in a quarter. |
| 7 | **Speech quality on Ghanaian languages.** Recognition of Ghanaian languages is ahead of synthesis of them; no Twi/Akan/Ga TTS voice exists at production quality. | Medium | Four-provider fallback chain including a fully offline model; the product answers in the modality it was addressed in and never implies a Twi voice exists. |

---

## Appendix A — Sources

- Pooled hypertension prevalence 27.0% across 85 studies / 82,045 subjects;
  awareness 45.9%, control 23.8% —
  [PLOS One systematic review & meta-analysis](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0248137)
- 28.1% prevalence, WHO STEPwise method, middle-belt Ghana —
  [International Journal of Hypertension](https://www.hindawi.com/journals/ijhy/2019/1089578/)
- 96% of non-compliant patients cited cost — Buabeng et al., 2004 (Ghana).
- 55% chronic-medication non-adherence in Ghana.
- Helium Health scale figures — company published.
- Speech benchmark findings — our own measurements; methodology and results in
  `benchmark/README.md`.

## Appendix B — Assumptions register

Everything below is unproven. Each line names what resolves it.

| # | Assumption | Value used | Resolved by |
| --- | --- | --- | --- |
| A1 | Price per active patient per month | US$1.50 (~GHS 20) | Quoting five facilities a real price (Sprint weeks 5–8) |
| A2 | Who the payer is | Facility, or facility+pharmacy owner | The same pricing conversations |
| A3 | Chronic patients per target facility | 400 | Question 1 on the discovery script |
| A4 | Share of diagnosed patients in active private-sector care | 15% | Discovery across the pipeline |
| A5 | Ghana adult (18+) population | ~19M | Published; low risk |
| A6 | Patient reply rate sustains past week 3 | Assumed | 60-day pilot |
| A7 | Cost barriers actually resolve via NHIS alternative | Assumed | 60-day pilot; measure resolution not detection |
| A8 | Variable cost per active patient per month | "Cents" | Metered pilot usage |
| A9 | Facility count trajectory 6 / 18 / 40 | Modelled | Actual close rate after the first five priced offers |

## Appendix C — Links

| | |
| --- | --- |
| Live demo | [ ] |
| Demo video | [ ] |
| GitHub | github.com/JohnEvansOkyere |
| Benchmark report | [ ] |
| Landing page | [ ] |

---

*Veloxa Technology Limited · Accra, Ghana · August 2026*
