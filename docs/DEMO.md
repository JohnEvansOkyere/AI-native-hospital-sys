# VeloxaCare — Demo Guide

How to run the demo and walk a clinic (or pharmacy) through it so they can't say no.

---

## 0. Before the meeting

```bash
cd /home/grejoy/Projects/Clinic-Bot
cp .env.example .env        # paste ANTHROPIC_API_KEY for the live AI report
./start.sh                  # wait for "VeloxaCare is running!"
```

Open **http://localhost:5173** in full-screen.

**Reset to a clean slate** (do this right before each demo so the story is fresh):
```bash
rm backend/veloxacare.db        # then restart ./start.sh — it re-seeds automatically
```

**Pre-flight checklist**
- [ ] Dashboard loads with 6 patients and red alerts already showing.
- [ ] Click "Weekly Report" once to warm it up (confirms your API key works).
- [ ] Browser zoomed so the 3 columns (patients · detail · WhatsApp) all show.
- [ ] If no internet at the venue: the system still works — only the *AI* report and
      *AI* reason-detection fall back to rules. Everything else is local. Demo safely.

---

## 1. The 90-second story (what the screen already shows)

Before touching anything, let the dashboard speak. It is pre-loaded to look like a
clinic that's been running VeloxaCare for two weeks:

- **6 patients**, auto-sorted by urgency.
- Top bar: **on-track / watch / urgent** counts + **average adherence**.
- **Active Alerts** panel already showing real escalations.

> *"This is what your clinic looks like two weeks after we switch it on. Every patient
> who left your consulting room is still being followed — automatically, on WhatsApp,
> with no extra work from your nurses. The system has already flagged the 4 patients
> you need to worry about."*

---

## 2. The live walk-through (3–4 minutes)

### Beat 1 — "We catch the ones who slip" (Kofi Mensah, red, 8%)
- Click **Kofi Mensah**.
- Point to the **adherence heatmap** — mostly red 💸. Point to the **cost-barrier
  escalation** already raised.
- In the WhatsApp pane, click the **"Cost 💸"** quick-reply → send.
- The bot instantly replies, flags the nurse, and mentions an **NHIS-covered
  alternative**. The message gets a `cost` tag.

> *"A normal reminder bot just knows he said no. Ours knows WHY — he can't afford it.
> That's the #1 reason patients in Ghana stop their meds. Instead of losing him, we
> route him to a cheaper covered drug. The clinic keeps the patient. The pharmacy keeps
> the sale."*

### Beat 2 — "Your nurse sees danger in real time" (Kwame Asante, red)
- Click **Kwame Asante**.
- In the WhatsApp pane, click **"High BP 🔴"** → send `168/102` (or `170/105`).
- Watch a **new red alert appear live** in the Active Alerts panel — no refresh.

> *"That reading just crossed a danger threshold. Your nurse is alerted this second —
> not at his next appointment in three weeks. This is how you prevent a stroke instead
> of treating one."*

### Beat 3 — "The reward" (Abena Owusu, green, 92%)
- Click **Abena Owusu** — green heatmap, long streak, healthy BP.
- Click **"YES ✅"** → bot gives warm, streak-aware encouragement.

> *"This is a well-managed patient — and she stays that way because someone checks in
> every single morning. That 'someone' costs you nothing."*

### Beat 4 — "What the doctor actually wants" (the report)
- Click **Weekly Report** in the top bar.
- Claude generates a doctor-ready summary: urgent cases first, per-patient breakdown,
  recommended actions. Click **Print / Save PDF**.

> *"This lands on the doctor's desk the night before clinic. Every patient, summarized,
> ranked by risk. Your doctor walks into each consultation already knowing the story.
> This is the thing you're really buying."*

### Beat 5 — "Onboarding is 30 seconds" (enroll live)
- Click **Enroll Patient**, fill it in with *their* name and number, submit.
- A welcome WhatsApp message appears instantly in the thread.

> *"That's the entire workload for your staff — 30 seconds after a consultation. From
> then on, we do the rest."*

---

## 3. Quick-reply cheat sheet (in the WhatsApp pane)

| Button | Sends | Shows off |
|---|---|---|
| YES ✅ | "Yes done!" | Adherence logged + streak reinforcement |
| Cost 💸 | "I can't afford it this week" | Reason detection → cost → NHIS escalation |
| High BP 🔴 | `168/102` | Rule-based danger detection → live red alert |
| Good BP ✅ | `128/82` | Healthy reading → positive feedback |

You can also free-type anything as the patient — try *"I forgot, I was at work"* or
*"the medicine makes me dizzy"* to show the AI classifying `forgot` vs `side_effect`.

---

## 4. The numbers to quote (research-backed)

- Chronic-med adherence sits at **50–60%**; **a quarter of new prescriptions are never
  filled.**
- In a Ghanaian primary-care study, non-compliance was **55.5%**, and **96% blamed
  cost** — not forgetting. *(This is why reason-detection matters.)*
- A WhatsApp adherence trial in diabetes/hypertension patients: **67.5% adherent vs
  58.5%** control after 4 months.
- Daily messaging in care raised odds of staying in care by **~20%**.

---

## 5. The close — three audiences, three pitches

**To the clinic (retention / quality):**
> "Your patients stay on treatment, your doctors walk in prepared, and your nurses do
> 30 seconds of work instead of follow-up calls they never have time for."

**To a pharmacy (the real payer):**
> "A chronic patient is worth ~12 refills a year. Half drop off after two or three.
> We keep them refilling — and when one can't afford it, we switch them to your
> generic instead of losing the sale. You pay us per active patient; we make you more
> than we cost."

**To an NGO / donor (reach):**
> "Measurable retention and adherence improvement for underserved chronic patients,
> on the phone they already own, with no app to install."

---

## 6. The offer that makes it impossible to refuse

> **Free 60-day pilot. One condition (hypertension). We do the work — you get the
> weekly report.** No setup cost, no dashboard to learn. At day 60 we show retention
> vs. your normal drop-off. If it didn't help, you owe nothing.

That pilot produces the case study that sells every clinic and pharmacy after it.

---

## 7. If something goes wrong on stage

- **Report won't generate** → no internet / no API key. Say *"the AI report needs
  connectivity; here's one I generated earlier"* and have a saved PDF ready. Everything
  else keeps working offline.
- **Want a totally fresh board** → `rm backend/veloxacare.db` and restart.
- **Accidentally messy state** → same reset. The seed is date-relative so it always
  looks current.
