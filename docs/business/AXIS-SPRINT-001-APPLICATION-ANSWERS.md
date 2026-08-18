# Axis Sprint 001 Accelerator — VeloxaCare Application Answers

Ideation Axis Group · 12-week venture-building program · Demo Day close.

**Applying as:** Team — John Evans Okyere (founder & CEO, product & technology) +
Deborah Boluwatife Adeolu (co-founder & COO), with Asamoah as Program Lead for
business development & client delivery.
**Format:** Hybrid — Accra-based, so eligible for in-person workshops and Demo Day.

## The framing rule for every answer on this form

**Wedge and endgame, in that order, in the same breath.**

The company is what
[EXECUTE-AFRICA-VELOXACARE-AI-NATIVE-HEALTH-OS.md](EXECUTE-AFRICA-VELOXACARE-AI-NATIVE-HEALTH-OS.md)
describes: an AI-native healthcare operating system for African clinics — a
shared permissioned health-and-operations graph, worked by a workforce of agents,
with licensed humans holding every clinical decision. Say that. It is the answer
to "long-term vision," which is on their selection criteria.

But never say it alone. A committee that reads thirty applications has read
"operating system for African healthcare" before, and the ones that convince are
the ones that can name the first thing that works. So every vision claim is
immediately followed by the proof: *the first agent is built and live — WhatsApp
care coordination that detects why a chronic patient stopped and routes cost to
an NHIS alternative.*

The failure modes, in both directions:

- **Too small** — describing a WhatsApp adherence bot. Reads as a feature, not a
  company, and invites "what happens when Twilio ships this?"
- **Too big** — describing intake, triage, documentation, claims, pharmacy, labs,
  referrals and reporting as though they exist. You are at MVP with no live
  pilot. This is the failure the phrase "we are less interested in polished pitch
  decks" was written about, and one mentor question exposes it.

Present the agents that do not exist yet as *sequence*, never as inventory:
"documentation, triage, pharmacy, claims and management reporting are the agents
that follow, on the same graph." That is a roadmap. A feature list is a lie.

---

> **Before submitting:** the Execute Africa form displayed "300 words" but
> enforced a 300-*character* limit. Paste each answer into the field and check
> what actually fits before trusting the word counts below. Short fallbacks are
> provided for every long answer.

---

## Placeholders to fill before submission

| Field | Value |
| --- | --- |
| Q13 Years of professional experience | ☐ 1–2 ☐ 3–5 ☐ 6–10 ☐ 10+ |
| Q14 Highest level of education | ☐ High School ☐ Diploma ☐ Bachelor's ☐ Master's ☐ PhD |
| Q8 LinkedIn URL | _______________ |
| Q9 Portfolio / CV / personal website | _______________ |
| Q11 X profile (optional) | _______________ |
| Asamoah's full name, email, LinkedIn | _______________ |
| Q23 Advisors — do you have any? | _______________ |
| **Q39 Price per active patient per month** — the market model assumes US$1.50 (~GHS 20) | _______________ |
| Q39 Chronic patients per target clinic — model assumes 400 | _______________ |
| Q43/44 Is a landing page live? | _______________ |
| Q44 Live demo URL · demo video URL | _______________ |
| City (confirm) | Accra |

---

## Q1–Q11 — Identity and links

| # | Field | Answer |
| --- | --- | --- |
| 1 | First Name | John |
| 2 | Last Name | Okyere |
| 3 | Email | okyerevansjohn@gmail.com |
| 4 | Contact (WhatsApp) | +233 54 495 4643 |
| 5 | Contact (calls) | +233 54 495 4643 |
| 6 | Country | Ghana |
| 7 | City | Accra |
| 8 | LinkedIn | _fill in_ |
| 9 | Portfolio / CV / site | Best option: the live VeloxaCare demo URL. Second: the GitHub repo README — it opens with the problem, the product, and the benchmark. Give both if the field accepts them. |
| 10 | GitHub (optional) | github.com/JohnEvansOkyere |
| 11 | X (optional) | _fill in or leave blank_ |

**On Q9** — do not send a bare CV if you can send the working product. This
committee says it is "less interested in polished pitch decks and more
interested in exceptional founders." A URL where they can press a mic button and
watch an escalation fire is worth more than any PDF.

---

## Q12 — Are you currently working on this startup full-time?

**No.**

Answer honestly. The commitment question is answered by Q15 and Q16 with
evidence, not by a checkbox. If the form gives you a comment box, add:

> Not yet full-time, but VeloxaCare is where all my building time goes. In the
> last month I shipped the product end to end, ran a four-model speech benchmark
> with human speakers, and moved three clinics to proposal stage. I can commit
> fully to the 12 weeks.

---

## Q13 — Years of professional experience

_Your answer._ Pick the bracket honestly; a low number is not a weakness here —
the committee explicitly selects at idea and prototype stage.

---

## Q14 — Highest level of education

_Your answer._

---

## Q15 — Tell us about yourself (300 words or less)

### Submission answer (~295 words)

I am a software engineer in Accra, and I am building VeloxaCare because of my
mother. She nearly died after missing her diabetes medicine.

That is not a rare story here. In Ghana, 55% of chronic patients do not take
medication as prescribed, and in one study 96% said the reason was cost — not
forgetting. A reminder bot would have been useless to her. So VeloxaCare does
not just ask whether a patient took their drugs. It detects *why* they stopped —
cost, forgot, side effect, ran out — and routes each reason to a different
action. A cost barrier escalates to the care team and triggers an NHIS-covered
alternative. Patients can answer by voice note in Twi-English or Pidgin-English,
because that is how people actually speak.

I built the system myself: FastAPI backend, React clinician dashboard, WhatsApp
Cloud API integration, and a four-provider speech layer that falls back to a
model running offline on CPU, so a district clinic with no internet still works.
Then I benchmarked it against four speech models on human Ghanaian recordings,
with signed consent and de-identified speaker IDs. It produced findings I could
not have guessed: one commercial API rejects every Ghanaian language code while
accepting Swahili, and it heard a blood pressure of 116 as 160 — the difference
between a stable patient and an emergency.

I have taken it to market too. Five providers contacted; three — Sonrisa Dental,
Impact Medical & Diagnostic Centre, and Rivia Clinics — have requested proposals
or meetings. I registered Veloxa Technology Limited, and I build it with my
co-founder Deborah, who runs operations — we shipped a company together before
this one.

I am the right person because I have the reason, the ability to build it alone,
and a record of shipping. What I need now is the commercial discipline this
Sprint teaches.

### Short fallback (297 characters)

My mother nearly died after missing her diabetes medicine. I built VeloxaCare
alone — WhatsApp voice care for chronic patients in Ghana that detects *why*
they stop, not just whether. Live product, four-model speech benchmark, three
clinics at proposal stage. I ship; I need commercial discipline.

---

## Q16 — Why are you building this company?

### Submission answer (~200 words)

Because the failure that nearly killed my mother is invisible to the health
system, and it is invisible on purpose.

When a patient cannot afford their refill, they do not call the clinic to say
so. They simply stop, and nobody finds out until the next appointment — if they
even show up. The clinic records it as non-compliance. It was actually poverty,
and it was solvable: there was a cheaper NHIS-covered drug the whole time.

That gap between what a patient is going through and what their care team can
see is what I am building against. Every silent dropout is a person the system
had the information to save and no way to hear.

The technology is finally cheap enough to close it. Ghanaians already live on
WhatsApp. Speech models can now understand Twi-English. Nothing needs to be
installed, and nothing needs to be explained to a patient beyond "reply."

And once you see it as a coordination failure, you cannot stop seeing it. The
same gap loses referrals, loses lab results, lets medicines run out and lets
claims get rejected. So I am not building a reminder app. I am building the
operating system that coordinates the whole patient journey for African clinics —
starting with the patients who disappear, because that is the problem in front of
me and the people it hurts are mine.

### Short fallback (289 characters)

My mother nearly died from a missed medicine she could not afford. Patients do
not tell clinics they have stopped — they just stop, and it looks like
non-compliance. I am building the layer that lets a clinic keep hearing from a
patient after they leave. Ghana, hypertension, WhatsApp first.

---

## Q17 — What gives you an unfair advantage?

**Select: Lived experience · Technical expertise · Research**

Skip *Industry experience* unless you have clinical or health-sector employment
to point at — a claim you cannot defend in a mentor conversation costs more than
the checkbox is worth. Skip *Existing network* for the same reason: five cold
outreaches with three replies is a working sales process, not a network. Say so
when you get the chance; it is a stronger story than the checkbox.

If the form allows a supporting note:

> **Lived experience** — my mother nearly died from a missed medicine she could
> not afford. That is why the product detects the *reason* a patient stopped,
> not just the fact.
> **Technical expertise** — I built the whole system myself: WhatsApp
> integration, clinician dashboard, and a speech layer that keeps working
> offline on a clinic's laptop with no internet.
> **Research** — I ran a four-model speech benchmark on human Ghanaian
> recordings and found that the commercial APIs cannot even be told a patient is
> speaking Twi, and that one of them misheard a blood pressure of 116 as 160.
> Nobody building on those models by default knows this. I measured it.

---

## Q18 — Are you applying as?

**Team.**

- **John Evans Okyere** — Founder & CEO. Product, technology, clinical-safety
  boundaries, pricing, final decisions. Built the entire system.
- **Deborah Boluwatife Adeolu** — Co-founder & COO. Operations and delivery.
  Technical, full-time. We built VeloxaRecruit together before this.
- **Asamoah** — Program Lead, Business Development & Client Delivery (not a
  co-founder). MBA in Project Management. Owns prospect → meeting → discovery →
  demo → proposal → pilot → paying client, and coordinates pilot onboarding.

Full details in Q19–Q20 below.

---

## Q19 — Number of co-founders

**1** — Deborah Boluwatife Adeolu.

Asamoah is a Program Lead (business development & client delivery), not an
equity co-founder, so he goes in Q20 as a team member rather than being counted
here. If the form's wording turns out to mean *total founders including you*,
answer 2.

---

## Q20 — Team members details

| Name | Role | Email | LinkedIn | Technical | Full-time |
| --- | --- | --- | --- | --- | --- |
| John Evans Okyere | Founder & CEO — product, engineering, clinical-safety boundaries | okyerevansjohn@gmail.com | _fill in_ | Yes | No |
| Deborah Boluwatife Adeolu | Co-founder & COO — operations, delivery | deeodeola@gmail.com | linkedin.com/in/debbie-adeolu-boluwatife | Yes | Yes |
| Asamoah _[surname]_ | Program Lead, Business Development & Client Delivery (not a co-founder) — MBA, Project Management | _fill in_ | _fill in_ | No | _fill in_ |

If the field is plain text rather than a table, use one line each:

> **John Evans Okyere** — Founder & CEO. Product, engineering and
> clinical-safety boundaries. okyerevansjohn@gmail.com · [LinkedIn] · Technical:
> Yes · Full-time: No.
> **Deborah Boluwatife Adeolu** — Co-founder & COO. Operations and delivery.
> deeodeola@gmail.com · linkedin.com/in/debbie-adeolu-boluwatife · Technical: Yes
> · Full-time: Yes.
> **Asamoah [surname]** — Program Lead, Business Development & Client Delivery.
> MBA in Project Management. Runs prospect → discovery → demo → proposal → pilot.
> Not a co-founder.

---

## Q21 — How did you meet your team?

### Submission answer (~110 words)

Deborah and I met on Azubi Africa's data analytics training, Track 2 — same
track, same sub-group of five. After the programme ended I pitched an idea for
automating recruitment with AI video interviews to her and one other person from
the group. The other person could not stay. Deborah did, and we built
VeloxaRecruit together. VeloxaCare is our second product.

So we did not meet over this idea — we had already shipped one company together
before starting it, and I know how she works when something gets hard, because
I have watched someone else walk away from the same table.

Asamoah joined later to lead business development and pilot delivery.

### Short fallback (283 characters)

We met on Azubi Africa's data analytics training, same track and sub-group. I
pitched two of them an AI recruitment idea after the programme; one left,
Deborah stayed, and we shipped VeloxaRecruit together. VeloxaCare is our second
product — we had already built one before this.

---

## Q22 — Why is this the right team to build this company?

### Submission answer (~220 words)

Because we have already done the hard version of this once.

Deborah and I built and shipped VeloxaRecruit together before VeloxaCare
existed. We know each other's working rhythm under a deadline, and I know she
stays — when we started, a third person left and she did not. Most founding
teams find that out at month eight. We found it out before we began.

The split is clean. I build. I wrote the entire VeloxaCare system — the WhatsApp
integration, the clinician dashboard, and a speech layer that keeps working
offline when a clinic's internet does not — and I hold the clinical-safety
boundary that keeps the AI out of diagnosis. Deborah is COO and technical, and
she runs delivery: onboarding, operations, and everything that has to work on
the twentieth clinic, not just the first. Asamoah leads business development with
an MBA in project management, moving providers from first conversation to signed
pilot.

And the reason is not abstract for me. My mother nearly died after missing her
diabetes medicine. I am not going to get bored of this problem.

What we do not have is a clinician on the team. We have designed around that —
all escalation is rule-based, never AI-decided, with a human always in the loop —
but a practising Ghanaian clinician advisor is what I most want from this
programme.

### Short fallback (298 characters)

We shipped a company together before this one — VeloxaRecruit — so we already
know how each other works under pressure. I build and own clinical safety;
Deborah runs delivery; Asamoah runs BD. And my mother nearly died from a missed
medicine, so I will not get bored of this problem.

---

## Q23 — Do you have advisors or mentors?

_Your answer — I have no record of any in the repo._

If you have none, answer honestly and turn it into an ask. A short, specific
"no" reads better to a selection committee than a padded list:

> Not formally yet. The two I am actively looking for are a practising Ghanaian
> clinician to review our escalation protocols, and someone who has sold software
> into Ghanaian private health facilities and dealt with NHIS. Both are a large
> part of why I am applying.

---

## Q24 — Startup Name

**VeloxaCare** — a product of Veloxa Technology Limited.

---

## Q25 — One-sentence pitch (max 100 characters)

### Submission answer (92 characters)

An AI-native operating system for African clinics, starting with the patients who disappear.

### Alternatives, all under the limit

- (86) An AI-native operating system for African clinics — starting where patients disappear.
- (92) WhatsApp care that catches why chronic patients stop their medicine — before they disappear.
- (85) WhatsApp follow-up for chronic patients that detects why they stop, not just whether.

Use the first for this application: it names the company you are building, and
the second clause proves you have a real wedge rather than a slide. Keep the
WhatsApp versions for clinic sales, where the buyer wants the tool, not the
platform.

Count the characters in the field itself before submitting — an em dash or a
curly apostrophe can be counted differently by different forms.

---

## Q26 — What problem are you solving?

### Submission answer (~215 words)

African healthcare is not short of effort. It is short of coordination.

A patient's care is scattered across a paper folder, a clinic's software, a
pharmacy's ledger, a lab's report and a claims portal that do not talk to each
other. Patients repeat their history at every desk. Referrals, results and
follow-ups fall between institutions. Nurses and doctors spend their hours on
documentation and claims instead of patients. Medicines run out with no warning.
And no manager can say, on a given morning, which patients are at risk, what will
be out of stock this month, or where revenue leaked.

The sharpest and most measurable instance of that failure is what happens after
a patient walks out. More than half of chronic patients stop their medication
within weeks. In one Ghanaian study, 96% of those who stopped said the reason
was **cost**, not forgetting — and none of them told the clinic. There is no
moment anywhere in the system where a patient can say "I cannot afford this
month's refill," so it is recorded as non-compliance and answered with more
education, when it was poverty and a cheaper NHIS-covered drug existed the whole
time.

Nothing in the system is listening between visits. The patient returns with a
preventable complication, and the facility has lost the outcome, the patient and
the revenue.

### Short fallback (299 characters)

African healthcare is short of coordination, not effort — care is scattered
across folders, systems and desks that do not talk. The sharpest instance: over
half of chronic patients stop their medicine, 96% because of cost, and nobody
tells the clinic. Nothing is listening between visits.

---

## Q27 — Who experiences this problem?

### Submission answer (~200 words)

**Patients.** Ghanaians living with hypertension and diabetes — usually 40+,
often on a single income, paying cash or partly covered by NHIS. They ration
tablets, switch to herbal alternatives, or stop entirely, then arrive at hospital
with a stroke or kidney damage that was preventable.

**Nurses and doctors.** They carry the failure and cannot fix it. A doctor
discovers a drop-off at the consultation, with no record of the three months in
between. A nurse who wants to follow up has a personal handset and no time.
Clinical staff spend hours on documentation, claims and coordination that are not
care.

**Facility owners and managers.** Small and mid-sized private clinics,
specialist practices, and pharmacies serving chronic patients — the ones that
need a real operating system and cannot afford enterprise hospital software. A
chronic patient is worth roughly twelve refills a year; half drop off after
three. That is retention revenue leaving quietly, and nobody on staff can name
which patients are going. They also cannot see stockouts coming or why a claim
was rejected.

We start with hypertension in private clinics and pharmacies in Accra, because
the condition is chronic, the drugs are cheap, and the drop-off is measurable
inside 60 days.

### Short fallback (297 characters)

Patients with hypertension and diabetes who ration or stop. The nurses and
doctors who only find out three months later. And the small private clinics and
pharmacies that need a real operating system but cannot afford enterprise
hospital software. We start with hypertension in Accra.

---

## Q28 — How are they solving it today?

### Submission answer (~190 words)

With paper, with software that stops at the door, and mostly not at all.

Inside the building, facilities run on a paper folder, a spreadsheet, or a
hospital management system built for record-keeping — plus a separate claims
portal and a separate pharmacy ledger. Ghana's national programmes, LHIMS,
DHIMS2 and NHIS CLAIM-it, are real progress, but they store records and process
claims. None of them coordinates: none decides what should happen next, assigns
it to someone, and checks whether it happened.

Outside the building there is nothing. The honest answer from clinics is "we
can't" — once a patient leaves, the next data point is whether they show up in
three months. Where anything exists it is a nurse calling a few patients from
her own handset between duties until the day gets busy, or WhatsApp broadcasts
from a personal number with no record of who replied, or SMS reminders with no
reply path, so a patient who is struggling has no way to say so.

We have watched that front door directly. One provider we approached — a company
whose own promise is a better patient experience — answered our first message
with an automated support ticket and replied seven hours later.

Patients solve it themselves by halving doses to stretch a pack, switching to
herbal remedies, or waiting for symptoms. All three are invisible to the clinic.

### Short fallback (298 characters)

Paper, spreadsheets, and software that stops at the door. LHIMS and CLAIM-it
store records and process claims; nothing decides what happens next and checks
that it happened. Outside the building there is nothing — a nurse phoning from
her own handset, or SMS with no reply path.

---

## Q29 — What is your solution?

### Submission answer (~260 words)

VeloxaCare is an AI-native operating system for African clinics: a shared,
permissioned health-and-operations graph, worked by specialised AI agents, with
licensed humans holding every clinical decision.

**The graph is the product.** Patient identity and consent, the longitudinal
record, care plans, encounters, appointments, referrals, prescriptions, pharmacy
stock, lab orders, billing and NHIS claims — and, critically, tasks,
escalations, approvals and audit. A patient record here is not a document. It is
a live model of what needs to happen next, who is responsible, and whether it
actually happened. LHIMS, NHIS, labs, mobile money and Ghana Card connect at the
boundary; they never define the core.

Every event runs one loop: understand it, decide the next step, let policy decide
whether an agent may act or a human must approve, execute, track the outcome,
learn what worked.

**We have built the first agent of that workforce, and it is live.** Patient
access and care coordination, over WhatsApp — no app to install. Patients reply
by text or by voice note in Twi-English or Pidgin-English. The system works out
*why* a patient stopped — cost, forgot, side effect, ran out — and routes each
reason to a different action: cost escalates to the care team and opens an
NHIS-covered-alternative workflow. The doctor gets one page before clinic, every
patient ranked by risk, with the reason.

Safety is a boundary, not a promise: escalation thresholds are fixed rules, never
a model's judgement, and it keeps running offline when the clinic's internet does
not.

Documentation, triage, pharmacy, claims and management reporting are the agents
that follow — on the same graph.

### Short fallback (298 characters)

An AI-native operating system for African clinics: one permissioned health-and-
operations graph worked by AI agents, humans holding every clinical decision. The
first agent is live — WhatsApp care coordination that detects *why* a patient
stopped and routes cost to an NHIS alternative.

---

## Q30 — Why is now the right time for this startup?

### Submission answer (~235 words)

Until about two years ago this system could not have been built. Three things
changed, and it needs all three.

**Software can finally do the work, not just store it.** Every previous
generation of health software was a filing cabinet — a human read the record and
decided everything. AI agents can now read a message, structure it, decide the
next step and open a task. That is the difference between a record system and an
operating system, and it is why an AI-native architecture beats bolting a chatbot
onto an existing HMS. It also collapsed the cost: classifying why one patient
slipped now costs a fraction of a pesewa, which is what makes per-patient pricing
work at Ghanaian prices.

**Speech models are only now learning to hear Ghanaians — and I can date it.**
The African-built provider documents Twi, Akan, Pidgin and Ga; the major
commercial one rejects all four outright with explicit errors while accepting
Swahili. I measured that rather than assuming it. And the specific capability
our patients need — Akan–English *code-switching*, not either language alone —
was still being rolled out while we were testing. We are building at the exact
moment the infrastructure arrives; a year ago this product could not have
understood its own users, and a system that requires a 55-year-old in Kumasi to
type formal English is a different, worse system.

**Ghana is digitising, and the coordination layer is the gap.** LHIMS, DHIMS2 and
NHIS CLAIM-it are live, so facilities now expect to run on software — but those
manage records and claims inside the building. Nothing coordinates the journey or
follows the patient home, while the non-communicable-disease burden grows.

WhatsApp and mobile money are already universal here. The adoption barrier is
gone. Only the coordination is missing.

### Short fallback (298 characters)

Three things just changed: AI agents can now do the work instead of storing it,
so an operating system beats a filing cabinet; African speech models can finally
hear Twi and Pidgin (measured — a major API rejects all four); and Ghana is
digitising records while nothing coordinates the journey.

---

## Q31 — Which industry best describes your startup?

**HealthTech.**

Pick HealthTech, not AI. The buyer is a health facility and the outcome is
clinical and operational; AI is the architecture, not the category. "AI-native"
is doing that work in every answer already. If a later question asks for a
secondary category, that is where the agent and speech work belongs.

---

## Q32 — Startup stage

**MVP.**

The honest read. You have a complete working product — WhatsApp integration,
clinician dashboard, voice, escalation logic, deployed — but no patients using
it in a live clinic yet. That is MVP, not Beta Users.

Move to **Beta Users** the moment a pilot goes live with real patients. Do not
claim it before then; the first mentor conversation will find it, and the same
committee that forgives an early stage does not forgive an inflated one.

---

## Q33 — Have you spoken with potential customers?

**Yes.**

Five providers contacted. Three moved forward: Impact Medical & Diagnostic
Centre (visited in person, proposal requested), Rivia Clinics (proposal
requested), and Sonrisa Dental Clinic (replied "we would like to know more,"
meeting requested). Two more — The Bank Hospital and First American — are in
outreach. We also run a structured discovery script built to find the drop-off
number in the provider's own words before any demo.

---

## Q35 — What is the biggest insight you learned?

> This sits right after "have you spoken with potential customers," so answer it
> as a **customer** insight. The alternative below is for a product or technical
> section — do not use both.

### Submission answer (~205 words)

That the problem I built for is narrower than the problem people actually have.

I built VeloxaCare for hypertension — the cost insight, the escalation
thresholds, all of it aimed at chronic disease. Then I took it to market, and the
three providers who moved fastest were not chronic-care clinics at all.

A dental clinic replied asking to know more, because their version is the
six-month recall that never happens and the post-procedure patient nobody checks
on. A multi-specialty diagnostic centre asked for a proposal, because their
version is a patient who uses one of sixteen services and never discovers the
other fifteen. An employee-health company asked for a proposal, because their
version is members who never use the care their employer already paid for.

Same failure in different clothes: the patient leaves, and nobody has a way to
reach them.

Three things followed. It is a large part of why I now describe VeloxaCare as an
operating system rather than an adherence tool — the coordination gap is general,
and hypertension is just where it is easiest to measure. It changed how I sell:
to a clinician this is patient care, to an owner it is retention revenue, and it
is the same feature said two ways.

And the third thing was deciding *not* to chase it. What those clinics want right
now is recall reminders, and a reminder is the one part of this that anyone can
copy. Our advantage — detecting why a patient stopped and routing cost to an
NHIS-covered alternative — only pays off where medicine cost is the failure
mode. So the demand told me how big the eventual platform is, not what to build
next. We stayed on chronic care.

### Short fallback (286 characters)

I aimed at hypertension, but the fastest movers were a dental clinic, a
diagnostics centre and an employee-health plan — same failure: the patient
leaves and nobody can reach them. It sized the platform; it did not change the
roadmap. Recall reminders are copyable; cost-routing is not.

### Alternative, if this question sits in a product or technical section (~165 words)

That I was measuring the wrong thing, and it nearly cost me the right answer.

Our speech benchmark ranked four models by word error rate, and the African-built
model came last. It had not failed. It heard "one forty-two over ninety-five" and
wrote **142/95** — it recognised the number as a blood pressure — while the
others wrote "142 over 95." Our scorer counted that as one token against three
and punished the model that had understood the content best. I fixed the
normaliser and it went from worst to best. Nothing about the audio or the models
changed.

The lesson generalises well past speech. Word error rate measures string
agreement, not comprehension, and it can rank the most useful output last. What
actually matters is whether the right patient got escalated — and on *that*
metric every model scored perfectly and none was ever fooled. We now score
downstream task success first and WER second.

It is also why I no longer trust a metric I have not tried to break.

---

## Q38 — Who is your ideal customer?

### Submission answer (~235 words)

Every facility that loses sight of a patient needs this — clinics, private
hospitals, pharmacy chains and eventually the public system. But the *ideal first*
customer is deliberately narrow, because that is what gets us to proof fastest.

**Today:** a private clinic or small hospital group in Accra with 200–600 chronic
patients, an owner or medical director who can decide alone, and an attached or
partner pharmacy. 5–40 clinical staff, no IT department, already using WhatsApp
with patients informally, and a nurse who has tried follow-up calls by hand and
given up.

The pharmacy link matters most. The clinic feels the problem; the pharmacy feels
it in cedis — a chronic patient is worth roughly twelve refills a year and half
drop off after three. Where one owner sees both sides, retention has a P&L line
and the decision takes weeks, not quarters. Big enough that the drop-off is
expensive, small enough that enterprise hospital software is out of reach.

**Concretely, one we are already talking to:** Impact Medical & Diagnostic
Centre in Asylum Down — a multi-specialty clinic with in-house diagnostics and
chronic patients spread across sixteen departments. I visited in person and they
asked for a proposal. That is the shape we are looking for.

**Then:** multi-site private hospital groups and pharmacy chains, where the same
system sells per branch. **Then:** insurers and employer health plans, who carry
the cost of every uncontrolled patient. **Then:** NGO programmes, and the public
system — CHPS compounds, district hospitals and NHIS-funded chronic care, which
is where the scale actually is.

Government is a question of sequence, not ambition. Public procurement will ask
for outcome evidence from real deployments, and we intend to have it.

### Short fallback (298 characters)

Ultimately every facility that loses patients — clinics, hospitals, pharmacy
chains, eventually the public system. First and best: an Accra private clinic
with 200–600 chronic patients, an owner who decides alone, and an attached
pharmacy, because that is where retention has a P&L line.

### If a follow-up asks why not government first

Say it plainly — it reads as judgement, not timidity:

> The public system is where the scale is, and it is where this ends up. But
> procurement there runs on cycles measured in years and will ask what outcomes
> we produced elsewhere. Private clinics let us generate that evidence in 60-day
> increments. We are building the integration boundary for LHIMS and NHIS from
> day one so that when we go, we are not rewriting the product.

---

## Q39 — How big is the opportunity? (max 250 words)

> **Set your price before submitting.** The model below assumes
> **US$1.50 per active patient per month** (roughly GHS 20 — check the rate).
> Nothing in the repo fixes a price yet, and every number moves with it. The
> patient-count assumption per clinic should also be replaced with the real
> answer as soon as your discovery meetings produce it — that is literally
> question 1 on your discovery sheet.

### Submission answer (~240 words)

**Ghana, the wedge.** About 27% of Ghanaian adults are hypertensive — roughly 5
million people. Fewer than half know it, and only about a quarter of those
diagnosed have it under control. That leaves ~2.3 million diagnosed adults who
need lifelong follow-up nobody is providing. At US$1.50 per active patient per
month, that is a **US$41M annual market in hypertension alone** in Ghana. Add
diabetes and it is roughly US$60M.

**Our serviceable slice.** Private-sector chronic patients under active facility
care — call it 15% of the diagnosed population, ~350,000 patients — is a
**US$6M annual market** we can reach with the product as it exists today,
through a sales motion we are already running.

**Three years.** 40 facilities averaging 400 chronic patients is ~16,000 patients
and ~US$290K ARR — enough to prove the model, and a rounding error against the
ceiling.

**Where it actually goes.** Chronic care is the wedge, not the business. The same
graph runs documentation, triage, pharmacy, claims and reporting, which moves us
from US$1.50 per patient to a facility operating-system subscription — an order
of magnitude more per account, sold into clinics that already trust us.

**And the continent.** Hypertension prevalence across sub-Saharan Africa is
comparable to Ghana's, against ~1.1 billion people, and the same conditions hold
everywhere: WhatsApp ubiquity, mobile money, thin clinical staffing, fragmented
records. Ghana is the proving ground, not the market.

### Short fallback (251 characters)

27% of Ghanaian adults are hypertensive — ~5M people, 2.3M diagnosed and
unfollowed. At $1.50/patient/month that is $41M a year in Ghana on hypertension
alone, ~$60M with diabetes. Chronic care is the wedge; the same graph then sells
as a facility OS.

**Sources for the prevalence figures** (keep these to hand; a judge may ask):
- Pooled hypertension prevalence 27.0% across 85 studies / 82,045 subjects —
  [PLOS One systematic review & meta-analysis](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0248137)
- Awareness 45.9%, control 23.8% — same review.
- 28.1% prevalence, WHO STEPwise method, middle-belt Ghana —
  [Int. J. Hypertension](https://www.hindawi.com/journals/ijhy/2019/1089578/)

**Assumptions you are responsible for defending:** Ghana adult (18+) population
~19M; price US$1.50/patient/month; 15% of diagnosed patients are in active
private-sector care; 400 chronic patients per target facility. State them if the
form has room — a committee trusts a number with visible assumptions far more
than a big round one without.

---

## Q40 — Who are your biggest competitors?

### Submission answer (~200 words)

**The status quo, and it wins most of the time.** Paper folders, a nurse's
personal handset, and nothing at all. Every deal we lose in the next year will be
lost to "we'll get to it," not to a rival.

**mPharma** (Accra) is the most serious commercial competitor. Their Mutti
platform already owns the medicine-access and affordability relationship through
a pharmacy network, plus teleconsultation and diagnostics. They are strong
exactly where our cost-barrier workflow lands — though they come at it from drug
supply, and they are as plausibly a partner as a rival.

**Helium Health** (Nigeria, live in Ghana and six other countries, 7,000+
clinicians and 300,000+ monthly patient visits) is the incumbent for facility
software. HeliumOS is the EMR that clinics buy today, and they are moving into
financing. They are the benchmark we get compared to in the room.

**mDoc** (Nigeria) is closest to our wedge — digital self-management coaching for
chronic disease, delivered by mobile and web.

**Adjacent:** conventional HMS vendors, Turn.io-style WhatsApp health
infrastructure, and Ghana's own LHIMS — all of which store records or send
messages, and none of which coordinate the journey.

### Short fallback (299 characters)

Mostly the status quo — paper, a nurse's handset, nothing. Commercially: mPharma
(Accra) owns medicine access and affordability; Helium Health is the incumbent
EMR across Ghana and six other countries; mDoc does chronic-disease coaching.
Plus conventional HMS vendors and LHIMS.

---

## Q41 — Why will customers choose you instead?

### Submission answer (~230 words)

**Against the EMRs:** they manage what happens inside the building. We are the
only one that keeps working after the patient walks out, which is where the
outcome and the repeat revenue are actually lost. An EMR records that a patient
was prescribed amlodipine. We find out that they stopped taking it, why, and get
them back on it.

**Against everyone in the space:** we detect the *reason*, not the fact. Every
other follow-up tool asks "did you take it?" and logs yes or no. That is useless
in a market where 96% of people who stop, stop because of cost. We route cost to
an NHIS-covered alternative, side effects to a human, and forgetting to a changed
reminder — three different actions from one "no."

**Against all of them, on language:** patients answer by voice note in
Twi-English or Pidgin-English. I measured this — a major commercial speech API
rejects Twi, Akan, Pidgin and Ga outright while accepting Swahili. Anyone
building on default infrastructure cannot serve the patient who cannot type
formal English.

**On trust:** escalation thresholds are fixed rules, never a model's judgement, a
licensed human decides everything clinical, and every action is audited. That is
what makes a medical director sign.

**On friction:** nothing to install, no workflow change, no staff training, and a
free 60-day pilot measured in retention. The clinic risks nothing to find out.

### Short fallback (299 characters)

EMRs stop at the door; we work after the patient leaves. Everyone else logs
whether a patient took their medicine — we detect *why* they stopped and route
cost, side effects and forgetting differently. Patients reply by voice note in
Twi-English. Escalation is fixed rules, never AI judgement.

---

## Q42 — What have you built so far?

### Submission answer (~230 words)

A working system, deployed, that a clinic could run patients through this week.

**The patient side:** a WhatsApp agent on the Meta Cloud API. Daily medication
check-ins, weekly blood-pressure requests, and replies by text or voice note in
Twi-English or Pidgin-English. It classifies why a patient slipped — cost,
forgot, side effect, ran out — and routes each to a different action, with cost
opening an NHIS-covered-alternative workflow.

**The clinic side:** a live dashboard, updating over WebSockets as messages
arrive. Patients ranked by risk, alerts, full message history with provenance on
every AI action, one-click enrolment, and an auto-generated weekly report ranking
every patient by risk before clinic.

**The safety layer:** all escalation is deterministic. A BP at or above 160/100
escalates immediately; cost or side effect escalates after two occurrences in
fourteen days. The AI never decides.

**The speech layer:** four providers with automatic fallback, ending in a model
that runs entirely offline on CPU — so a clinic with no internet still gets
transcription and escalation.

**The research:** a published benchmark of four speech models on human Ghanaian
recordings with signed consent and de-identified speaker IDs, scoring downstream
task success — did the right patient get escalated — not just word error rate.

**The commercial side:** Veloxa Technology Limited registered, five providers
approached, three at proposal or meeting stage.

### Short fallback (285 characters)

A deployed system: WhatsApp agent with voice in Twi-English, live clinician
dashboard, deterministic escalation (BP ≥160/100), four-provider speech stack
that falls back offline. Plus a benchmark of four models on consented Ghanaian
recordings. Company registered, three proposals out.

---

## Q43 — Do you currently have:

**Tick: Prototype · MVP · Web App · AI Model**

- **Landing Page** — tick only if one is actually live. If not, build one this
  week; Q44 says links raise your chances and you currently have no marketing
  surface.
- **Mobile App** — no. Do not tick. Patients use WhatsApp; that is a deliberate
  choice and a strength, not a gap.
- **Hardware** — no.
- **AI Model** — defensible to tick, but know your answer when probed: *"We
  integrate and benchmark models rather than train them. What we built is the
  layer around them — reason classification, the deterministic escalation engine,
  and a four-provider speech stack that falls back to offline."* Saying that
  before you are asked reads as rigour; being caught out reads as padding.

---

## Q44 — Product links

Provide, in this order:

1. **Live demo URL** — the deployed dashboard. Strongest single link you have.
2. **GitHub** — github.com/JohnEvansOkyere/[repo]. The README opens with the
   problem, the product and the benchmark, which is exactly the read they want.
3. **Demo video** — if the Intron challenge video exists, use it. If not, record
   90 seconds: send a Twi-English voice note, watch the escalation fire on the
   dashboard. That single clip carries the whole pitch.
4. **Benchmark report** — optional, but almost nobody in the cohort will have
   original measured research. If it is written up, link it.

---

## Q45 — Where do you see this company in 10 years?

### Submission answer (~190 words)

The coordination layer underneath African healthcare.

In ten years a patient should be able to move from a CHPS compound to a clinic,
to a pharmacy, to a specialist, to a hospital, without repeating their history,
losing a referral, or having a lab result vanish — because one system holds the
thread, and it moves with them rather than sitting inside any one building.

For facilities, VeloxaCare runs the operation: intake, documentation, triage,
appointments, pharmacy and stock, claims, labs, referrals and reporting, worked
by agents, supervised by licensed professionals. The clinician's job becomes
clinical again.

The part I care most about is the outcome data. Nobody currently knows which
follow-up interventions actually keep an African patient on treatment — the
studies are small and mostly borrowed from elsewhere. Running millions of these
loops and tracking what happened afterwards produces that evidence, and it is
both the moat and the public good.

Ghana first, because you earn the right to a continent by working properly in
one country. Then West Africa, then wherever the same conditions hold — which is
most of it.

### Short fallback (298 characters)

The coordination layer underneath African healthcare: a patient moves between
CHPS compound, clinic, pharmacy and hospital without losing their history, and
facilities run their whole operation on agents supervised by clinicians. Plus
the outcome data on what actually keeps patients on treatment.

---

## Q46 — If everything goes perfectly, what does success look like?

### Submission answer (~170 words)

Success is a number a doctor reads out to me without being asked.

Concretely, at the end of a pilot: of 30 hypertension patients, the clinic's
normal six-month drop-off would have lost half. We lost six. Eleven cost barriers
were caught and switched to NHIS-covered alternatives instead of turning into
silent dropouts. Four patients were escalated on a dangerous reading in the same
hour rather than at their next appointment. The nurses did no extra work.

Then that clinic pays, without being persuaded, and introduces us to two others.

Beyond that, success is when the drop-off statistic stops being true. Ghana
currently loses more than half its chronic patients within weeks, and treats it
as a fact of life. Making that number visibly move in even one district is the
version of this that matters.

And personally: a patient somewhere says they could not afford their medicine,
and someone hears it and acts — which is the thing that did not happen for my
mother.

### Short fallback (256 characters)

Of 30 pilot patients the clinic would normally lose half; we lose six. Eleven
cost barriers caught and switched to NHIS alternatives instead of silent
dropouts. Nurses do no extra work. Then the clinic pays without persuasion and
introduces us to two more.

---

## Q47 — What is your biggest risk?

### Submission answer (~200 words)

Not whether it works. Whether a Ghanaian clinic will pay for something it has
never had to measure.

Retention has no line item in a small private clinic's budget. Owners feel the
drop-off but have never quantified it, so the honest risk is a pilot that
delights everyone clinically and then stalls at "we love it, come back next
quarter." A free pilot proves value and simultaneously trains people to expect it
free.

Three things we are doing about it. First, price against the pharmacy, not the
clinic budget — a chronic patient is ~12 refills a year and the pharmacy has a
direct P&L link, so we sell to whoever owns both. Second, agree the drop-off
baseline *before* the pilot starts, in the clinic's own numbers, so the result is
their measurement and not our marketing. Third, keep the pilot deliberately
narrow — one condition, 30 patients, 60 days — so the decision is small.

The secondary risk is bus factor: I built the system alone and I am not yet
full-time on it. Deborah is technical and full-time, and the architecture is
documented, but concentration on one engineer is real and I would rather name it
than have it found.

### Short fallback (297 characters)

Not whether it works — whether a clinic will pay for retention it has never
measured. Owners feel the drop-off but never quantified it, and a free pilot
trains people to expect free. Mitigation: price against pharmacy refill revenue,
agree the baseline before we start, keep the pilot small.

---

## Q48 — Why do you want to join Axis Sprint 001?

### Submission answer (~190 words)

Because my gap is not technical, and I know exactly what it is.

I can build this. I have built it — the product works, it is deployed, and the
research behind it is original. What I have never done is convert a delighted
pilot into a signed contract, price health software for facilities that have no
budget line for it, or raise money. Those are the three things standing between
VeloxaCare working and VeloxaCare existing as a company.

Three specific asks. **Pricing and business model** for a product sold to
facilities, where the payer, the beneficiary and the user are three different
people. **Sales discipline** — I currently have three warm proposals and no
process for what happens after the pilot ends. **A clinician advisor**, because
we hold a hard clinical-safety boundary and I want a practising Ghanaian doctor
reviewing our escalation protocols before we scale, not after.

I also want the accountability. I am building alongside other commitments, and a
12-week cohort with milestones is the structure that makes people ship. Being in
Accra, I can be in the room for the in-person sessions.

### Short fallback (276 characters)

My gap is not technical. I built and deployed this; what I have never done is
convert a delighted pilot into a signed contract, price for facilities with no
budget line, or raise. I also want a clinician advisor on our escalation
protocols, and the accountability of a cohort.

---

## Q49 — What do you hope to accomplish in 12 weeks?

### Submission answer (~180 words)

Move from "it works" to "someone pays for it."

**Weeks 1–4:** two pilots live with real patients, not demo data — Impact Medical
and one of Sonrisa or Rivia are already at proposal stage. Baselines agreed in
the clinic's own numbers before day one, so the result is measurable.

**Weeks 5–8:** pricing set and tested. I want to have made a real offer at a real
price to at least five facilities and know the objection pattern. In parallel,
onboarding tightened so a new clinic goes live without me personally doing it —
that is the difference between a project and a product.

**Weeks 9–12:** first paying customer, the pilot retention data written up as a
case study, company and data-protection housekeeping done properly, and a Demo
Day pitch built on measured results rather than a promise.

The concrete milestone I will hold myself to: **one signed paying customer and
one pilot with 60 days of real retention data by Demo Day.** Everything else is
in service of those two.

### Short fallback (233 characters)

Two pilots live with real patients by week four, baselines agreed first. Pricing
set and offered to five facilities by week eight. By Demo Day: one signed paying
customer and 60 days of real retention data written up as a case study.

---

## Q50 — Which areas do you need the most help with?

**Tick: Sales · Business Model · Fundraising/Funding · Legal**

The reasoning, in case there is a comment box:

- **Sales** — three warm proposals, no repeatable close. This is the binding
  constraint on the company right now.
- **Business Model** — pricing a product where the payer, beneficiary and user
  are three different parties, and choosing between facility subscription and
  per-active-patient.
- **Fundraising/Funding** — never raised, and Demo Day is the point of the
  programme.
- **Legal** — health data under Ghana's Data Protection Act, clinical liability
  boundaries, and pilot-to-contract paperwork.

**Do not tick Product, AI, or Engineering.** You built a deployed system with an
original benchmark; claiming you need help there contradicts your own evidence
and dilutes the asks that matter. If the form allows a fifth, **Operations** is
the honest next one — onboarding a clinic currently depends on you personally.

---

## Q51 — Commit to the full 12 weeks, October–December 2026?

**Yes.**

---

## Q52 — Can you attend all required sessions?

**Yes.**

---

## Q53 — Are you based in Ghana?

**Yes** — Accra, so you qualify for the hybrid track: in-person workshops,
networking, and Demo Day. Say so if there is anywhere to say it; it signals you
will actually be in the room.

---

## Q54–Q58 — not yet drafted

The form jumps from the commitment questions to the business-plan upload. If
Q54–Q58 ask anything substantive, draft them before submitting — the evidence
bank below covers most of what they are likely to want.

---

## Q58 — Upload Business Plan (optional)

**Upload it.** See [VELOXACARE-BUSINESS-PLAN.md](VELOXACARE-BUSINESS-PLAN.md) —
export to PDF and attach.

Two reasons to bother with an optional field. Most of the cohort will skip it,
so it is cheap differentiation. And this committee said it is "less interested
in polished pitch decks" — a plain plan with its assumptions visible and its
gaps named is exactly the opposite of a deck, and reads as the thing they said
they wanted.

Fill the placeholders (demo URL, Asamoah's surname, compensation lines) before
exporting. Leave the assumptions register in. Nothing in the plan makes a claim
the rest of this form does not.

---

## Q59 — Tell us about the hardest thing you have ever built or accomplished.

> Answered from **Pharma-POS-AI**, the pharmacy point-of-sale system — not from
> VeloxaCare. It is the harder build, and it is the only evidence on this form
> that you have taken software all the way to the standard a real business
> depends on. It also frees the benchmark story for Q63.

### Submission answer (~250 words)

Pharma-POS-AI — a pharmacy point-of-sale system for Ghanaian pharmacies. I built
it alone over eight months, and it is the hardest thing I have done because of
what happens when it is wrong.

A bug in most software is an annoyance. A bug here dispenses an expired drug,
lets a cashier void a sale to cover a theft, or loses a day's takings when the
internet drops in a pharmacy that never had reliable internet to begin with. So
stock is dispensed first-expiry-first-out with row locking, because two tills can
otherwise allocate the same batch. Every stock change is append-only. Every audit
entry hashes the one before it, so no record can be silently edited. Every sale
is written to a local outbox before anything else, so nothing is lost when the
connection is.

None of that was the hard part. The hard part was the eleven audits I ran against
my own work, and what they returned: revenue that counted voided sales,
discounts that could drive a total negative, deleting a user that cascaded away
their sales *and their audit trail*. All my code. All of it looking finished.

And the hardest single decision: I had built full per-client infrastructure
isolation — separate database, separate secrets, encrypted off-platform backups
per pharmacy — and got it passing 280 tests across two deployment profiles. Then
I deleted it, because onboarding a shop should not require standing up a server.
Eight months to build it. One decision to admit I had built the wrong thing well.

### Short fallback (299 characters)

A pharmacy POS for Ghanaian pharmacies, built alone over eight months, where a
bug dispenses an expired drug. FEFO with row locking, hash-chained audit,
offline outbox. Then I ran eleven audits against my own code and deleted an
isolated-per-client architecture that already passed 280 tests.

### If a mentor asks what actually made it hard

Three things, in order:

1. **Correctness under offline conditions.** Local-first PostgreSQL, an outbox
   with monotonic sequence numbers and payload hashes, idempotent sync
   ingestion. Everything must survive the power and the internet going out
   mid-sale, on a low-spec pharmacy machine.
2. **Auditing my own work honestly.** Eleven audits between April 2026 and July
   2026, each producing a defect table with severity, file, and status. Most
   critical findings were mine.
3. **Reversing an architecture I was proud of.** Per-tenant isolation was the
   correct instinct and the wrong product decision. Pooled SaaS with enforced
   tenant scope replaced it.

---

## Q60 — What is one belief you have about your industry that most people disagree with?

### Submission answer (~215 words)

That medication adherence is an economics problem, and almost the entire industry
treats it as a psychology problem.

Nearly every adherence product ever built is a reminder — a push notification, a
pillbox, an SMS nudge — because the design assumption is that patients forget.
That assumption is correct in the health systems where the software was
designed, where medicine is covered. In Ghana it is wrong. In one study of
non-compliant patients, 96% named cost. A reminder tells a person who cannot
afford their medicine to take their medicine. It is not merely useless; it is
slightly insulting.

People disagree partly because forgetting is genuinely the failure mode
elsewhere, and partly because a reminder is far easier to build than a workflow
that identifies a cheaper NHIS-covered alternative and gets a prescriber to sign
off on it. The easy thing became the category.

The corollary gets more disagreement still: the valuable use of AI in African
healthcare is administrative, not clinical. Everyone wants to build the
diagnosing AI. But very few Ghanaian patients are harmed because a doctor could
not name their condition — they are lost *between* the visits, in the
coordination. So we keep the model out of diagnosis entirely, deliberately, and
put it on the work that is actually failing.

### Short fallback (297 characters)

Adherence is an economics problem the industry treats as psychology. Every
product is a reminder, because the assumption is patients forget. Here 96% of
non-compliant patients said cost. A reminder tells someone who can't afford
medicine to take it. The hard workflow is finding the cheaper drug.

---

## Q61 — What would you build if funding did not matter?

> This is the one question on the form where naming the whole operating system
> is not overreach — they asked. Keep the proof sentence at the end anyway.

### Submission answer (~255 words)

The whole operating system at once, instead of one agent at a time.

VeloxaCare is meant to be an AI-native operating system for African clinics: a
shared, permissioned health-and-operations graph, worked by a workforce of
specialised agents, with licensed humans holding every clinical decision. Patient
access. Clinical documentation, turning a clinician's speech into a structured
note. Triage and routing. Care coordination. Pharmacy and supply, predicting a
stockout before it happens. Claims and finance. And a facility manager agent that
answers "which patients need attention today?" in plain language.

Every event runs the same loop — understand it, decide the next step, let policy
decide whether AI acts or a human approves, execute, track the outcome, learn
from it. That loop is the system. No single agent is.

Funding is what forces me to build it in revenue order rather than dependency
order, and those are not the same order. A documentation agent alone is dictation
software. A claims agent alone is a form-filler. The compounding only starts when
one patient's event moves through all of them on one graph — which is exactly the
part no individual clinic will fund, because each of them pays for a piece and
the value shows up in the whole.

With money out of the question I would also build the two things nobody owns: the
patient continuity record that follows a Ghanaian from CHPS compound to clinic to
pharmacy, and the outcome evidence on what actually keeps an African patient on
treatment. I would publish the second one.

But this is a sequence I have started, not a wish. The first agent is live.

### Short fallback (299 characters)

The whole operating system at once instead of one agent at a time —
documentation, triage, pharmacy, claims, facility manager, all on one graph.
Funding forces revenue order, not dependency order; the compounding only starts
when a patient event runs through all of them. The first agent is live.

### If asked what specifically the money buys

Do not answer this one with "more engineers." Answer with the dependency:

> The agents that pay for themselves fastest are not the agents that unlock the
> others. Documentation and claims sell easily and sit at the edge of the graph.
> Identity, consent, the care-episode model and the task-and-audit spine sell to
> nobody and everything else depends on them. Funding buys the spine before the
> revenue, which is the correct build order and the one I cannot currently
> afford.

---

## Q62 — If we reject your application, what will you do next?

### Submission answer (~200 words)

Keep going, on a slower and more expensive path.

The pilots do not depend on you. Impact Medical and Rivia asked for proposals
before I applied here, and the plan is real patients on the system in Q4 either
way. What I lose without the Sprint is the part I cannot generate alone: I would
be pricing by guesswork, closing by instinct, and looking for a clinician advisor
through cold outreach rather than through a room that already contains one. That
costs months, and months are patients.

So, concretely, on a rejection: run the two pilots anyway with baselines agreed
up front; take the first paying customer at whatever price I can defend; and
apply to the next programme carrying 60 days of real retention data instead of a
prototype — which will be a stronger application than this one.

I would also ask you what was missing. A specific reason from a committee that
read thirty of these is worth a great deal to me, and I will take it in one line
if that is all there is time for.

None of this is contingent on a yes. The company was moving before the
application and will be moving after it.

### Short fallback (295 characters)

Keep going, slower. The pilots pre-date this application — real patients in Q4
either way. Without the Sprint I price by guesswork and close by instinct, which
costs months. I would run the pilots, take a first paying customer, ask you what
was missing, and reapply with real retention data.

---

## Q63 — Describe a time you failed and what you learned from it.

> **Check the bracketed line against what actually happened with VeloxaRecruit
> before submitting.** The shape of the answer is right; only you know the exact
> outcome. If the facts do not fit, use the alternative below.

### Submission answer (~215 words)

I built a company before I ever asked anyone to pay for one.

VeloxaRecruit — AI video interviewing — was Deborah's and my first product. We
shipped it. It worked. it never converted
into paying customers / it stalled at 0 users now. The failure was not technical, which
is exactly what made it instructive. We built for months against our own idea of
what recruiters wanted, and did the selling last, by which point the product was
already shaped.

What I learned is that order matters more than effort. Nothing about that
product would have been harder to build if we had spoken to twenty recruiters
first — it would simply have been a different product, and possibly a live one.

You can see the correction in how VeloxaCare has been run. Five providers
contacted while the product was still rough. A discovery script whose first
question is the clinic's own drop-off number, asked before any demo. Three
proposals in flight before a single pilot patient exists. And when three of those
providers turned out to want something adjacent — dental recall, cross-department
referral — I did not chase it, because the second lesson from VeloxaRecruit is
that interest is not demand.

I am still not good at closing. That is a large part of what I am applying for.

### Short fallback (294 characters)

We built and shipped VeloxaRecruit before ever asking anyone to pay. The failure
wasn't technical — we sold last, when the product was already shaped. Order
matters more than effort. With VeloxaCare I contacted five providers while the
product was still rough. Still not good at closing.

### Alternative, if the VeloxaRecruit facts do not fit (~150 words)

Now clear to use — Q59 above answers from Pharma-POS-AI, so the benchmark story
is not spoken for anywhere else on the form.

> I nearly published a false research finding because I liked the result.
>
> Our benchmark ranked the African-built speech model last on word error rate.
> That matched what the whole industry assumes, so I almost shipped it. One
> transcript did not look like a failure: the model had heard "one forty-two
> over ninety-five" and written 142/95 — it understood the number was a blood
> pressure — while the models beating it wrote the words out. My scorer counted
> understanding as three errors.
>
> The failure was not the bug. It was that a result confirming my assumptions
> got less scrutiny than one contradicting them would have. I now score
> downstream task success first, and I do not trust a metric I have not tried to
> break.

---

## Q64 — What evidence do you have that customers truly need this solution?

### Submission answer (~235 words)

Three tiers, and I will be straight about where the strongest one is still
missing.

**Population evidence.** 55% of Ghanaian chronic patients do not take medication
as prescribed. In one Ghanaian study, 96% of non-compliant patients named cost,
not forgetting. That establishes the problem at scale. It does not prove anyone
will buy a solution to it.

**Provider evidence — the real signal.** Five providers approached, three moved
forward: Impact Medical & Diagnostic Centre requested a proposal after an
in-person visit, Rivia Clinics requested a proposal, Sonrisa Dental asked for a
meeting. What convinced me was not the hit rate. It was that each one restated
the problem in their own words, unprompted, before we had described it that way.
The dental clinic's version is the six-month recall that never happens. The
diagnostics centre's is a patient who uses one of sixteen services and never
learns about the other fifteen. The employee-health company's is members who
never use care their employer already paid for. Nobody had to be sold the
problem. That is the difference between a real need and a pitch landing well.

**The evidence I do not have: nobody has paid, and no pilot has run.** Interest
is not demand, and I would rather say that in an application than dress three
proposals up as traction. Turning that sentence into a signed contract is
precisely what I am applying for.

### Short fallback (299 characters)

55% of Ghanaian chronic patients are non-adherent; 96% of those in one study
said cost. Five providers approached, three moved to proposal — and each
restated the problem unprompted in their own words. What I don't have: nobody
has paid and no pilot has run. Interest is not demand.

---

## Q65 — What assumptions about your business are you most uncertain about today?

### Submission answer (~230 words)

In order of how much damage being wrong would do.

**1. Who pays, and how much.** The entire market model runs on US$1.50 per active
patient per month. That is a modelling assumption, not a tested price — nobody
has ever been quoted it. I also do not know yet whether the buyer is the clinic,
the attached pharmacy, an insurer or an employer plan. Payer and price are one
uncertainty, and it is the biggest thing standing between this working and this
being a company.

**2. That patients keep replying.** Week-one engagement is easy. I have not
measured week six. If reply rates decay the way they do in most messaging health
programmes, the honest answer is fewer and better-timed messages, not more — but
right now that is a belief, not a finding.

**3. That the cost workflow actually resolves.** We detect a cost barrier
reliably. Whether the NHIS-covered alternative reaches the patient depends on a
prescriber signing off and a pharmacy holding stock — two things outside our
software. If that chain breaks in practice, we are an excellent detector of a
problem we cannot fix.

**4. Facility size.** The model assumes 400 chronic patients per clinic. It is a
guess, and it is question one on our discovery sheet.

A 60-day pilot resolves 2 and 3. Five real priced offers resolve 1 and 4. Both
happen inside the twelve weeks.

### Short fallback (298 characters)

Biggest: who pays and how much — $1.50/patient/month is modelled, never quoted,
and the buyer may be the pharmacy not the clinic. Then: whether patients still
reply in week six. Then: whether a detected cost barrier actually resolves, since
that depends on a prescriber and pharmacy stock.

---

## Q66 — Why are you the right person (not just a good person) to solve this problem?

### Submission answer (~240 words)

A good person would have built the reminder app.

That is the honest distinction. The reason I did not is that I watched this fail
from close up — my mother nearly died after missing her diabetes medicine, and
the problem was never that she forgot. So when I sat down to build, I already
knew the obvious product was the wrong one, and I went looking for the real
failure mode before writing a line of code. That is lived experience doing work,
not lived experience as a credential.

Then three things that are not about caring.

**I can build the whole thing, and did.** The WhatsApp integration, the clinician
dashboard, the deterministic escalation engine, and a four-provider speech stack
that keeps working offline when a clinic's internet does not.

**I measure instead of assuming.** Everyone building voice for Africa assumes the
major commercial APIs handle it. I ran the benchmark: one rejects Twi, Akan,
Pidgin and Ga outright while accepting Swahili, and it heard a blood pressure of
116 as 160 — the difference between a stable patient and an emergency. That is
not an opinion I hold. It is a result I have.

**I hold the line under commercial pressure.** Three providers wanted an adjacent
product that would have been easier to sell. I stayed on chronic care, because a
recall reminder is the one part of this anyone can copy and the cost workflow is
not.

### Short fallback (299 characters)

A good person builds the reminder app. I knew that was the wrong product because
I watched it fail in my own family. Then: I built the whole system alone, I
benchmarked the speech models instead of assuming, and I turned down three
easier adjacent customers to stay on the problem that matters.

---

## Q67 — How did you hear about Axis Sprint?

_Your answer._ Tick the one that is true — LinkedIn / X / Friend / University /
Partner / Event / Newsletter. Nothing rides on it; do not overthink it.

---

## Q68 — Is there anything else you would like us to know?

### Submission answer (~150 words)

Two things.

First, the fastest way to evaluate this application is not to read it. The
product is live. Open the demo, send a voice note in Twi-English, and watch a
patient escalate on the clinician dashboard in real time. It takes ninety seconds
and it will tell you more than anything above.

Second, what I am *not* claiming. No pilot has run. Nobody has paid. I have three
proposals out and a price I have never quoted to anyone. Everything on this form
described as built is built, and everything described as measured is measured — I
have tried hard not to let those two blur into each other, because that blur is
how most of these forms get written.

The distance between a system that works and a company that sells is roughly
twelve weeks of exactly what you teach. That is why I am here.

### Short fallback (290 characters)

Fastest way to evaluate this is not to read it — open the demo, send a Twi-
English voice note, watch a patient escalate live. And what I'm not claiming: no
pilot has run, nobody has paid, my price has never been quoted. Everything I
called built is built; everything measured is measured.

---

## Evidence bank — facts to reuse across any remaining question

All of these are things you have actually done. Nothing below is aspirational.

**Product**
- WhatsApp-based chronic-care agent, live and demo-able: patient replies by text
  or voice note; clinician dashboard updates in real time over WebSockets.
- Reason detection (`cost` / `forgot` / `side_effect` / `ran_out` / `other`) with
  a different downstream action per reason.
- Safety boundary held deliberately: the LLM structures, classifies and
  summarises; **all** red-flag detection (BP ≥160/100) is rule-based. Cost or
  side-effect escalates only after 2+ occurrences in 14 days.
- Degrades gracefully with no API keys and no network — speech falls back to
  local faster-whisper on CPU. The demo cannot hard-fail.

**Research (the part almost nobody else will have)**
- Four-model code-switch speech benchmark: Intron Sahara, Cartesia Ink, OpenAI
  Whisper, local faster-whisper. The benchmark imports the product's own speech
  code, so it measures the models actually serving patients.
- Measured: Cartesia rejects `tw`, `ak`, `pcm` and `gaa` with explicit HTTP 400s;
  the only African language it accepts is Swahili.
- Measured: a blood pressure of "one sixteen over seventy eight" transcribed as
  "160 Nova 78" — 116/78 is green, 160/78 is red, and the error runs in the
  dangerous direction.
- Measured: on Ghanaian-accented English, Intron Sahara is the only model that
  transcribes *amlodipine* correctly. The African-built model has the
  pharmaceutical vocabulary.
- Scores **downstream task success** (escalation correctness, BP extraction,
  intent), not just WER — and found a case where transcription failed badly yet
  the patient was still routed correctly.
- Ethics by construction: written consent per speaker, speaker IDs never names,
  scripted utterances, no real patient data.

**Commercial**
- Veloxa Technology Limited registered.
- Pipeline: Sonrisa Dental Clinic (meeting requested), Impact Medical &
  Diagnostic Centre (proposal requested, after an in-person visit), Rivia Clinics
  (proposal requested), The Bank Hospital and First American (outreach ready).
- Offer: free 60-day pilot, one condition (hypertension), 30 patients, weekly
  report to the clinic, no setup cost.
- Business model: facility subscription / per-active-patient. The clinic,
  pharmacy, insurer or programme pays; the patient does not.
- A structured Growth & Market Expansion Program with weekly targets, a defined
  11-stage pipeline, and Friday reporting.

**Long-term vision (the committee explicitly weighs this)**
- VeloxaCare is an AI-native healthcare operating system for African facilities:
  intake, triage, clinical documentation, appointments, pharmacy and stock,
  billing and NHIS claims, labs, referrals, follow-up and management reporting —
  run by a workforce of specialised agents over one shared, permissioned
  health-and-operations graph.
- **The agent roster, in build order.** Shipped: patient access + care
  coordination. Next: clinical documentation (clinician speech → structured
  note), then triage and routing, then pharmacy and supply (stockout
  prediction), then claims and finance, then the facility manager agent that
  answers "which patients need attention today?" in plain language.
- **One loop for every event:** understand → decide the next step → policy
  decides act-or-approve → execute → track the outcome → learn. That loop, not
  any individual agent, is the system.
- **Not a chatbot bolted onto an HMS.** Existing hospital software is a filing
  cabinet a human operates. This is designed from the start around agents doing
  the work under human supervision — which is why an incumbent cannot retrofit
  it without rewriting their data model.
- **Ghana-first by construction:** offline-first with sync, WhatsApp/SMS/USSD/
  voice rather than smartphone-only, mobile money, NHIS-aware claims, local
  hosting and full auditability.

**Why this wedge earns that platform — the argument that makes the vision credible**
- Care coordination is the only entry point that requires the *whole* graph. To
  route one cost barrier you need the patient's identity, their prescription,
  the pharmacy's stock, what NHIS covers, and a task assigned to a named human
  with an audit trail. Build that honestly and you have already built the spine.
- It is also the cheapest thing to sell: no workflow change, no staff training,
  free 60-day pilot, and the clinic measures the result in retention.
- Every agent after it sells into an account that already trusts us, on a graph
  that already holds its patients.

**Defensibility**
- The care-and-operations data model and the agent workflow engine.
- Ghana-specific clinical and administrative protocols.
- The facility network, and the patient continuity record that moves with a
  patient between CHPS compound, clinic, hospital and pharmacy.
- The outcome data showing which interventions actually changed adherence —
  which nobody else is collecting.
- LHIMS, NHIS, labs, mobile money and Ghana Card connect at the boundary; they
  never define the core data model.
- Deliberately built incrementally so no increment has to be thrown away.

**Business model and expansion**
- Facility subscription and per-active-patient pricing; later, claims
  automation, pharmacy and supply services, premium operational analytics.
- The facility, insurer or programme pays. Patients access essential care
  interactions at no direct cost.
- Path: private clinics and pharmacies → hospital groups → pharmacy chains and
  insurers → NGO and government health programmes → beyond Ghana.

**What the Sprint gives you that you cannot give yourself**
Say this plainly if asked what you want from the program. It reads as
coachability, which is on their selection criteria.
- Pricing a health product sold to facilities, not consumers.
- Getting from free pilot to signed paying contract.
- Ghana health-sector regulatory and data-protection guidance.
- Investment readiness — you have never raised.
- Founder accountability alongside a cohort, given you are not yet full-time.

---

## Tone notes

- Do not call it a reminder bot anywhere, and do not let "WhatsApp" be the noun.
  WhatsApp is the channel the first agent runs on, not the company. The noun is
  *operating system*; the proof is the agent that already works.
- Equally, never let a vision sentence stand without the proof sentence behind
  it. Vision alone is the most common way this form is failed.
- Lead with the mother, once, early. It is the most credible sentence you have.
  Do not repeat it in every answer — twice across the whole form is right.
- Every claim above is measured or done. Do not add a number you cannot show.
- Keep sentences plain. This committee reads dozens of these; clarity reads as
  competence.
