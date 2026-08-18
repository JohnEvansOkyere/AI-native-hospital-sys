# Competitive & funding landscape — African digital health

**Compiled 14 August 2026.** Companion to [LANDSCAPE.md](LANDSCAPE.md), which covers
the *research* landscape (datasets, ASR models, papers). This one covers the
*market and money* landscape: who else is building this, who has already won, and
what you can actually enter.

Every claim here is a link you can check. Where something is my analysis rather
than a sourced fact, it says so.

---

## 0. The five findings that should change what you do

1. **2026 is the worst funding year African healthtech has had in eight years.**
   Under **$20M across 36 startups** in H1 2026 — down from a 2025 in which health
   funding *grew over 200%*, the fastest of any African sector
   ([Africa Health Ventures #28](https://rowenaluk.substack.com/p/africa-health-ventures-28),
   [healthcare.digital](https://www.healthcare.digital/single-post/healthtech-africa-emerges-in-2025-driven-by-significant-investments-and-innovation)).
   **Implication: stop optimising for a VC round. Optimise for grants, prizes, and
   one paying clinic.** That is what this document is organised around.

2. **The Google thing you're remembering is almost certainly the MedGemma Impact
   Challenge, and its winner is uncomfortably close to you.** First place went to
   **EpiCast** — West Africa (ECOWAS), turning community health workers' *unstructured
   clinical observations in local languages* into structured WHO disease-surveillance
   signals ([blog.google](https://blog.google/innovation-and-ai/technology/health/med-gemma-impact-challenge/)).
   Local language + health + West Africa + a downstream structured action. That is
   your sentence, pointed at surveillance instead of adherence. §2 unpacks what this
   means.

3. **Someone already proved your core thesis in Ghana — and the government adopted
   it.** The Novartis Foundation's **ComHIP** ran community-based hypertension
   management in Ghana with SMS adherence support and moved control rates from
   **36% to 72%**, with a **−12 mmHg** average systolic drop. Ghana folded the
   curriculum and treatment guidelines into national policy
   ([Novartis Foundation](https://www.novartisfoundation.org/past-programs/better-hearts-better-cities/community-based-hypertension-improvement-project-comhip),
   [Africa Briefing](https://africabriefing.com/when-the-shopkeeper-measures-blood-pressure-novartis-foundation-tackles-hypertension-in-ghana/)).
   This is **good news framed correctly and fatal framed wrongly** — see §5.

4. **Nobody in the entire map does reason-coded non-adherence.** Everyone reminds,
   coaches, refills, or screens. Not one player classifies *why* a patient stopped and
   branches the action on it. Your differentiator survives a hard look. It is also
   the only thing that does — see §6.

5. **Local-language voice is now table stakes, not a differentiator.** Three of the
   six Google Ideathon finalists shipped African-language or voice interfaces, and the
   MedGemma winner did too. Two years ago that was the whole pitch. In 2026 it is the
   price of entry, and the differentiation has moved to *what the voice does next*.

---

## 1. The funding weather

| Metric | Figure | Source |
|---|---|---|
| African health startup funding, H1 2026 | **< $20M across 36 startups** — lowest in 8 years | [AHV #28](https://rowenaluk.substack.com/p/africa-health-ventures-28) |
| African health funding growth, 2025 | **+200%**, fastest-growing sector on the continent | [healthcare.digital](https://www.healthcare.digital/single-post/healthtech-africa-emerges-in-2025-driven-by-significant-investments-and-innovation) |
| African digital health market size | **$5.6B (2025) → $7.6B (2029)** | [Kapsule](https://kapsuletech.com/blog/digital-health-africa/) |
| Share of health funding going to pharmacy tech | **~40%** | [Kapsule](https://kapsuletech.com/blog/digital-health-africa/) |
| Share of all African startup funding to KE/NG/ZA/EG | **~83%** (Q1 2025) | [Kapsule](https://kapsuletech.com/blog/digital-health-africa/) |
| Ghana healthtech share of national startup deals | **~15%** of deals, smaller cheques, NHIS/GHS integration traction | [jbklutse](https://www.jbklutse.com/ghana-startups-funding-2026/) |

**The 2026 deals that did close** — note the shape of them:
Reme-D (Egypt, $1.5M, molecular diagnostics) · EdenCare (Rwanda/Kenya, €250k, digital
health insurance) · Biovac (South Africa, $15M loan, vaccine manufacturing) · Tibu
Health (Kenya, Proparco, clinic expansion) · Valorigo (DRC, medication price
comparison). **Supply chain, diagnostics, insurance, physical primary care.** Not one
patient-engagement or messaging company.

The author of that newsletter is explicit that this is capital retreating, not the
market collapsing: *"deal quality is high, valuations are rational… the businesses
that compound through a funding winter are the ones that will define the decade to
follow."*

> **Read for VeloxaCare:** a pre-revenue patient-engagement product is in the least
> fundable position in the least fundable year. That is not a reason to stop — it is a
> reason to route through **prizes and grants** (which are counter-cyclical and
> currently *more* available than usual, see §7) while you build the one thing that
> converts in any weather: **a clinic that pays you and outcome data from real
> patients**.

---

## 2. What Google actually picked

You asked specifically about this. There are four distinct Google programmes and it
matters which one you mean.

### 2a. MedGemma Impact Challenge — this is the one that fits you

**850+ teams globally.** Winners
([blog.google](https://blog.google/innovation-and-ai/technology/health/med-gemma-impact-challenge/)):

| Place | Team | What it does |
|---|---|---|
| **1st** | **EpiCast** | ECOWAS/West Africa. Community health workers' unstructured clinical observations **in local languages** → structured WHO IDSR disease-surveillance signals |
| 2nd | Sunny | Privacy-preserving skin cancer self-screening |
| 3rd | FieldScreen AI | TB screening, **fully on-device**, for community health workers |
| 4th | Tracer | Medical error prevention from physician notes |
| Novel Task | ClinicDx | Sub-Saharan health centres, **offline**, 160+ WHO and MSF guidelines |
| Novel Task | UniRad3s | Radiology reporting |
| **Edge AI** | BridgeDx | **Offline** decision support |
| Agentic | CaseTwin | Chest X-ray matching |
| **Agentic** | **BigTB6** | **Voice-driven** TB and anaemia screening |

### 2b. Data Science for Health Ideathon — Google + SisonkeBiotik, Ro'ya, DS-I Africa

30+ submissions, six finalists
([Google Research](https://research.google/blog/spotlight-on-innovation-google-sponsored-data-science-for-health-ideathon-across-africa/)):

| Team | Country | What |
|---|---|---|
| **Dawa Health** (1st + Audience Choice) | Zambia | **Multilingual** cervical cancer education + screening; midwives upload colposcopy images **via WhatsApp**, MedSigLIP detection, Gemini clinical guidance on WHO + Zambian protocols |
| Solver (2nd) | Benin | CerviScreen AI — cervical cytology, MedGemma-27B + LoRA |
| **Mkunga** (3rd) | Kenya | Maternal health advice **in Swahili, with TTS and STT**, MedGemma + Gemini on Vertex AI |
| HexAI (Best PoC) | Guinea-Bissau | DermaDetect — **offline-first** skin triage for CHWs |
| **MamaLens Lab** | Nigeria/Cameroon | **Multilingual offline** Android, **English + Yoruba**, pregnancy risk for CHWs |

### 2c. Google for Startups Accelerator Africa — Class 10

15 startups from **~2,600 applicants**, 13 Apr – 19 Jun 2026, **equity-free**. Since
2018: 106 startups, 17 countries, **$263M raised**, 2,800 jobs
([blog.google](https://blog.google/intl/en-africa/company-news/meet-the-15-startups-joining-the-google-for-startups-accelerator-africa-class-10/)).

**Only one health company made it: Meditect** (Ivory Coast, pharmacy digitisation).
The nearest adjacent is **Vambo AI** (South Africa, multilingual African-language AI
infrastructure). Note what that says: in an AI-first cohort of 15, health got one seat
and it went to *pharmacy supply software*, not patient engagement.

### 2d. Google.org

$25M to an AI Collaborative for Food Security; a **$30M AI Breakthrough Fund** open
call with **$1–3M grants**, health among the focus areas; ~$37M total committed to AI
in Africa. Google.org funds **Jacaranda Health's PROMPTS** (3.8M mothers)
([connectingafrica](https://www.connectingafrica.com/ai/google-commits-37m-to-advancing-ai-in-africa)).

### The pattern in what wins — my analysis, not a sourced claim

1. **Winners are built on the sponsor's models.** MedGemma, MedSigLIP, Gemini, Vertex
   AI. Every single Google-picked health solution. This is not decoration — it is the
   entry ticket, and VeloxaCare currently runs on Groq/Llama. For a Google programme
   you would need a MedGemma or Gemini path. For Intron's challenge, Sahara. Match the
   sponsor's stack or don't enter.
2. **Offline-first recurs relentlessly** — FieldScreen, ClinicDx, BridgeDx, HexAI,
   MamaLens. You have this (faster-whisper, no key, no network) and you under-sell it.
3. **The user is usually a health worker, not the patient.** EpiCast, FieldScreen,
   HexAI, MamaLens, Dawa all put a CHW or midwife in the loop. Panels read
   patient-facing AI as riskier. Your care-team dashboard is the answer to this and
   should lead, not trail, the pitch.
4. **Screening and detection dominate; chronic-disease adherence is nearly absent.**
   Cervical cancer ×2, TB ×2, skin, maternal risk, surveillance. **Not one NCD
   adherence solution in either Google cohort.** That is a real gap and it is yours.
5. **"Structured output from messy local-language input" is the winning verb.**
   EpiCast's whole pitch. Also literally what `bot.py` does — voice in Twi → reason
   code → routed action. You are closer to the winning shape than you probably think;
   you are describing it as a chatbot instead of as a structuring layer.

---

## 3. Tier 0 — the thing that already proved your thesis in Ghana

**ComHIP** (Community-based Hypertension Improvement Project) — Novartis Foundation,
Ghana Health Service, London School of Hygiene & Tropical Medicine, FHI 360. Launched
2015, peri-urban Ghana.

| | |
|---|---|
| Model | Shift screening and treatment into the community; tech supports health workers and patient self-management; **SMS for medication, diet and exercise adherence** |
| Result | Control rates **36% → 72%** for patients retained >1 year |
| Result | **−12 mmHg** systolic, **−7 mmHg** diastolic, average |
| Outcome | Ghana government **integrated the curriculum and treatment guidelines into national policy** and committed to scale to further regions |

Sources: [Novartis Foundation](https://www.novartisfoundation.org/past-programs/better-hearts-better-cities/community-based-hypertension-improvement-project-comhip) ·
[Africa Briefing](https://africabriefing.com/when-the-shopkeeper-measures-blood-pressure-novartis-foundation-tackles-hypertension-in-ghana/) ·
[Fierce Pharma](https://www.fiercepharma.com/marketing/novartis-foundation-and-partners-launch-new-hypertension-program-ghana) ·
[roundtable proceedings](https://pmc.ncbi.nlm.nih.gov/articles/PMC11465716/)

**Why this is the most important entry in this document.** It settles the question
*"does structured messaging improve hypertension control in Ghana?"* — yes, decisively,
and the Ministry agrees. So:

- ❌ **Do not pitch:** "WhatsApp messaging can improve hypertension control in Ghana."
  A reviewer who knows ComHIP will mark you down for not knowing it.
- ✅ **Do pitch:** "ComHIP proved community hypertension management works in Ghana and
  the government adopted it. It ran on SMS and human field officers, which is why it
  is expensive to scale and why it could not detect *why* a patient stopped.
  VeloxaCare is the layer that makes that model cheap: voice in the patient's own
  language, and reason-coded routing so the care team's scarce time goes to the
  patients whose barrier is cost."

That framing turns the strongest competitor in the document into your strongest
citation. **Also note: the Novartis Foundation founded HealthTech Hub Africa** (§7) —
so this is a funder lead, not just a literature reference.

---

## 4. Tier 1 — direct comparables

| Company | Country | What it does | Scale / evidence | Money |
|---|---|---|---|---|
| **[mDoc](https://www.psi.org/project/self-care/member-spotlight-mdoc/)** | Nigeria | **Closest business-model twin.** CompleteHealth™ virtual chronic-disease coaches + NudgeHubs™ physical hubs + NaviHealth.ai™ directory + provider tele-education | **84% of members improved chronic condition management**; **2.28M patient interactions**; 15,000+ health workers trained | ~$248k disclosed grants incl. **Google for Startups $100k** (2021), MassChallenge ([Crunchbase](https://www.crunchbase.com/organization/mdoc)) |
| **Healthy Heart Assistant** | Nigeria | WhatsApp GPT self-care assistant for hypertensive patients, cardiology clinic | Published study ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2949761225000501)) | Academic |
| **[Famasi Africa](https://www.famasi.africa/)** | Nigeria | Medication ordering, **automated monthly refills**, doorstep delivery, free follow-ups; 1,000+ pharmacies | Targeting **1M refills by 2027** | Pre-seed led by **Microtraction**; **Google for Startups AI-First** 2023 |
| **[Redbird](http://redbird.co/)** | **Ghana** | 5-minute rapid tests at community pharmacies — BP, blood sugar, cholesterol, BMI, anaemia + more | **360+ pharmacies** (Accra/Kumasi), **125,000+ tests**, 35,000+ patients | **$1.5M seed** — J&J Foundation, Newtown Partners, Founders Factory Africa |

**Reading each one against you:**

- **mDoc** is what you become in five years if this works. They out-scale you on every
  axis and have the Google grant you'd be applying for. What they *don't* have: voice,
  any Ghanaian language, code-switch handling, or reason-coded routing. Their coaches
  are humans, which is their moat and their cost ceiling.
- **Healthy Heart Assistant** is the closest published system and it is text-only,
  English-only, no cost-barrier routing. It is the paper you cite to say "this has
  been tried in English text; here is what changes in Twi voice."
- **Famasi** solves `ran_out` — logistically and well. It never asks *why*. A patient
  who stopped because of cost gets an automated refill they still can't afford.
  **This is the single sharpest illustration of your differentiator.** Use it.
- **Redbird owns the step upstream of you** in your own market: they are where a
  Ghanaian discovers their BP is high. They have no chronic follow-up layer.
  **This is your best partnership target in Ghana, full stop** — 360 pharmacies of
  distribution and a J&J Foundation relationship. Talk to them before you talk to
  another funder.

---

## 5. Tier 2 — the players who beat you on scale and evidence

These are not competitors so much as the standard you are being measured against.
Every grant panel has these in their heads.

| Player | Reach | Evidence |
|---|---|---|
| **[MomConnect](https://en.wikipedia.org/wiki/MomConnect)** / Praekelt, South Africa | **~5M mothers** since 2014, **95%+ of public health facilities**, national DoH programme, SMS + WhatsApp | WhatsApp subscribers **6.7× more likely** to use the helpdesk |
| **[Jacaranda Health PROMPTS](https://jacarandahealth.org/prompts/)**, Kenya | **3.8M mothers**; two-way SMS; ML triage; **Swahili LLM**; high-risk cases escalate to human helpdesk | **+20% antenatal attendance**, **1.85×** postpartum family planning. Google.org-funded |
| **[Viamo](https://viamo.io/ask-viamo-anything-ai/)**, 24 countries | 3-2-1 IVR **in local languages**; **17M subscribers** (2022); platform handles **1M calls/day**; "Ask Viamo Anything" LLM | **A third of early AVA questions were health**. [IVR outperformed SMS](https://viamo.io/global-health/voice-wins-over-text-how-ivr-outranked-sms-in-hiv-self-tests/) on HIV self-test uptake |
| **[Penda Health + OpenAI](https://openai.com/index/ai-clinical-copilot-penda-health/)**, Kenya | AI Consult, EHR-integrated clinical copilot, 15 clinics | **39,849 visits.** −16% diagnostic errors, −13% treatment errors; where red alerts fired, **−31%** and **−18%**. Ethics approval from **AMREF, Kenya MoH, Digital Health Agency, Nairobi County** |

**What to take from each:**

- **MomConnect** — the ceiling of this category is a *national programme*, not a
  startup. Your long-run buyer in Ghana is the Ghana Health Service / NHIA, and ComHIP
  (§3) is the precedent for how a pilot gets there.
- **PROMPTS** — this is the closest architectural sibling: two-way messaging, ML
  triage, local-language LLM, **human escalation for high-risk cases**. Their design is
  a validation of yours. Read their published work before you write another application.
- **Viamo** — proof that *voice beats text for exactly your population*, at continental
  scale. Cite the HIV self-test result; it is a much stronger argument for your voice
  channel than anything you can generate yourself.
- **Penda** — the gold standard for *how to prove an AI health claim*. Real visits, a
  control arm, a published effect size, and four named ethics approvals. This is the
  bar. **You are not close to it, and closing that distance is worth more than any new
  feature** (see §8).

---

## 6. Tier 3 — infrastructure you sit on or partner with

| Player | Relevance |
|---|---|
| **[Intron Health](https://docs.voice.intron.io/docs)** (Nigeria) | Sahara: **57 languages**, **14M+ audio clips**, **40,000+ speakers**, 30 countries; ~**92% accuracy on medical terms with heavy accents**. $1.6M pre-seed (Microtraction, Octopus, Plug and Play); **NVIDIA Inception; research partnerships with Google Research and the Gates Foundation**. Expanded beyond health into justice, fintech, telco. **They run the challenge you're closest to winning.** |
| **[Lelapa AI](https://www.technologyreview.com/2023/11/17/1083637/lelapa-ai-african-languages-vulavula/)** (SA) | Vulavula — ASR, translation, sentiment for African languages |
| **Vambo AI** (SA) | Multilingual African-language AI infrastructure; Google Class 10 |
| **Digital Umuganda** (Rwanda) · **Awarri** (Nigeria) | Local-language data and foundation models; Awarri is the technical partner behind Nigeria's N-ATLAS |
| **[GhanaNLP / Khaya](https://huggingface.co/ghananlpcommunity)** | Your Twi/Ewe TTS and MT. The only vendor in this table with real Ghanaian voices. |
| **mPharma** (Ghana) | 400+ mutti pharmacies, **4M prescriptions/year**, $35M+ raised, 4 countries |
| **Zipline** (Ghana) | ~2,000 health facilities served |
| **[Ilara Health](https://african.business/2026/05/innov-africa-deals/clinics-at-scale-how-ilara-health-is-building-africas-quiet-health-infrastructure)** (Kenya) | 2M+ patients, ~3,000 clinics, $10.89M raised — the "clinic operating system" model |

---

## 7. Where VeloxaCare actually stands

### Genuine strengths — things nothing above does

1. **Reason-coded non-adherence with differentiated routing.** `cost` / `forgot` /
   `side_effect` / `ran_out` → four different actions. **Zero players in this document
   do this.** mDoc coaches, Famasi refills, ComHIP reminds, PROMPTS triages risk — none
   classify the barrier and branch on it.
2. **The cost→NHIS-alternative workflow is Ghana-specific and evidence-backed.**
   Beyond Buabeng's 96%, there is a sharper stat: hypertension *is* NHIS-covered, yet
   **28.2% of patients still pay entirely out of pocket and 26.8% pay part**
   ([BMC Cardiovascular Disorders](https://link.springer.com/article/10.1186/s12872-025-05410-3)),
   because facilities face low and delayed NHIS reimbursement and run out of stock.
   **The cost barrier survives insurance.** That single finding justifies your entire
   product and you should lead with it.
3. **Twi and Ewe voice output.** Nothing else in this map speaks a Ghanaian language
   back to a patient.
4. **Task-success benchmarking over WER** — escalation correctness as the headline
   metric. This is methodologically novel, defensible, and exactly what Intron's
   challenge is asking for.
5. **An offline floor.** Recurring trait among Google's winners; you have it and
   under-advertise it.

### Honest weaknesses — ranked by how much they cost you

1. **No users.** Every Tier 1 and Tier 2 player has a denominator. You have a demo, a
   simulator, and a benchmark with **one speaker and five English utterances**. This is
   the single biggest gap for every opportunity in §8 — and Gates Grand Challenges
   *explicitly requires* an operational user base.
2. **No outcome data.** ComHIP has 36→72%. Penda has −16%. PROMPTS has +20%. You have
   "the escalation fired correctly." That is a systems claim, not a health claim.
3. **No clinical or institutional partner.** Penda listed four ethics approvals; ComHIP
   had Ghana Health Service and LSHTM. Panels read institutional backing as
   de-risking, and its absence as the main reason to reject.
4. **Team.** Africa Prize and the accelerators weight team heavily. A named Ghanaian
   clinician co-applicant is the cheapest, highest-leverage thing you can add.
5. **Category crowding at the messaging layer.** If the first line of your pitch is
   "WhatsApp bot for hypertension," you are competing with a 5M-user national programme
   and losing.
6. **Ga has no voice, and Sahara's Akan–English pair was not shipped when you tested.**
   Keep stating both plainly. Reviewers reward the honesty and punish the discovery.
7. **The stack doesn't match the sponsors.** Groq/Llama wins nothing at a Google
   programme. See §8.

---

## 8. The pipeline — what you can actually enter

Ordered by a blend of deadline urgency and fit. ⏰ = closes within 30 days.

| ⏰ | Opportunity | Prize / funding | Deadline | Fit | Effort |
|---|---|---|---|---|---|
| ⏰ | **[Sahara CodeSwitch Africa Challenge](https://techcabal.com/2026/08/04/97-teams-at-the-deep-learning-indaba-take-on-africas-language-mixing-problem/)** (Intron) | $10,000 across **5 categories incl. health** | **15 Aug – 15 Sept 2026** | ★★★★★ | **Low — you have the code** |
| ⏰ | **[Africa Prize for Engineering Innovation 2027](https://africaprize.raeng.org.uk/about-the-prize/how-to-apply/)** (Royal Academy of Engineering) | **£85k total; £50k to winner** + 8-month commercialisation programme | **8 Sept 2026, 16:00 UTC+1** | ★★★★☆ | Medium |
| ⏰ | [Gates Foundation Grand Challenges — AI-Enabled Consumer Engagement for Family Planning](https://gcgh.grandchallenges.org/) | **up to $500k**, 12 months | **25 Aug 2026, 11:30 PT** | ★★☆☆☆ | High |
| | **[MIT Solve](https://solve.mit.edu/challenges/10-for-10-challenge)** — next Global Challenges round | ≥$100k unrestricted per winner | **Opens Sept 2026**, broader early-stage eligibility | ★★★★☆ | Medium |
| | **[HealthTech Hub Africa](https://thehealthtech.org/)** (Kigali) | Accelerator + market access into public health systems | Rolling cohorts — watch | ★★★★★ | Medium |
| | **[timbuktoo HealthTech Hub](https://www.undp.org/rwanda/press-releases/call-applications-timbuktoo-healthtech-startup-accelerator-programme-kigali)** (UNDP, Kigali) | Part of a **$1B / 10-year** initiative; 6-month accelerator | Cohort-based — watch | ★★★★☆ | Medium |
| | **[LINGUA Africa](https://www.ai4d.ai/calls/lingua-africa)** (Masakhane + Microsoft + Gates + Google.org) | **Sectoral applications: up to $250k cash + $400k compute** | Round 1 closed 15 Jun 2026 — **watch for round 2** | ★★★★★ | Medium |
| | **[Google for Startups Accelerator Africa](https://startup.google.com/programs/accelerator/africa/)** Class 11 | Equity-free; alumni have raised $263M | Applications typically open ~Feb | ★★★☆☆ | Medium |
| | **[Multilingual AI for Health Challenge](https://opportunitiesforyouth.org/2026/05/14/multilingual-ai-for-health-challenge-2026-build-ai-systems-for-african-languages-and-win-up-to-5000-usd/)** (HASH / Makerere / Sunbird AI) | $2,500 / $1,500 / $1,000 | 2026 round closed 21 Jul — **Akan was explicitly listed**; watch 2027 | ★★★☆☆ | Low |
| | [Africa Health ExCon Accelerator](https://msmeafricaonline.com/call-for-applications-africa-healthtech-excon-accelerator-2026-for-health-innovation-startups/) | 6-month programme, up to 15 startups | Open 2026 | ★★★☆☆ | Low |
| | [Google.org AI Breakthrough Fund](https://www.google.org/) | **$1–3M grants**, health a focus area | Rolling / open call | ★★☆☆☆ *(too early)* | High |
| | [Tony Elumelu Foundation](https://www.tonyelumelufoundation.org/) | $5,000 seed + training | **1 Jan – 1 Mar** annually | ★★☆☆☆ | Low |

**Notes on the borderline ones.** *Gates GC* is a poor topical fit (family planning,
not hypertension) and requires an existing operational user base — enter only if you
have a real cohort by the 25th, which you don't. *Villgro Africa's* current
accelerator is eye health (closed Jan 2026) — wrong vertical, but they co-implement
HealthTech Hub Africa, so the relationship is worth having. *Milken-Motsepe's* live
prize is Circular Economy; their health prize is not currently open.

### My recommendation, in order

1. **Enter Sahara CodeSwitch (opens 15 Aug, closes 15 Sept).** Highest fit on the
   board, lowest marginal effort, and the sponsor is the one organisation whose stack
   you already run. You did not place in the August hackathon — the six-week main
   challenge is where that gets corrected, and the judging explicitly rewards
   *benchmarking across models* and *a functional product, not a transcription demo*.
   That is a description of your repo. **Fix the recording gap first**: your benchmark
   still rests on one speaker.
2. **Apply to the Africa Prize (closes 8 Sept).** £50k, an 8-month commercialisation
   programme, and they have shortlisted AI cardiac and maternal health tools before.
   The overlap with #1 is high, so write both in the same fortnight.
3. **Get on HealthTech Hub Africa's radar now.** Founded by the **Novartis Foundation**
   — the same funder that ran ComHIP in Ghana. There is no warmer strategic lead in
   this entire document.
4. **Watch for LINGUA Africa round 2.** $250k cash + $400k compute for a *sectoral
   application* of African-language AI is the single largest well-fitting cheque here.

---

## 9. What to do in the next 90 days

The pattern across every winner in this document is the same: **a real user base and a
measured outcome**. Features are not the constraint. Evidence is.

**Weeks 1–2 — close the benchmark gap.**
Get 3–5 speakers recorded per `benchmark/recording/RECORDING_GUIDE.md`. Your current
English control is one speaker, five utterances. Every claim in a submission rests on
it, and a reviewer will notice. This is also the gating item for Sahara CodeSwitch.

**Weeks 1–4 — submit Sahara CodeSwitch and the Africa Prize.** Both close inside the
window. Reuse one narrative core.

**Weeks 2–6 — get one clinic.** Not a pilot study. One clinic, twenty hypertensive
patients, four weeks. The metric that matters is not accuracy — it is **how many
patients disclosed a cost barrier they had never told the clinician**. That number is
your entire company in one statistic, and nothing else in this document has it.

**Weeks 4–8 — a named clinical collaborator.** The Mensah et al. Akan ASR paper has a
co-author at the **University of Ghana Health Service** (see [LANDSCAPE.md](LANDSCAPE.md) §7).
Redbird has 360 pharmacies and a J&J Foundation relationship. Either is a warm route
to both a clinical partner and an ethics pathway. Two emails.

**Weeks 6–12 — a MedGemma/Gemini path.** Not to replace Groq, but so that a Google
application isn't disqualified on stack. Every Google-picked health winner ran on
Google's health models. Given `ai.py` already isolates the LLM behind a service
boundary with rule-based fallbacks, this is a provider addition, not a rewrite — the
same shape as the existing STT/TTS provider chains.

**Reframe the pitch throughout.** Not *"a WhatsApp bot for hypertension"* — that loses
to MomConnect and ComHIP before you finish the sentence. Instead:

> **VeloxaCare turns unstructured Twi and Pidgin speech from chronic patients into
> structured, reason-coded clinical actions — and routes the ones caused by cost to
> an NHIS-covered alternative.** ComHIP proved community hypertension management works
> in Ghana; we make it cheap enough to scale, in the language the patient actually
> speaks.

That sentence is EpiCast's winning verb, Ghana's proven clinical model, and the one
thing nobody else in this document does — in a single line.

---

## Appendix — source index

**Funding:** [Africa Health Ventures #28](https://rowenaluk.substack.com/p/africa-health-ventures-28) ·
[healthcare.digital](https://www.healthcare.digital/single-post/healthtech-africa-emerges-in-2025-driven-by-significant-investments-and-innovation) ·
[Kapsule](https://kapsuletech.com/blog/digital-health-africa/)

**Google:** [MedGemma Impact Challenge](https://blog.google/innovation-and-ai/technology/health/med-gemma-impact-challenge/) ·
[DS4Health Ideathon](https://research.google/blog/spotlight-on-innovation-google-sponsored-data-science-for-health-ideathon-across-africa/) ·
[Accelerator Class 10](https://blog.google/intl/en-africa/company-news/meet-the-15-startups-joining-the-google-for-startups-accelerator-africa-class-10/) ·
[$37M AI commitment](https://www.connectingafrica.com/ai/google-commits-37m-to-advancing-ai-in-africa)

**Ghana hypertension:** [ComHIP](https://www.novartisfoundation.org/past-programs/better-hearts-better-cities/community-based-hypertension-improvement-project-comhip) ·
[Africa Briefing on ComHIP](https://africabriefing.com/when-the-shopkeeper-measures-blood-pressure-novartis-foundation-tackles-hypertension-in-ghana/) ·
[NHIS adherence study](https://link.springer.com/article/10.1186/s12872-025-05410-3) ·
[roadblocks roundtable](https://pmc.ncbi.nlm.nih.gov/articles/PMC11465716/) ·
[insurance & BP control, NG+GH](https://pmc.ncbi.nlm.nih.gov/articles/PMC9893381/)

**Comparables:** [mDoc](https://www.psi.org/project/self-care/member-spotlight-mdoc/) ·
[Famasi](https://www.famasi.africa/) ·
[Redbird](http://redbird.co/2021/04/15/redbird-closes-1-5m-seed-round/) ·
[MomConnect](https://en.wikipedia.org/wiki/MomConnect) ·
[PROMPTS](https://jacarandahealth.org/prompts/) ·
[Viamo AVA](https://viamo.io/ask-viamo-anything-ai/) ·
[Viamo IVR vs SMS](https://viamo.io/global-health/voice-wins-over-text-how-ivr-outranked-sms-in-hiv-self-tests/) ·
[Penda × OpenAI](https://openai.com/index/ai-clinical-copilot-penda-health/) ·
[Ilara](https://african.business/2026/05/innov-africa-deals/clinics-at-scale-how-ilara-health-is-building-africas-quiet-health-infrastructure)

**Voice AI:** [Intron expansion](https://disruptafrica.com/2025/07/04/nigerian-voice-ai-startup-intron-expands-from-health-into-other-key-sectors/) ·
[Sahara v2](https://kenyanwallstreet.com/intron-launches-new-voice-ai-service-sahara-v2) ·
[Sahara CodeSwitch, 97 teams](https://techcabal.com/2026/08/04/97-teams-at-the-deep-learning-indaba-take-on-africas-language-mixing-problem/) ·
[Lelapa AI](https://www.technologyreview.com/2023/11/17/1083637/lelapa-ai-african-languages-vulavula/)

**Opportunities:** [Africa Prize](https://africaprize.raeng.org.uk/about-the-prize/how-to-apply/) ·
[MIT Solve](https://solve.mit.edu/challenges/10-for-10-challenge) ·
[HealthTech Hub Africa](https://thehealthtech.org/) ·
[timbuktoo HealthTech](https://www.undp.org/rwanda/press-releases/call-applications-timbuktoo-healthtech-startup-accelerator-programme-kigali) ·
[LINGUA Africa](https://www.ai4d.ai/calls/lingua-africa) ·
[Gates Grand Challenges](https://gcgh.grandchallenges.org/) ·
[Multilingual AI for Health](https://opportunitiesforyouth.org/2026/05/14/multilingual-ai-for-health-challenge-2026-build-ai-systems-for-african-languages-and-win-up-to-5000-usd/)
