# Clinical code-switched Akan ASR — research landscape

**Compiled 8 August 2026.** Everything here is a link you can check, not a
recollection. Where a claim is a dataset card's own wording rather than
something measured, it says so.

Read this before designing the study. Two things landed in the *week* before it
was written that change what the project should be.

---

## 0. The two findings that reset the plan

**1. The training data I said you'd have to collect already exists.**
[KasaSpeech](https://huggingface.co/datasets/Kennethdot/Ghana_English-Twi_Code-switching_Speech)
— **95.58 hours** of human-transcribed **English–Twi code-switched** speech,
54,855 recordings, speaker IDs included, **Apache-2.0** (commercial use fine),
by Kenneth Dotse. Last updated **5 Aug 2026**. Everyday topics, no clinical
content. Split: 83.94h train / 6.80h val / 4.84h test.

Earlier in this project I advised that code-switched Twi data barely existed and
you'd need 20+ hours of your own before a fine-tune was defensible. That advice
is now wrong, and it was wrong within days of being given. You can start
training this month.

**2. Intron built the clinical code-switch benchmark — and left Ghana out.**
[AfriSwitchCare](https://huggingface.co/datasets/intronhealth/AfriSwitchCare)
(published **3 Aug 2026**) is an "African Code-Switched Clinical Conversation
Benchmark": simulated doctor–patient conversations, African language ×
English, 12 clinical conditions. Languages: Amharic, French, Hausa,
Kinyarwanda, Pidgin, Swahili, Igbo, Yoruba.

**No Akan. No Twi. No Ga. No Ewe.** Its sibling
[AfriSwitch](https://huggingface.co/datasets/intronhealth/AfriSwitch) (54.41h,
in-the-wild code-switch, 14 languages) also has no Ghanaian language other than
Pidgin.

So the thing you were going to claim as novel now half-exists — built by the
company whose challenge you entered — and the half that doesn't exist is
exactly Ghana-shaped. That is a *better* position than inventing a category:
the methodology, the framing and the venue are established, and the hole is
specific, defensible and yours to fill.

---

## 1. Speech data for Akan/Twi — what actually exists

| Resource | Size | Domain | Code-switched? | Licence | Notes |
|---|---|---|---|---|---|
| [KasaSpeech](https://huggingface.co/datasets/Kennethdot/Ghana_English-Twi_Code-switching_Speech) | 95.58h, 54,855 clips | everyday topics | **Yes, En–Twi** | Apache-2.0 | Speaker IDs; prompts designed to elicit switching |
| [UGSpeechData](https://doi.org/10.57760/sciencedb.22298) ([paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12301755/)) | Akan: **1,085h audio / 104h transcribed**, 2,151 speakers | image descriptions, 50 categories | Mostly mono; English allowed where no Twi term exists | CC BY | Part of a 5,384h five-language corpus (Akan, Ewe, Dagbani, Dagaare, Ikposo), Univ. of Ghana |
| Financial Inclusion Speech Dataset (Ashesi/Nokwary) | ~107h Akan, <5s clips | financial phrases | No | check | Three dialects: **Asante, Akuapem, Fante** |
| [Lagyamfi/akan_audio](https://huggingface.co/datasets/Lagyamfi/akan_audio) | ~2h test used in lit. | Bible readings | No | check | Single male narrator — narrow |
| Common Voice Akan (v18) | ~1h, 9 speakers | crowdsourced | No | CC0 | Tiny |
| [ghana-nlp-health-UNICEF-asr-twi](https://huggingface.co/datasets/ghananlpcommunity/ghana-nlp-health-UNICEF-asr-twi) | **<1K samples** | **health** | unclear | CC BY-NC 4.0 | Ewe + Dagbani siblings exist. Closest thing to clinical Twi speech — and it's tiny |
| [ghananlpcommunity/*](https://huggingface.co/ghananlpcommunity) | ~50 datasets | TTS, MT, news, youth conversation, navigation | some | mixed | `pristine-twi-english`, `twi-english-paragraph-dataset_news`, `youth-conversations-tw` |
| [intronhealth/afrispeech-200](https://huggingface.co/datasets/intronhealth/afrispeech-200) | 200h, 2,463 speakers, 120 accents | **clinical + general, accented English** | No (English only) | CC BY-NC-SA 4.0 | [TACL 2023](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00627/118796/) — the clinical-English backbone |
| [AfriSwitch](https://huggingface.co/datasets/intronhealth/AfriSwitch) | 54.41h, 14 languages | in-the-wild conversation | Yes | CC BY-NC-SA 4.0 | **Test-only.** No Ghanaian language but Pidgin |
| [AfriSwitchCare](https://huggingface.co/datasets/intronhealth/AfriSwitchCare) | <1K, 8 languages | **clinical dialogue** | Yes | CC BY-NC-SA 4.0 | **Test-only. Ghana absent** |

**Licence trap worth noting early:** KasaSpeech and UGSpeechData are permissive
(Apache-2.0 / CC BY). Everything from Intron and the UNICEF health sets are
**NC — non-commercial**. You can train on NC data for a paper; you cannot ship
the resulting weights inside a product you charge a clinic for. Decide per
dataset which side of that line it sits on, and keep the product model and the
research model separable from day one.

---

## 2. Akan ASR models that already exist

From Mensah et al. (2025), [*Benchmarking Akan ASR Models Across
Domain-Specific Datasets*](https://arxiv.org/pdf/2507.02407) (Univ. of Ghana,
Univ. of Oulu, and **Univ. of Ghana Health Service**) — seven models, Whisper
and Wav2Vec2/XLS-R based, four public on HF:

- [`GiftMark/akan-whisper-model`](https://huggingface.co/GiftMark/akan-whisper-model) — Whisper-small, Bible, ~35% WER
- [`azunre/wav2vec2large-xlsr-akan`](https://huggingface.co/azunre/wav2vec2large-xlsr-akan) — Common Voice
- [`asr-africa/wav2vec2-xls-r-akan-100-hours`](https://huggingface.co/asr-africa/wav2vec2-xls-r-akan-100-hours) — 100h, ~30% WER
- [`asr-africa/wav2vec2-xls-r-asheshi-akan-10-hours`](https://huggingface.co/asr-africa/wav2vec2-xls-r-asheshi-akan-10-hours) — financial, **~7–10% in-domain WER**
- Also [`abiawilliamsa/Wav2Vec-XLS-5-AKAN-ASR`](https://huggingface.co/abiawilliamsa/Wav2Vec-XLS-5-AKAN-ASR) (1.7k downloads)


**A data-scaling ladder is already published**: `asr-africa` has Akan models at
[1h](https://huggingface.co/asr-africa/akan-1-hours-asheshi-wav2vec2-xlr-s),
[5h](https://huggingface.co/asr-africa/akan-5-hours-asheshi-wav2vec2-xlr-s),
[10h](https://huggingface.co/asr-africa/akan-10-hours-asheshi-wav2vec2-xlr-s)
and [20h](https://huggingface.co/asr-africa/akan-20-hours-asheshi-wav2vec2-xlr-s).
Anyone asking "how many hours do you need?" has a reference curve — and you can
extend it into the clinical domain, which nobody has.

### The two findings from that paper you should build on

**(a) Domain mismatch in Akan ASR is catastrophic, not gradual.** In-domain WER
~10–30%; the *same models* out-of-domain hit 80–100%, with two Whisper models
exceeding 100% WER on the financial set ("decoder collapse"). The best model on
one corpus was among the worst on another.

This is the scientific justification for your whole project: **you cannot take
an existing Akan model and point it at clinical speech.** It is not a matter of
a few points of WER. And 95h of KasaSpeech, being everyday-topic speech, will
not by itself deliver clinical performance either — which is precisely the
thing to measure.

**(b) Whisper's errors are "fluent but potentially misleading"; Wav2Vec2's are
"more obvious yet less interpretable."** The paper flags this as an
architecture-selection trade-off for low-resource languages.

Nobody has followed that finding into a clinical setting — and that is where it
becomes a **safety** result rather than a readability preference. A fluent wrong
transcript in your system produces a confident wrong BP, which produces a wrong
escalation decision. You already have the machinery to measure exactly that.
This is, in my view, the strongest single paper-shaped idea available to you.

---

## 3. Code-switch ASR methods worth knowing

- **Joint LID + ASR loss**: fine-tune Whisper with an auxiliary language-ID loss;
  reported 14–36 percentage-point error reductions ([paper](https://orbilu.uni.lu/bitstream/10993/61597/1/Joint_Fine_tuning_of_Language_Detection_and_ASR_for_Code_Switching_Speech.pdf)).
- **LoRA + custom tokenizer** for Setswana code-switch — the closest published
  recipe to what you'd do ([writeup](https://kesegomokgosi23.medium.com/empowering-setswana-asr-fine-tuning-whisper-for-code-switching-659ec93426b1)).
- **Multilingual SSL helps code-switching in low-resource African languages**
  ([arXiv 2311.15077](https://arxiv.org/abs/2311.15077)).
- **South African code-switch ASR** (isiZulu/Setswana/Sesotho/isiXhosa × English)
  is the most mature African code-switch literature — read it for evaluation
  conventions.
- **Edge/compact models**: [WAXAL-NET](https://arxiv.org/html/2606.02375)
  fine-tunes Whisper-Tiny/Small and MMS-300M across 19 African languages
  against Whisper-Large-v3, MMS-1B and Omnilingual-1B baselines. Directly
  relevant to your offline-clinic story.
- Curated reading list: [gentaiscool/code-switching-papers](https://github.com/gentaiscool/code-switching-papers).

Also note [AfriSpeech-MultiBench](https://arxiv.org/html/2511.14255) and
[AfriVox-v2](https://arxiv.org/html/2605.03590) — Intron's verticalized,
multi-domain African ASR benchmark suites. These define the evaluation style
your work should match if you want it read by the same community.

---

## 4. Does the product already exist?

Partly, and it's worth knowing before you pitch it as novel.

- **[Healthy Heart Assistant](https://www.sciencedirect.com/science/article/pii/S2949761225000501)** —
  a WhatsApp GPT-based self-care assistant for hypertensive patients at a
  Nigerian cardiology clinic. Closest published system to VeloxaCare. **Text-based,
  English, no code-switched voice, no cost-barrier routing.**
- **[mHealth RCT, Ghana + Nigeria](https://pmc.ncbi.nlm.nih.gov/articles/PMC10543310/)** —
  225 adults, twice-weekly app messages, adherence as secondary outcome.
- **[mHealth for chronic disease in Ghana](https://jogh.org/2026/jogh-16-04203)** —
  874 adults, diabetes + hypertension, reminders/education/self-monitoring.
- **[StAR SMS trial, South Africa](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3909351/)** —
  the classic SMS adherence RCT.
- Asamoah et al. (cited in Mensah et al.) collected **~148 hours of Twi and Ga
  speech via a WhatsApp Wizard-of-Oz chatbot** for financial services. Direct
  precedent for collecting speech data through the channel you already run —
  and a methodology citation for your own collection.

**What none of them do:** voice-first in a Ghanaian language, code-switch aware,
with reason-coded non-adherence (cost vs forgot vs side-effect) driving
different downstream actions. The reminder-bot space is crowded; the
*why-did-you-stop* space, in voice, in Twi, is not. Your product thesis
survives this review. Your *ASR* thesis needs the repositioning below.

---

## 5. The gap, stated precisely

Everything below is true as of 8 Aug 2026:

1. There is **no clinical-domain Akan/Twi speech dataset** of meaningful size.
   (UNICEF health-Twi is <1K samples.)
2. There is **no code-switched clinical benchmark covering any Ghanaian
   language** — AfriSwitchCare covers 8 languages and excludes all of them.
3. Published Akan ASR **collapses across domains** (80–100% WER), so existing
   models are known-unfit for clinical speech, and this has never been measured
   *in* the clinical domain.
4. No Akan ASR work scores **downstream task success**. All of it reports
   WER/CER. Your benchmark already scores BP extraction, escalation correctness
   and intent — and your own results show WER ranking the most *useful*
   transcript last.
5. The **clinical-safety consequence of Whisper's fluent-but-wrong error mode**
   is flagged in the literature but never followed into a setting where a wrong
   number changes a care decision.

### The research question

> When a low-resource language model meets a safety-critical domain, does
> reducing word error actually reduce *clinical decision* error — and how much
> in-domain code-switched data does it take to close the gap?

That question is answerable with what exists, is not answered by anyone, and
puts your existing harness (escalation correctness as the headline metric) at
the centre rather than bolted on.

### Contributions, in order of defensibility

1. **KasaCare (working name): a clinical English–Twi code-switched evaluation
   set** — the Ghanaian counterpart to AfriSwitchCare, built to the same shape
   (conditions × conversations), de-identified, consented, published.
   *This is the contribution that survives even if every model experiment fails.*
2. **A domain-transfer study**: existing Akan models + KasaSpeech-trained models
   evaluated on clinical speech; measure the collapse Mensah et al. predict, then
   measure how many hours of clinical data close it (mirroring the asr-africa
   1/5/10/20h ladder).
3. **Task-success vs WER divergence**, quantified: where does lower WER *not*
   mean better escalation decisions?
4. **Error-profile safety analysis**: Whisper vs Wav2Vec2/MMS — does fluent-wrong
   produce more dangerous clinical errors than fragmented-wrong? Frame with the
   116/160 minimal pair you already designed.

---

## 6. Honest risks

- **Intron may extend AfriSwitchCare to Ghanaian languages themselves.** They
  added Akan–English to Sahara in the week of 10 Aug 2026 and are shipping fast.
  Mitigation: move now, and treat them as a collaborator rather than a
  competitor — a Ghana extension to their benchmark, credited, is a better
  outcome for you than a race.
- **KasaSpeech is one contributor's dataset, three days old, unproven.**
  Validate it before building on it: listen to samples, check transcript
  quality, check the speaker-ID distribution (71 distinct values reported —
  verify whether that means 71 speakers, which is thin for a 95h corpus).
- **Clinical data collection is the long pole**, and it's the one thing you
  can't shortcut. Simulated doctor–patient dialogue (AfriSwitchCare's own
  method) is the legitimate, fast, low-risk path — no real patient data, ethics
  burden manageable, and it's what the benchmark you're extending did.
- **NC licences** limit what can enter the product (§1).
- **Dialect scope**: Asante vs Akuapem vs Fante. Financial Inclusion covers all
  three; KasaSpeech says it "may not generalize to all Akan dialects." State
  your scope explicitly rather than saying "Akan."

---

## 7. What I'd do next, in order

1. **Validate KasaSpeech by hand** (a day). Listen to 30 clips, read the
   transcripts, count real speakers. If it holds up, it's your training set and
   most of the data problem disappears.
2. **Reproduce Mensah et al.'s cross-domain collapse on your own 57 clips**
   using the public Akan models. Cheap, uses the harness you have, and it's the
   baseline table every later claim rests on. *Do this before any training.*
3. **Design KasaCare** to AfriSwitchCare's shape — conditions × conversations,
   simulated dialogue, consented speakers, de-identified, speaker-disjoint by
   construction. Your `benchmark/recording/` kit is already 80% of the protocol.
4. **Email Intron and the Mensah et al. group.** Intron: "AfriSwitchCare has no
   Ghanaian language; I'm building one and would like it to be compatible."
   Univ. of Ghana: they have a co-author at the **University of Ghana Health
   Service** — that is a clinical-collaborator lead and a possible ethics route.
   Both emails cost an hour and could change the project's trajectory.
5. **Only then** train: Whisper-small + LoRA on KasaSpeech, ±clinical data,
   evaluated on the frozen KasaCare split with both WER and task-success.

**Do not skip step 2.** A baseline table produced before you have a model to
promote is the difference between a benchmark people trust and one they assume
was tuned to flatter your result.

---

## Appendix: canonical links

Datasets: [KasaSpeech](https://huggingface.co/datasets/Kennethdot/Ghana_English-Twi_Code-switching_Speech) ·
[UGSpeechData](https://doi.org/10.57760/sciencedb.22298) ·
[AfriSwitchCare](https://huggingface.co/datasets/intronhealth/AfriSwitchCare) ·
[AfriSwitch](https://huggingface.co/datasets/intronhealth/AfriSwitch) ·
[AfriSpeech-200](https://huggingface.co/datasets/intronhealth/afrispeech-200) ·
[ghananlpcommunity](https://huggingface.co/ghananlpcommunity)

Papers: [Benchmarking Akan ASR](https://arxiv.org/pdf/2507.02407) ·
[UGSpeechData](https://pmc.ncbi.nlm.nih.gov/articles/PMC12301755/) ·
[AfriSpeech-200 (TACL)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00627/118796/) ·
[AfriSpeech-Dialog](https://arxiv.org/html/2502.03945v1) ·
[AfriSpeech-MultiBench](https://arxiv.org/html/2511.14255) ·
[WAXAL-NET](https://arxiv.org/html/2606.02375) ·
[SSL for CS African ASR](https://arxiv.org/abs/2311.15077)
