import os
import re
from groq import AsyncGroq

client = None

# Groq models — cheap + fast. Small model for per-message work, larger for reports.
FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")
REPORT_MODEL = os.getenv("GROQ_REPORT_MODEL", "llama-3.3-70b-versatile")


def get_client():
    global client
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            client = AsyncGroq(api_key=api_key)
    return client


def display_first_name(full_name: str) -> str:
    """Use the person's name rather than an honorific as the chat salutation."""
    parts = full_name.strip().split()
    if not parts:
        return "there"
    titles = {"mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr."}
    if parts[0].lower() in titles and len(parts) > 1:
        return parts[1].rstrip(".,")
    return parts[0].rstrip(".,")


async def generate_care_assistant_reply(facts: dict, message: str) -> str:
    """Answer non-urgent category questions using only the patient's care context."""
    c = get_client()
    first = display_first_name(facts["name"])
    if c:
        try:
            resp = await c.chat.completions.create(
                model=FAST_MODEL,
                max_tokens=180,
                temperature=0.35,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a warm WhatsApp care assistant. Answer the patient's question using only the supplied context. "
                            "Do not diagnose, prescribe, or invent an appointment or reminder. "
                            "For urgent symptoms, tell the patient the case is marked urgent for the care team. "
                            "If the system says automatic scheduling is inactive, say that clearly. "
                            "Keep the reply to 2-4 short sentences in simple English."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Patient: {facts['name']}\nCategory: {facts['category']}\nService: {facts['service_type']}\n"
                            f"Approved instructions: {facts['care_instructions'] or 'None recorded'}\n"
                            f"Next follow-up: {facts['next_follow_up'] or 'Not set'}\n"
                            f"Recall date: {facts['recall_date'] or 'Not set'}\n"
                            f"Reminder time: {facts['reminder_time']}\n"
                            "Automatic scheduled WhatsApp messages: inactive in this demo\n\n"
                            f"Patient question: {message}"
                        ),
                    },
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass
    return (
        f"Thanks for your message, {first}. Your care team can help with that question; "
        "I’ve kept it with your follow-up record."
    )


REASON_KEYWORDS = {
    "cost": ["afford", "money", "expensive", "price", "cheap", "cost", "buy", "purchase", "no cash", "broke", "nhis", "funds"],
    "forgot": ["forgot", "forget", "remember", "slipped", "busy", "work", "travel", "away"],
    "side_effect": ["side effect", "side-effect", "dizzy", "dizziness", "nausea", "nauseous", "nauseated",
                    "sick", "headache", "pain", "feel bad", "react", "reaction", "stomach", "vomit",
                    "rash", "swelling", "swollen", "itching", "palpitation", "makes me feel"],
    "ran_out": ["run out", "finished", "out of", "no more", "last one", "empty", "stock", "pharmacy"],
}

BP_PATTERN = re.compile(r'(\d{2,3})\s*/\s*(\d{2,3})')
SUGAR_PATTERN = re.compile(r'(\d+\.?\d*)\s*(mmol|mg|mmo)?', re.IGNORECASE)

# Strong affirmations: count even inside a longer sentence ("yes I took it")
STRONG_YES = {"yes", "done", "taken", "took", "yeah", "yep", "yup", "✅"}
# Weak/ambiguous: only count when the message is essentially just this word
WEAK_YES = {"y", "ok", "okay", "yh", "sure", "already", "1", "yes!"}


def is_affirmative(text: str) -> bool:
    """Whole-word match for a 'yes / taken' reply. Avoids two failure modes:
    the 'y' inside 'dizzy' being read as 'yes', and 'ok' inside a question
    ('is it ok to exercise?') being read as a medication confirmation."""
    t = text.lower().strip().rstrip("!.?")
    if t in STRONG_YES or t in WEAK_YES:
        return True
    if any(p in t for p in ("i did", "took it", "all done", "have taken", "i have taken")):
        return True
    words = set(re.split(r"[^a-z0-9✅]+", t))
    if words & STRONG_YES:
        return True
    # Weak words only when it's a short, non-question reply (not "is it ok ...?")
    if not text.strip().endswith("?") and len(words) <= 3 and (words & WEAK_YES):
        return True
    return False


# ── Emergency / red-flag detection (deterministic — never LLM-only) ────────────

EMERGENCY_PATTERNS = [
    "chest pain", "chest is tight", "chest feels tight", "tight chest", "chest tightness",
    "can't breathe", "cant breathe", "cannot breathe", "can not breathe",
    "difficulty breathing", "trouble breathing", "short of breath", "struggling to breathe",
    "fainted", "fainting", "passed out", "collapse", "collapsed", "unconscious",
    "slurred speech", "face drooping", "one side of my", "numbness", "numb on one",
    "weak on one side", "blurred vision", "can't see", "sudden blindness",
    "severe headache", "bad headache", "worst headache", "pounding headache",
    "convulsion", "seizure", "coughing blood", "vomiting blood", "blood in my",
]


def detect_emergency(message: str) -> bool:
    t = message.lower()
    return any(p in t for p in EMERGENCY_PATTERNS)


# Dental recovery concerns are intentionally deterministic. The assistant can
# collect and route a concern, but it must not diagnose the patient.
DENTAL_URGENT_PATTERNS = [
    "uncontrolled bleeding", "heavy bleeding", "bleeding won't stop", "bleeding wont stop",
    "face swelling", "facial swelling", "swelling is getting worse", "severe swelling",
    "difficulty swallowing", "can't swallow", "cant swallow", "fever", "pus",
    "severe pain", "pain is severe", "worst pain",
]
DENTAL_CONCERN_PATTERNS = [
    "pain", "swelling", "bleeding", "bad taste", "bad smell", "smell from the",
    "still numb", "not healing", "hurts", "sore",
]


def assess_dental_concern(message: str) -> tuple[str | None, str | None]:
    """Return a risk and a safe routing note for a dental recovery message."""
    t = message.lower()
    if any(pattern in t for pattern in DENTAL_URGENT_PATTERNS) or (
        "pain" in t and "swelling" in t
    ):
        return "red", "⚠️ I’ve marked this urgent for your dental care team. Please keep your phone close, and seek urgent care if your breathing or swallowing is affected."
    if any(pattern in t for pattern in DENTAL_CONCERN_PATTERNS):
        return "amber", "Thanks for telling us. I’ve flagged this for your dental care team so they can review your recovery and contact you."
    return None, None


EYE_CONCERN_PATTERNS = [
    "eye pain", "blurred vision", "can't see", "cant see", "red eye", "eye is red",
    "swollen eye", "eye swelling", "discharge", "flashes", "floaters", "light hurts",
]


def assess_eye_concern(message: str) -> tuple[str | None, str | None]:
    t = message.lower()
    if any(pattern in t for pattern in ("sudden blindness", "blurred vision", "can't see", "cant see", "severe eye pain")):
        return "red", "⚠️ I’ve marked this urgent for the eye-care team. Please seek urgent care if your vision is suddenly affected."
    if any(pattern in t for pattern in EYE_CONCERN_PATTERNS):
        return "amber", "Thanks for telling us. I’ve flagged this for the eye-care team so they can review your recovery and contact you."
    return None, None


def detect_reason_rule(text: str) -> str:
    text_lower = text.lower()
    for reason, keywords in REASON_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return reason
    return "other"


def _valid_bp(s: int, d: int):
    # Physiologically plausible and systolic must exceed diastolic
    if 70 <= s <= 300 and 40 <= d <= 200 and s > d:
        return s, d
    return None, None


def parse_bp(text: str):
    """Parse a blood pressure reading from many natural phrasings:
    '135/86', '135 / 86', '135 over 86', or
    'Systolic Pressure: 135 mmHg Diastolic Pressure: 86 mmHg' (ignores pulse)."""
    t = text.lower()

    # 1. Explicitly labelled systolic / diastolic (most reliable, ignores pulse)
    sys_m = re.search(r'systolic\D{0,15}(\d{2,3})', t)
    dia_m = re.search(r'diastolic\D{0,15}(\d{2,3})', t)
    if sys_m and dia_m:
        v = _valid_bp(int(sys_m.group(1)), int(dia_m.group(1)))
        if v[0]:
            return v

    # 2. Slash format: 135/86
    m = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})', t)
    if m:
        v = _valid_bp(int(m.group(1)), int(m.group(2)))
        if v[0]:
            return v

    # 3. "135 over 86"
    m = re.search(r'(\d{2,3})\s*over\s*(\d{2,3})', t)
    if m:
        v = _valid_bp(int(m.group(1)), int(m.group(2)))
        if v[0]:
            return v

    return None, None


# Phrases that mean "I want to report a reading" but contain no numbers yet
BP_INTENT_KEYWORDS = [
    "blood pressure", "my pressure", "checked my pressure", "check my pressure",
    "bp reading", "my bp", "pressure reading", "send the result", "send my result",
    "send the reading", "my reading", "took my pressure", "measured my",
]


def wants_to_report_bp(message: str) -> bool:
    t = message.lower()
    has_number = any(ch.isdigit() for ch in message)
    return (not has_number) and any(k in t for k in BP_INTENT_KEYWORDS)


def assess_bp_risk(systolic: int, diastolic: int) -> tuple[str, str]:
    if systolic >= 160 or diastolic >= 100:
        return "red", f"⚠️ {systolic}/{diastolic} is dangerously high. Please rest and go to the clinic today if you have a headache or chest tightness. I’ve marked this urgent for your care team."
    elif systolic >= 140 or diastolic >= 90:
        return "amber", f"⚠️ {systolic}/{diastolic} is above your target (below 140/90). I've noted this for your doctor. Try to reduce salt and stay consistent with your medication."
    else:
        return "green", f"✅ {systolic}/{diastolic} is in your target range. Excellent — your medication is working!"


async def detect_reason_ai(patient_name: str, message: str) -> str:
    c = get_client()
    if not c:
        return detect_reason_rule(message)
    try:
        resp = await c.chat.completions.create(
            model=FAST_MODEL,
            max_tokens=20,
            temperature=0,
            messages=[{
                "role": "user",
                "content": (
                    f"A patient named {patient_name} said: \"{message}\"\n"
                    "They were asked why they didn't take their medication. "
                    "Reply with exactly ONE word from: cost, forgot, side_effect, ran_out, other"
                )
            }]
        )
        reason = resp.choices[0].message.content.strip().lower().split()[0].strip(".,!")
        if reason in ("cost", "forgot", "side_effect", "ran_out", "other"):
            return reason
        return detect_reason_rule(message)
    except Exception:
        return detect_reason_rule(message)


BOT_RESPONSES = {
    "yes": [
        "✅ Logged! Great job staying on track, {name}.",
        "✅ Excellent consistency, {name}! Your doctor will see your progress.",
        "✅ Done! You're building a strong habit, {name}. Keep it up 💪",
        "✅ Logged! That's {streak} days in a row — outstanding, {name}!",
    ],
    "cost": (
        "I understand, {name}. 🏥 I've marked this for your care team to review an "
        "NHIS-covered alternative. Please keep your phone close."
    ),
    "forgot": (
        "No worries! Take it now if it's been less than 6 hours, {name}. "
        "Try leaving your medication next to your morning tea so it becomes automatic. See you tomorrow! 😊"
    ),
    "side_effect": (
        "That's important to tell us, {name}. I've marked this for your nurse to review. "
        "Please don't stop your medication without speaking to your doctor first. 🏥"
    ),
    "ran_out": (
        "I've flagged this to your clinic, {name}. 🏥 They can help you get a refill. "
        "In the meantime, try not to go more than 2 days without it."
    ),
    "other": (
        "Thank you for letting me know, {name}. I've flagged this for your care team. "
        "Please try to take your medication as soon as possible."
    ),
}


async def generate_bot_reply(patient_name: str, flow: str, message: str, reason: str = None, streak: int = 0) -> str:
    c = get_client()
    first_name = display_first_name(patient_name)

    if flow == "awaiting_medication_ack":
        if is_affirmative(message):
            templates = BOT_RESPONSES["yes"]
            import random
            t = random.choice(templates)
            return t.format(name=first_name, streak=streak)
        elif reason and reason in BOT_RESPONSES:
            return BOT_RESPONSES[reason].format(name=first_name)
        else:
            if c:
                try:
                    resp = await c.chat.completions.create(
                        model=FAST_MODEL,
                        max_tokens=120,
                        temperature=0.6,
                        messages=[
                            {"role": "system", "content": (
                                "You are VeloxaCare, a warm, empathetic health assistant in Ghana. "
                                "You help chronic disease patients stay on their medication. "
                                "Keep replies under 2 sentences. Use simple, clear English. "
                                "End with a supportive nudge. Never give medical diagnoses."
                            )},
                            {"role": "user", "content": f"Patient {first_name} said: \"{message}\". They missed their medication. Respond warmly."}
                        ]
                    )
                    return resp.choices[0].message.content.strip()
                except Exception:
                    pass
            return BOT_RESPONSES["other"].format(name=first_name)

    return f"Thank you, {first_name}. Your care team has been updated."


# ── Intent classification ─────────────────────────────────────────────────────

MISS_INDICATORS = [
    "didn't take", "did not take", "haven't taken", "have not taken", "not taken",
    "missed", "skip", "skipped", "stopped", "couldn't take", "can't take",
    "cannot take", "didn't drink", "no i didn't", "not yet",
]
APPOINTMENT_KEYWORDS = [
    "appointment", "book", "visit", "see the doctor", "see doctor", "come to",
    "reschedule", "schedule", "clinic visit", "check up", "checkup", "review",
]


def classify_intent_rule(message: str) -> str:
    """Rule-based intent fallback. Returns: missed | appointment | question | other"""
    t = message.lower()
    if any(k in t for k in APPOINTMENT_KEYWORDS):
        return "appointment"
    if any(k in t for k in MISS_INDICATORS):
        return "missed"
    if any(k for k in REASON_KEYWORDS["cost"] if k in t) or \
       any(k for k in REASON_KEYWORDS["side_effect"] if k in t) or \
       any(k for k in REASON_KEYWORDS["ran_out"] if k in t):
        return "missed"
    if t.strip().endswith("?") or t.startswith(("what", "when", "how", "why", "can i", "where", "should i")):
        return "question"
    return "other"


async def classify_intent(patient_name: str, message: str) -> str:
    """Classify a free-text patient message into an actionable intent.
    Returns one of: missed | appointment | question | other"""
    c = get_client()
    rule = classify_intent_rule(message)
    if not c:
        return rule
    try:
        resp = await c.chat.completions.create(
            model=FAST_MODEL,
            max_tokens=10,
            temperature=0,
            messages=[{
                "role": "user",
                "content": (
                    f"A chronic-care patient sent this WhatsApp message: \"{message}\"\n"
                    "Classify the intent as exactly ONE word:\n"
                    "- missed (they did NOT take their medication / explaining why they can't)\n"
                    "- appointment (asking to book, reschedule, or visit the clinic/doctor)\n"
                    "- question (asking a general health or service question)\n"
                    "- other (greeting, thanks, small talk, anything else)\n"
                    "Reply with only the one word."
                )
            }]
        )
        intent = resp.choices[0].message.content.strip().lower().split()[0].strip(".,!")
        if intent in ("missed", "appointment", "question", "other"):
            return intent
        return rule
    except Exception:
        return rule


ASSISTANT_SYSTEM = (
    "You are VeloxaCare, a warm, knowledgeable WhatsApp health assistant for a clinic in Accra, Ghana. "
    "You help chronic-disease patients between visits. You are talking to one patient.\n\n"
    "PATIENT CONTEXT:\n"
    "- Name: {name}\n"
    "- Condition: {condition}\n"
    "- Medication: {drug_name} ({drug_dosage})\n"
    "- Medication adherence (last 14 days): {adherence_pct}%\n"
    "- Current daily streak: {streak} days\n"
    "- Last blood pressure reading: {last_bp}\n\n"
    "YOU CAN AND SHOULD:\n"
    "- Answer general health questions about their condition in simple terms.\n"
    "- Explain what their medication is for and common, well-known side effects.\n"
    "- Give practical lifestyle, diet, exercise and salt-reduction guidance suitable for Ghana.\n"
    "- Explain why taking medication consistently matters; encourage them warmly using their data.\n"
    "- Appointment booking is handled by the clinic scheduling workflow before messages reach you.\n"
    "- Answer questions about how this service works.\n\n"
    "YOU MUST NOT:\n"
    "- Diagnose new conditions, or change/suggest changing their prescription or dosage.\n"
    "- Interpret or judge blood pressure / vital sign numbers yourself (e.g. saying a reading is "
    "'high' or 'fine'). If they share a reading, ask them to send it as numbers like 135/86 so the "
    "system can assess it properly.\n"
    "- Claim the patient has done something they only said they INTEND to do. If they say they 'will' "
    "take their medication, encourage the intention — do not congratulate them as if it's already done.\n"
    "- Give emergency medical instructions. If symptoms sound urgent (chest pain, severe headache, "
    "trouble breathing, fainting), tell them to go to the nearest clinic or hospital immediately.\n"
    "- Invent specifics about their record you don't have.\n\n"
    "STYLE: Friendly, respectful, simple clear English for WhatsApp. Keep it to 2-4 short sentences. "
    "Use their first name naturally. You may use the occasional emoji."
)


async def generate_assistant_reply(facts: dict, history: list[dict], message: str) -> str:
    """Full context-aware conversational reply. `facts` = patient data,
    `history` = recent turns (oldest→newest, last turn is the current message)."""
    first = display_first_name(facts["name"])
    c = get_client()

    if c:
        try:
            system = ASSISTANT_SYSTEM.format(
                name=facts["name"],
                condition=facts["condition"],
                drug_name=facts["drug_name"],
                drug_dosage=facts["drug_dosage"],
                adherence_pct=facts["adherence_pct"],
                streak=facts["streak"],
                last_bp=facts.get("last_bp") or "none recorded yet",
            )
            messages = [{"role": "system", "content": system}]
            # Use prior turns for context; the current message is the last history entry
            prior = history[:-1] if history else []
            for h in prior[-8:]:
                role = "assistant" if h["direction"] == "outbound" else "user"
                messages.append({"role": role, "content": h["body"]})
            messages.append({"role": "user", "content": message})

            resp = await c.chat.completions.create(
                model=FAST_MODEL,
                max_tokens=220,
                temperature=0.6,
                messages=messages,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # Fallback without a key
    return (f"Thanks for your message, {first}! 😊 I can help with questions about your "
            f"{facts['condition']}, your {facts['drug_name']}, or booking an appointment. "
            f"Reply YES when you've taken your medication, or share a blood pressure reading anytime.")


async def generate_weekly_report(patients_data: list[dict]) -> str:
    c = get_client()

    summary = "\n".join([
        f"- {p['name']}: {p.get('care_completion_pct', p['adherence_pct'])}% care completion, risk={p['risk_level']}, "
        f"category={p.get('category', 'chronic')}, service={p.get('service_type') or p['condition']}, "
        f"medication={p['drug_name'] or 'not applicable'}, "
        f"flags={p.get('flags', 'none')}"
        for p in patients_data
    ])

    if c:
        try:
            resp = await c.chat.completions.create(
                model=REPORT_MODEL,
                max_tokens=1200,
                temperature=0.4,
                messages=[
                    {"role": "system", "content": (
                        "You are generating a professional weekly patient report for a private clinic in Accra, Ghana. "
                        "Format it clearly for a doctor to read before consultations. "
                        "Be concise, clinical but warm. Highlight urgent cases first. "
                        "Use markdown formatting."
                    )},
                    {"role": "user", "content": (
                        f"Generate a weekly VeloxaCare patient monitoring report for the week ending today.\n\n"
                        f"Patient data:\n{summary}\n\n"
                        "Include: executive summary, patient-by-patient breakdown, "
                        "urgent flags, and recommended actions for the doctor."
                    )}
                ]
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # Fallback if no API key
    total = len(patients_data)
    red = sum(1 for p in patients_data if p["risk_level"] == "red")
    amber = sum(1 for p in patients_data if p["risk_level"] == "amber")
    avg_adh = sum(p.get("care_completion_pct", p["adherence_pct"]) for p in patients_data) // max(total, 1)

    lines = [
        "## VeloxaCare Weekly Report",
        f"**Week ending:** {__import__('datetime').date.today().strftime('%d %B %Y')}",
        f"**Clinic:** Accra Family Clinic\n",
        "### Executive Summary",
        f"- **{total}** patients monitored",
        f"- **Average care completion:** {avg_adh}%",
        f"- **🔴 Red (urgent):** {red} patient(s)",
        f"- **🟡 Amber (watch):** {amber} patient(s)\n",
        "### Patient Breakdown",
    ]
    for p in sorted(patients_data, key=lambda x: {"red": 0, "amber": 1, "green": 2}[x["risk_level"]]):
        icon = {"red": "🔴", "amber": "🟡", "green": "🟢"}[p["risk_level"]]
        service = p.get("service_type") or p.get("condition", "Care follow-up")
        lines.append(f"{icon} **{p['name']}** — {p.get('care_completion_pct', p['adherence_pct'])}% care completion | {p.get('category', 'chronic')} · {service} | {p.get('flags', 'No flags')}")

    return "\n".join(lines)
