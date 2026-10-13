import json
from datetime import date, datetime, timedelta
from typing import Optional
from db import Connection
from services.appointments import booking_reprompt, handle_appointment_turn, is_side_question

from services.ai import (
    detect_reason_ai, detect_reason_rule, barrier_override, generate_bot_reply,
    parse_bp, assess_bp_risk, bp_band, BP_BAND_REASON, ELEVATED_ESCALATE_AT, is_affirmative,
    classify_intent, classify_intent_rule, generate_assistant_reply, detect_emergency, MISS_INDICATORS,
    wants_to_report_bp, assess_dental_concern, assess_eye_concern, assess_general_concern,
    display_first_name,
    generate_care_assistant_reply,
)


NO_WORDS = {"no", "n", "0", "nope", "nah", "no i haven't", "no i didn't"}


def is_yes(text: str) -> bool:
    return is_affirmative(text)


GREETINGS = ("start", "begin", "hi", "hello")


async def _is_first_contact(patient_id: int, db: Connection) -> bool:
    """True when the message being handled is the patient's first. The inbound
    row is logged before process_message runs, so first contact means one row.
    Only then does a greeting get the enrolment welcome; afterwards "hi" is
    just hello, not a re-enrolment."""
    cursor = await db.execute(
        "SELECT COUNT(*) FROM messages WHERE patient_id=? AND direction='inbound'", (patient_id,)
    )
    row = await cursor.fetchone()
    return (row[0] if row else 0) <= 1


def _is_reminder_question(text: str) -> bool:
    return "reminder" in text and any(word in text for word in ("when", "next", "coming", "time", "due"))


def _format_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%A, %d %B %Y")
    except (TypeError, ValueError):
        return value or "not set"


def _format_time(value: str) -> str:
    try:
        return datetime.strptime(value, "%H:%M").strftime("%-I:%M %p")
    except (TypeError, ValueError):
        return value or "not set"


async def _build_context(patient_id: int, db: Connection,
                         name: str, condition: str, drug_name: str,
                         drug_dosage: str, streak: int,
                         reminder_time: str = "08:00") -> tuple[dict, list[dict]]:
    """Gather the patient's real data + recent chat so the assistant can answer
    in context (their meds, adherence, last reading, conversation so far)."""
    # Adherence over last 14 days
    cursor = await db.execute(
        "SELECT response FROM adherence_logs WHERE patient_id=? AND log_date>?",
        (patient_id, (date.today() - timedelta(days=14)).isoformat())
    )
    rows = await cursor.fetchall()
    adherence_pct = round(sum(1 for r in rows if r[0] == "yes") / len(rows) * 100) if rows else 0

    # Last BP reading
    cursor = await db.execute(
        "SELECT reading_value, created_at FROM checkin_logs WHERE patient_id=? ORDER BY created_at DESC LIMIT 1",
        (patient_id,)
    )
    bp_row = await cursor.fetchone()
    last_bp = bp_row[0] if bp_row else None

    # Staff-entered care plan plus patient-reported context. The latter is
    # intentionally labelled as unverified in the AI instructions.
    cursor = await db.execute(
        "SELECT care_instructions, patient_context FROM patients WHERE id=?",
        (patient_id,),
    )
    profile = await cursor.fetchone()

    facts = {
        "name": name, "condition": condition, "drug_name": drug_name,
        "drug_dosage": drug_dosage, "adherence_pct": adherence_pct,
        "streak": streak, "last_bp": last_bp,
        "reminder_time": _format_time(reminder_time or "08:00"),
        "care_plan": profile[0] or "" if profile else "",
        "patient_context": profile[1] or "" if profile else "",
    }

    # Recent conversation (oldest→newest), includes the just-logged inbound as last turn
    cursor = await db.execute(
        "SELECT direction, body FROM messages WHERE patient_id=? ORDER BY created_at DESC LIMIT 10",
        (patient_id,)
    )
    msgs = await cursor.fetchall()
    history = [{"direction": m[0], "body": m[1]} for m in reversed(msgs)]

    return facts, history


# Reasons that represent a barrier to treatment and must be escalated to the care team.
# Repeated treatment barriers escalate on the 2nd occurrence in 14 days. Acute
# emergency symptoms still bypass this counter and create an immediate red case.
ESCALATE_AT = {"cost": 2, "ran_out": 2, "side_effect": 2}

ESC_REASON_TEXT = {
    "cost": "Cost barrier — patient unable to afford medication ({count}x in 14 days)",
    "ran_out": "Out of medication — patient has run out ({count}x in 14 days)",
    "side_effect": "Side effect reported — patient flagged an adverse reaction ({count}x in 14 days)",
}


RISK_ORDER = {"green": 0, "amber": 1, "red": 2}


async def _refresh_risk(patient_id: int, db: Connection) -> str:
    """Patient risk = the worst open case, as when staff resolve one (main.py).
    A later calm reading or a good streak must never clear a red patient while
    their case is still open."""
    cursor = await db.execute(
        "SELECT risk_level FROM escalations WHERE patient_id=? AND resolved=0", (patient_id,)
    )
    levels = [r[0] for r in await cursor.fetchall()]
    risk = max(levels, key=lambda r: RISK_ORDER.get(r, 0), default="green")
    await db.execute("UPDATE patients SET risk_level=? WHERE id=?", (risk, patient_id))
    return risk


async def _elevated_count(patient_id: int, db: Connection) -> int:
    """Earlier readings at elevated or worse in the last 14 days."""
    cursor = await db.execute(
        "SELECT reading_value FROM checkin_logs WHERE patient_id=? AND reading_type='bp' AND created_at>?",
        (patient_id, (date.today() - timedelta(days=14)).isoformat())
    )
    count = 0
    for (value,) in await cursor.fetchall():
        systolic, diastolic = parse_bp(value or "")
        if systolic is not None and bp_band(systolic, diastolic) in ("elevated", "high", "crisis"):
            count += 1
    return count


async def _record_bp_reading(patient_id: int, systolic: int, diastolic: int,
                             message: str, db: Connection, now: str) -> tuple[str, bool]:
    """Log a BP reading and open a case for anything outside the target range.

    One path for the check-in flow and free text, so a reading gets the same
    treatment however the patient sends it. Returns (reply, escalation_created).
    """
    band = bp_band(systolic, diastolic)
    reading = f"{systolic}/{diastolic}"
    count = await _elevated_count(patient_id, db) + 1 if band == "elevated" else 0
    repeated = count >= ELEVATED_ESCALATE_AT
    risk_level, note = assess_bp_risk(systolic, diastolic, repeated=repeated)
    await db.execute(
        "INSERT INTO checkin_logs (patient_id, reading_type, reading_value, risk_level, ai_note, created_at) VALUES (?,?,?,?,?,?)",
        (patient_id, "bp", reading, risk_level, note, now)
    )

    escalate = band in ("crisis", "high", "low") or (band == "elevated" and repeated)
    if band == "elevated" and repeated:
        # One open case per run of high readings, not one per reading.
        cursor = await db.execute(
            "SELECT COUNT(*) FROM escalations WHERE patient_id=? AND resolved=0 AND details LIKE ?",
            (patient_id, '%"band": "elevated"%')
        )
        escalate = (await cursor.fetchone())[0] == 0
    if escalate:
        details = json.dumps({"reading": reading, "band": band, "target": "below 140/90",
                              "elevated_readings_last_14_days": count, "message": message})
        await db.execute(
            "INSERT INTO escalations (patient_id, reason, risk_level, details, created_at) VALUES (?,?,?,?,?)",
            (patient_id, BP_BAND_REASON[band].format(reading=reading, count=count), risk_level, details, now)
        )
    await _refresh_risk(patient_id, db)
    return note, escalate


async def _start_booking(patient_id: int, name: str, doctor_name: str, service_type: str,
                         condition: str, message: str, db: Connection):
    """The classifier heard a booking request the keywords missed. Start the
    real flow — free-text chat can only promise an appointment, not make one."""
    turn = await handle_appointment_turn(
        db=db, patient_id=patient_id, patient_name=name,
        clinician_name=doctor_name or "Dr. Mensah",
        visit_type=service_type or f"{condition.title()} review",
        current_flow="idle", context={}, message=message, force_intent="book",
    )
    if not turn:
        return None
    bot_reply, new_flow, new_context = turn
    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, new_flow, json.dumps(new_context)),
    )
    await db.commit()
    return bot_reply, None, False


async def _barrier_days(patient_id: int, reason: str, db: Connection) -> int:
    """Days in the last 14 on which the patient reported this barrier. Days,
    not messages: saying "my legs are swelling" twice in one chat is one
    report, and must not turn a patient red on its own."""
    since = (date.today() - timedelta(days=14)).isoformat()
    cursor = await db.execute(
        "SELECT DISTINCT log_date FROM adherence_logs WHERE patient_id=? AND response=? AND log_date>?",
        (patient_id, reason, since)
    )
    days = {r[0] for r in await cursor.fetchall()}
    if reason == "side_effect":
        cursor = await db.execute(
            "SELECT DISTINCT log_date FROM care_logs WHERE patient_id=? AND activity='side_effect' AND log_date>?",
            (patient_id, since)
        )
        days |= {r[0] for r in await cursor.fetchall()}
    return len(days)


def _says_dose_missed(message: str) -> bool:
    text = message.lower().replace("’", "'")
    return text.strip(" !.") in NO_WORDS or any(k in text for k in MISS_INDICATORS)


async def _handle_missed_dose(patient_id: int, name: str, message: str,
                              db: Connection, now: str, today: str):
    """Single source of truth for a missed/blocked dose: detect the reason, log it,
    and apply the escalation rules. Used by BOTH the reminder-reply flow and free chat,
    so a cost barrier is flagged no matter how the patient phrases it.

    Returns (reply, reason, escalation_created, dose_missed). A side effect is
    a missed dose only when the patient says so — "my legs are swelling" is a
    symptom to review, and logging it as a miss made adherent patients look
    non-adherent. It is kept as a care note instead.
    """
    # Deterministic rules win for treatment barriers. Escalation is a clinical
    # decision, so the LLM may only fill in where the rules found nothing:
    # "couldn't afford it so I forgot" must count as cost, whatever the model says.
    rule_reason = detect_reason_rule(message)
    if rule_reason in ESCALATE_AT:
        reason = rule_reason
    else:
        reason = await detect_reason_ai(name, message)
        if reason == "other":
            reason = rule_reason or "other"

    dose_missed = reason != "side_effect" or _says_dose_missed(message)
    if dose_missed:
        # One row per reason per day, so a repeated message doesn't count as
        # another missed dose in the adherence figure.
        cursor = await db.execute(
            "SELECT COUNT(*) FROM adherence_logs WHERE patient_id=? AND log_date=? AND response=?",
            (patient_id, today, reason)
        )
        if (await cursor.fetchone())[0] == 0:
            await db.execute(
                "INSERT INTO adherence_logs (patient_id, log_date, response, created_at) VALUES (?,?,?,?)",
                (patient_id, today, reason, now)
            )
    if reason == "side_effect":
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "side_effect", "concern", message, now),
        )
    bot_reply = await generate_bot_reply(name, "awaiting_medication_ack", message, reason=reason)

    escalation_created = False
    if reason in ESCALATE_AT:
        count = await _barrier_days(patient_id, reason, db)
        # The reply tells the patient their care team has been told, so a case
        # must exist — amber on the first day, red once it repeats on another
        # day. One case per reason per day.
        cursor = await db.execute(
            "SELECT id, details FROM escalations WHERE patient_id=? AND resolved=0 AND created_at>=? "
            "AND details LIKE ? ORDER BY id DESC LIMIT 1",
            (patient_id, today, f'%"reason": "{reason}"%')
        )
        open_case = await cursor.fetchone()
        if open_case:
            # Same barrier again today: add it to that case so staff see what
            # changed ("my legs are swelling too", "so I stopped taking them").
            details = json.loads(open_case[1] or "{}")
            details.setdefault("further_messages", []).append(f"{now[11:16]} {message}")
            await db.execute("UPDATE escalations SET details=? WHERE id=?",
                             (json.dumps(details), open_case[0]))
            first = display_first_name(name)
            bot_reply = f"Thank you, {first}. I've added this to today's note for your care team."
            if reason == "side_effect":
                bot_reply += (" Please don't stop your medication without speaking to your doctor first. "
                              "If your face, lips or tongue swell, or you find it hard to breathe, "
                              "go to the nearest hospital now or call 112 or 193. 🏥")
        else:
            level = "red" if count >= ESCALATE_AT[reason] else "amber"
            details = json.dumps({
                "reason": reason, "occurrences_last_14_days": count, "last_message": message,
            })
            await db.execute(
                "INSERT INTO escalations (patient_id, reason, risk_level, details, created_at) VALUES (?,?,?,?,?)",
                (patient_id, ESC_REASON_TEXT[reason].format(count=count), level, details, now)
            )
            await _refresh_risk(patient_id, db)
            escalation_created = True

    return bot_reply, reason, escalation_created, dose_missed


async def _process_dental_message(
    patient_id: int,
    name: str,
    service_type: str,
    care_instructions: str,
    next_follow_up: str,
    recall_date: str,
    reminder_time: str,
    current_flow: str,
    message: str,
    db: Connection,
    now: str,
    today: str,
):
    """Dental aftercare and recall flow.

    This is deliberately separate from medication adherence: a dental patient
    is checking whether they followed aftercare and reporting recovery concerns,
    not confirming a daily prescription.
    """
    first = display_first_name(name)
    text = message.lower().strip()
    escalation_created = False
    reason = None
    new_flow = "idle"

    risk, concern_reply = assess_dental_concern(message)
    affirmative = is_affirmative(message)

    if text in GREETINGS and not await _is_first_contact(patient_id, db):
        bot_reply = f"Hello again, {first}! 👋 How is your recovery going? Ask me anything about your aftercare."
    elif text in GREETINGS:
        bot_reply = (
            f"Welcome, {first}! 👋 I’m your dental care assistant. "
            f"I’ll check on your {service_type or 'dental treatment'} recovery, help with aftercare, "
            "and remind you when it is time to return."
        )
    elif text in ("thanks", "thank you", "thanks a lot", "thank you so much", "got it, thanks") or text.startswith("thank you"):
        bot_reply = (
            f"You’re welcome, {first}! 😊 If anything changes—pain, swelling, bleeding, or trouble eating—"
            "send us a message and we’ll alert your dental team."
        )
        if current_flow in ("awaiting_dental_aftercare", "awaiting_dental_checkin"):
            new_flow = current_flow
    elif affirmative:
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "dental_aftercare", "done", care_instructions, now),
        )
        bot_reply = (
            f"✅ Thank you, {first}. I’ve recorded that you followed your aftercare instructions. "
            "We’ll check on your recovery again soon."
        )
    elif risk:
        reason = "dental_recovery_concern"
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "dental_aftercare", "concern", message, now),
        )
        details = json.dumps({
            "category": "dental",
            "service_type": service_type,
            "message": message,
            "action": "Dental team to review and contact patient.",
        })
        await db.execute(
            "INSERT INTO escalations (patient_id, reason, risk_level, details, created_at) VALUES (?,?,?,?,?)",
            (patient_id, f"Dental recovery concern reported: {message}", risk, details, now),
        )
        await _refresh_risk(patient_id, db)
        bot_reply = concern_reply
        escalation_created = True
    elif any(word in text for word in ("eat", "eating", "food", "drink", "meal", "spicy", "hot", "hard")):
        instruction = care_instructions or "Follow the aftercare instructions given by your dental team."
        if "extraction" in (service_type or "").lower():
            bot_reply = (
                f"For your extraction, {first}, follow the approved advice: {instruction} "
                "Choose soft foods for now and avoid hard or chewy foods until your dental team says it is safe. "
                "If you mean a specific food, tell me its name and the team can confirm."
            )
        else:
            bot_reply = f"For your {service_type or 'dental treatment'}, please follow the approved advice: {instruction} If you mean a specific food, tell me its name so the dental team can confirm."
        if current_flow in ("awaiting_dental_aftercare", "awaiting_dental_checkin"):
            new_flow = current_flow
    elif _is_reminder_question(text):
        next_follow_up_text = _format_date(next_follow_up) if next_follow_up else "not set"
        bot_reply = (
            f"Your care reminder time is set to {_format_time(reminder_time)}. "
            "In this demo, scheduled WhatsApp reminders are not active yet—the clinic triggers the reminder from the dashboard. "
            f"Your next recorded follow-up is {next_follow_up_text}."
        )
    elif any(word in text for word in ("appointment", "book", "schedule", "reschedule", "recall")):
        bot_reply = (
            f"Of course, {first}. I’ve noted that you want help with your dental appointment. "
            "The dental team will confirm the available time with you by message."
        )
    elif current_flow in ("awaiting_dental_aftercare", "awaiting_dental_checkin"):
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "dental_aftercare", "needs_clarification", message, now),
        )
        bot_reply = (
            f"Thanks, {first}. Please tell us if you have pain, swelling, bleeding, fever, or another concern. "
            "I’ll pass anything important to your dental team."
        )
        new_flow = current_flow
    else:
        bot_reply = await generate_care_assistant_reply(
            {
                "name": name,
                "category": "dental",
                "service_type": service_type or "dental care",
                "care_instructions": care_instructions,
                "next_follow_up": next_follow_up,
                "recall_date": recall_date,
                "reminder_time": reminder_time or "08:00",
            },
            message,
        )

    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, new_flow, "{}"),
    )
    await db.commit()
    return bot_reply, reason, escalation_created


async def _process_eye_message(
    patient_id: int,
    name: str,
    service_type: str,
    care_instructions: str,
    current_flow: str,
    message: str,
    db: Connection,
    now: str,
    today: str,
):
    """Small non-medication eye-care flow; detailed eye rules can be added later."""
    first = display_first_name(name)
    text = message.lower().strip()
    risk, concern_reply = assess_eye_concern(message)
    escalation_created = False
    reason = None
    new_flow = "idle"

    if text in GREETINGS and not await _is_first_contact(patient_id, db):
        bot_reply = f"Hello again, {first}! 👋 How is your eye doing? Ask me anything about your aftercare."
    elif text in GREETINGS:
        bot_reply = (
            f"Welcome, {first}! 👋 I’ll check on your {service_type or 'eye-care follow-up'} "
            "and remind you when it is time to return."
        )
    elif text in ("thanks", "thank you", "thanks a lot", "thank you so much", "got it, thanks") or text.startswith("thank you"):
        bot_reply = f"You’re welcome, {first}! 😊 If anything changes with your eyes or vision, send us a message and we’ll alert the eye-care team."
        if current_flow in ("awaiting_eye_aftercare", "awaiting_eye_checkin"):
            new_flow = current_flow
    elif is_affirmative(message):
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "eye_care", "done", care_instructions, now),
        )
        bot_reply = f"✅ Thank you, {first}. I’ve recorded your eye-care check-in. We’ll check on you again soon."
    elif risk:
        reason = "eye_recovery_concern"
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "eye_care", "concern", message, now),
        )
        details = json.dumps({"category": "eye", "service_type": service_type, "message": message})
        await db.execute(
            "INSERT INTO escalations (patient_id, reason, risk_level, details, created_at) VALUES (?,?,?,?,?)",
            (patient_id, f"Eye-care concern reported: {message}", risk, details, now),
        )
        await _refresh_risk(patient_id, db)
        bot_reply = concern_reply
        escalation_created = True
    elif any(word in text for word in ("appointment", "book", "schedule", "reschedule", "recall")):
        bot_reply = f"Of course, {first}. I’ve noted your request and the eye-care team will confirm the available time by message."
    elif current_flow in ("awaiting_eye_aftercare", "awaiting_eye_checkin"):
        bot_reply = f"Thanks, {first}. Please tell us if your vision or eye feels different, or if you have another concern."
        new_flow = current_flow
    else:
        bot_reply = f"Thanks for your message, {first}. I can help with your eye-care follow-up, aftercare questions, and booking a return visit."

    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, new_flow, "{}"),
    )
    await db.commit()
    return bot_reply, reason, escalation_created


async def _process_general_message(
    patient_id: int,
    name: str,
    service_type: str,
    care_instructions: str,
    current_flow: str,
    message: str,
    db: Connection,
    now: str,
    today: str,
):
    """Category-neutral follow-up scaffold for future care programs."""
    first = display_first_name(name)
    text = message.lower().strip()
    new_flow = "idle"
    risk, concern_reply = assess_general_concern(message)
    reason = None
    escalation_created = False

    if text in GREETINGS and not await _is_first_contact(patient_id, db):
        bot_reply = f"Hello again, {first}! 👋 How are you feeling? Ask me anything about your follow-up."
    elif text in GREETINGS:
        bot_reply = f"Welcome, {first}! 👋 I’ll help with your {service_type or 'clinic follow-up'} and remind you about your next step."
    elif text in ("thanks", "thank you", "thanks a lot", "thank you so much", "got it, thanks") or text.startswith("thank you"):
        bot_reply = f"You’re welcome, {first}! 😊 Send us a message any time you need help with your follow-up."
        if current_flow in ("awaiting_general_checkin", "awaiting_general_aftercare"):
            new_flow = current_flow
    elif is_affirmative(message):
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "general_care", "done", care_instructions, now),
        )
        bot_reply = f"✅ Thank you, {first}. I’ve recorded your care check-in. We’ll follow up again soon."
    elif risk:
        reason = "general_care_concern"
        await db.execute(
            "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
            (patient_id, today, "general_care", "concern", message, now),
        )
        details = json.dumps({"category": "general", "service_type": service_type, "message": message})
        await db.execute(
            "INSERT INTO escalations (patient_id, reason, risk_level, details, created_at) VALUES (?,?,?,?,?)",
            (patient_id, f"Follow-up concern reported: {message}", risk, details, now),
        )
        await db.execute(
            "UPDATE patients SET risk_level=? WHERE id=? AND risk_level<>'red'", (risk, patient_id)
        )
        bot_reply = concern_reply
        escalation_created = True
    elif any(word in text for word in ("appointment", "book", "schedule", "reschedule", "recall")):
        bot_reply = f"Of course, {first}. I’ve noted your appointment request and the care team will confirm the available time by message."
    elif current_flow in ("awaiting_general_checkin", "awaiting_general_aftercare"):
        bot_reply = f"Thanks, {first}. Please tell us how you are doing or share any concern for the care team."
        new_flow = current_flow
    else:
        bot_reply = f"Thanks for your message, {first}. I can help with your clinic follow-up, care instructions, and booking a return visit."

    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, new_flow, "{}"),
    )
    await db.commit()
    return bot_reply, reason, escalation_created


async def process_message(patient_id: int, message: str, db: Connection):
    """
    Core bot logic. Returns (bot_reply, reason, escalation_created).
    Also logs the inbound message, bot reply, adherence, checkin, escalation.
    """
    now = datetime.now().isoformat()
    today = date.today().isoformat()

    # Get patient
    cursor = await db.execute(
        """SELECT name, condition, drug_name, drug_dosage, category, service_type,
                  care_instructions, next_follow_up, recall_date, reminder_time, doctor_name
           FROM patients WHERE id=?""",
        (patient_id,),
    )
    patient = await cursor.fetchone()
    if not patient:
        return "Sorry, I couldn't find your profile.", None, False
    (name, condition, drug_name, drug_dosage, category, service_type,
     care_instructions, next_follow_up, recall_date, reminder_time, doctor_name) = patient

    # Get conversation state
    cursor = await db.execute("SELECT current_flow, context FROM conversation_state WHERE patient_id=?", (patient_id,))
    state_row = await cursor.fetchone()
    current_flow = state_row[0] if state_row else "idle"
    context = json.loads(state_row[1]) if state_row else {}

    bot_reply = None
    reason = None
    escalation_created = False
    new_flow = "idle"
    new_context = {}

    # Compute streak for positive reinforcement
    cursor = await db.execute(
        "SELECT response FROM adherence_logs WHERE patient_id=? ORDER BY log_date DESC LIMIT 7",
        (patient_id,)
    )
    recent = await cursor.fetchall()
    streak = 0
    for r in recent:
        if r[0] == "yes":
            streak += 1
        else:
            break

    msg_lower = message.lower().strip()

    # ── EMERGENCY (safety first — runs before any other flow) ──
    if detect_emergency(message):
        first = display_first_name(name)
        bot_reply = (
            f"⚠️ {first}, these symptoms can be serious. Please go to the nearest hospital "
            f"right away, or call 112 or 193 for an ambulance. Ask someone to help you if you can. "
            f"I've marked this urgent for your care team. Please keep your phone close. 🏥"
        )
        # Keep any reading sent with the symptoms ("190/120 and chest pain") —
        # staff need it, and the emergency reply above takes precedence.
        systolic, diastolic = parse_bp(message)
        if systolic is not None:
            risk_level, note = assess_bp_risk(systolic, diastolic)
            await db.execute(
                "INSERT INTO checkin_logs (patient_id, reading_type, reading_value, risk_level, ai_note, created_at) VALUES (?,?,?,?,?,?)",
                (patient_id, "bp", f"{systolic}/{diastolic}", risk_level, note, now)
            )
        reason = None
        if category == "dental":
            _, category_reply = assess_dental_concern(message)
            if category_reply:
                bot_reply = category_reply
                reason = "dental_recovery_concern"
        elif category == "eye":
            _, category_reply = assess_eye_concern(message)
            if category_reply:
                bot_reply = category_reply
                reason = "eye_recovery_concern"
        if reason in ("dental_recovery_concern", "eye_recovery_concern"):
            # The specialty wording names the right team; the emergency
            # instruction and numbers are never dropped for it.
            bot_reply += (" If it is severe or getting worse, go to the nearest hospital now "
                          "or call 112 or 193.")
        details = json.dumps({
            "category": category,
            "symptoms_reported": message,
            "action": "Patient advised to seek emergency care; urgent care-team case created.",
        })
        emergency_reason = (
            f"{category.title()} recovery concern reported: {message}"
            if category in ("dental", "eye") else "🚨 URGENT: possible emergency symptoms reported"
        )
        await db.execute(
            "INSERT INTO escalations (patient_id, reason, risk_level, details, created_at) VALUES (?,?,?,?,?)",
            (patient_id, emergency_reason, "red", details, now)
        )
        await db.execute("UPDATE patients SET risk_level='red' WHERE id=?", (patient_id,))
        if category != "chronic":
            await db.execute(
                "INSERT INTO care_logs (patient_id, log_date, activity, response, details, created_at) VALUES (?,?,?,?,?,?)",
                (patient_id, today, f"{category}_care", "concern", message, now),
            )
        await db.execute(
            """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
               ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
            (patient_id, "idle", "{}")
        )
        await db.commit()
        return bot_reply, reason, True

    # ── APPOINTMENTS (real downstream action) ──
    # Emergency handling stays above this. The assistant structures the request,
    # while deterministic availability rules create the actual database record.
    if category == "chronic" and is_side_question(message, current_flow, context):
        # Answer the question, keep the half-finished booking open.
        facts, history = await _build_context(patient_id, db, name, condition, drug_name,
                                              drug_dosage, streak, reminder_time)
        answer = await generate_assistant_reply(facts, history, message, booking_open=True)
        await db.commit()
        return f"{answer}\n\n{booking_reprompt(current_flow, context)}", None, False

    appointment_turn = await handle_appointment_turn(
        db=db,
        patient_id=patient_id,
        patient_name=name,
        clinician_name=doctor_name or "Dr. Mensah",
        visit_type=service_type or f"{condition.title()} review",
        current_flow=current_flow,
        context=context,
        message=message,
    )
    if appointment_turn:
        bot_reply, new_flow, new_context = appointment_turn
        await db.execute(
            """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
               ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
            (patient_id, new_flow, json.dumps(new_context)),
        )
        await db.commit()
        return bot_reply, None, False

    if category == "dental":
        return await _process_dental_message(
            patient_id, name, service_type, care_instructions, next_follow_up,
            recall_date, reminder_time, current_flow,
            message, db, now, today,
        )
    if category == "eye":
        return await _process_eye_message(
            patient_id, name, service_type, care_instructions, current_flow,
            message, db, now, today,
        )
    if category == "general":
        return await _process_general_message(
            patient_id, name, service_type, care_instructions, current_flow,
            message, db, now, today,
        )

    # ── ENROLLMENT flow ──
    if (msg_lower in GREETINGS and current_flow == "idle"
            and await _is_first_contact(patient_id, db)):
        bot_reply = (
            f"Welcome! ✅ You're now enrolled in VeloxaCare. "
            f"I'll remind you to take your {drug_name} every day at {_format_time(reminder_time or '08:00')} "
            f"and check in on how you're feeling weekly. Reply YES each morning when you've taken it. "
            f"Your health is our priority 💙"
        )
        new_flow = "idle"

    # ── MEDICATION ACK flow ──
    elif current_flow == "awaiting_medication_ack":
        if is_yes(message):
            # Log adherence as yes
            await db.execute(
                "INSERT INTO adherence_logs (patient_id, log_date, response, created_at) VALUES (?,?,?,?)",
                (patient_id, today, "yes", now)
            )
            streak += 1
            bot_reply = await generate_bot_reply(name, "awaiting_medication_ack", message, streak=streak)

            # Update risk toward green if streak building
            # A streak never clears an open case — risk follows the cases.
            if streak >= 7:
                await _refresh_risk(patient_id, db)

            # "I took it, BP was 135/85" — the reading must not be dropped.
            systolic, diastolic = parse_bp(message)
            if systolic is not None:
                bp_reply, escalation_created = await _record_bp_reading(
                    patient_id, systolic, diastolic, message, db, now
                )
                bot_reply = f"{bot_reply} {bp_reply}"

        else:
            # A reminder is pending, but the reply may be an excuse OR an unrelated
            # question/appointment request. Only log a miss if it's actually about the dose.
            # A plain "no" to a reminder is a missed dose, model or no model.
            systolic, diastolic = parse_bp(message)
            if msg_lower.rstrip("!.") in NO_WORDS:
                intent = "missed"
            elif (systolic is not None and not barrier_override(message)
                  and classify_intent_rule(message) != "missed"):
                intent = "reading"
            else:
                intent = await classify_intent(name, message)
            # Cost / side-effect / out-of-stock are barriers — always flag & escalate,
            # never let them slip into casual conversation.
            if barrier_override(message):
                intent = "missed"
            if intent == "reading":
                # A reading sent instead of YES must not be dropped; the dose
                # question stays open.
                bp_reply, escalation_created = await _record_bp_reading(
                    patient_id, systolic, diastolic, message, db, now
                )
                await db.commit()
                return (f"{bp_reply}\n\nHave you taken your {drug_name} today? Reply YES once you have.",
                        None, escalation_created)
            if intent == "appointment":
                booking = await _start_booking(patient_id, name, doctor_name, service_type,
                                               condition, message, db)
                if booking:
                    return booking
            if intent in ("appointment", "question", "other"):
                facts, history = await _build_context(patient_id, db, name, condition, drug_name,
                                                      drug_dosage, streak, reminder_time)
                bot_reply = await generate_assistant_reply(facts, history, message)
                # keep the reminder pending — they still haven't answered
                await db.execute(
                    """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
                       ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
                    (patient_id, "awaiting_medication_ack", "{}")
                )
                await db.commit()
                return bot_reply, None, False

            # Missed/blocked dose — shared handler logs it and applies escalation rules
            bot_reply, reason, escalation_created, dose_missed = await _handle_missed_dose(
                patient_id, name, message, db, now, today
            )
            # "Didn't take it, BP was 150/95" — keep the reading too.
            if systolic is not None:
                bp_reply, bp_escalated = await _record_bp_reading(
                    patient_id, systolic, diastolic, message, db, now
                )
                bot_reply = f"{bot_reply} {bp_reply}"
                escalation_created = escalation_created or bp_escalated
            if not dose_missed:
                # A symptom, not an answer: today's dose is still unknown.
                bot_reply = f"{bot_reply}\n\nHave you taken your {drug_name} today? Reply YES once you have."
                new_flow = "awaiting_medication_ack"

    # ── CHECK-IN flow ──
    # Only a reading completes it. Anything else — a question, a side effect —
    # is handled as free text below, never answered with "send your reading":
    # that loop once swallowed a swelling report without escalating it.
    elif current_flow in ("checkin_bp", "awaiting_bp") and parse_bp(message)[0] is not None:
        systolic, diastolic = parse_bp(message)
        bot_reply, escalation_created = await _record_bp_reading(
            patient_id, systolic, diastolic, message, db, now
        )
        new_flow = "idle"

    # ── IDLE / free text ──
    else:
        # Check if it looks like a BP reading
        systolic, diastolic = parse_bp(message)
        if systolic:
            bot_reply, escalation_created = await _record_bp_reading(
                patient_id, systolic, diastolic, message, db, now
            )
        elif wants_to_report_bp(message):
            # Patient says they want to share a reading but sent no numbers — prime the BP flow
            bot_reply = f"Of course, {display_first_name(name)}! 📋 Please send your reading as two numbers, like 135/86."
            new_flow = "awaiting_bp"
        elif is_yes(message):
            # Treat as medication ack even from idle
            await db.execute(
                "INSERT INTO adherence_logs (patient_id, log_date, response, created_at) VALUES (?,?,?,?)",
                (patient_id, today, "yes", now)
            )
            bot_reply = await generate_bot_reply(name, "awaiting_medication_ack", message, streak=streak + 1)
        else:
            # Not a YES, not a reading — figure out what the patient actually wants
            if msg_lower.rstrip("!.") in NO_WORDS:
                intent = "missed"
            else:
                intent = await classify_intent(name, message)

            # Cost / side-effect / out-of-stock are barriers — always flag & escalate,
            # even if the classifier thought it was casual conversation.
            if barrier_override(message):
                intent = "missed"

            booking = None
            if intent == "appointment":
                booking = await _start_booking(patient_id, name, doctor_name, service_type,
                                               condition, message, db)
            if booking:
                return booking
            if intent == "missed":
                bot_reply, reason, escalation_created, _ = await _handle_missed_dose(
                    patient_id, name, message, db, now, today
                )
            else:
                # appointment / question / general chat — no adherence logging
                facts, history = await _build_context(patient_id, db, name, condition, drug_name,
                                                      drug_dosage, streak, reminder_time)
                bot_reply = await generate_assistant_reply(facts, history, message)

    # Update conversation state
    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, new_flow, json.dumps(new_context))
    )
    await db.commit()

    return bot_reply or "Thank you — your care team has been updated.", reason, escalation_created


async def trigger_care_reminder(patient_id: int, db: Connection) -> str:
    """Trigger the category-specific care reminder used by the demo controls."""
    cursor = await db.execute(
        "SELECT name, drug_name, drug_dosage, category, service_type, care_instructions FROM patients WHERE id=?",
        (patient_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return ""
    name, drug, dosage, category, service_type, care_instructions = row
    first = display_first_name(name)

    if category in ("dental", "eye", "general"):
        await db.execute(
            """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
               ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
            (patient_id, f"awaiting_{category}_aftercare", "{}"),
        )
        await db.commit()
        instruction = care_instructions or (
            "Follow the aftercare instructions from your dental team."
            if category == "dental" else "Follow the care instructions from your clinical team."
        )
        if category == "eye":
            return f"Hi {first}! 👁️ How is your {service_type or 'eye-care treatment'} follow-up today? Please confirm when you’ve followed this advice: {instruction}"
        if category == "general":
            return f"Hi {first}! How is your {service_type or 'clinic follow-up'} today? Please confirm when you’ve completed this next step: {instruction}"
        return f"Hi {first}! 🦷 How is your {service_type or 'dental treatment'} recovery today? Please confirm when you’ve followed this advice: {instruction}"

    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, "awaiting_medication_ack", "{}")
    )
    await db.commit()

    return f"Hello {first}! 💊 It is time to take your {drug} ({dosage}). Reply YES when done, or NO if you missed it."


async def trigger_medication_reminder(patient_id: int, db: Connection) -> str:
    return await trigger_care_reminder(patient_id, db)


async def trigger_checkin(patient_id: int, db: Connection) -> str:
    cursor = await db.execute(
        "SELECT name, category, service_type FROM patients WHERE id=?",
        (patient_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return ""
    name, category, service_type = row
    first = display_first_name(name)

    if category in ("dental", "eye", "general"):
        await db.execute(
            """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
               ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
            (patient_id, f"awaiting_{category}_checkin", "{}"),
        )
        await db.commit()
        if category == "eye":
            return f"Hi {first}! 👁️ How is your recovery after your {service_type or 'eye-care treatment'}? Reply DONE if you’re well, or tell us about any vision or eye concern."
        if category == "general":
            await db.execute(
                "UPDATE conversation_state SET current_flow='awaiting_general_checkin' WHERE patient_id=?",
                (patient_id,),
            )
            await db.commit()
            return f"Hi {first}! How is your {service_type or 'clinic follow-up'} going? Reply DONE if you’re on track, or tell us what help you need."
        return f"Hi {first}! 🦷 How is your recovery after your {service_type or 'dental treatment'}? Reply DONE if you’re well, or tell us about any pain, swelling, bleeding, or other concern."

    await db.execute(
        """INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?,?,?)
           ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow, context=excluded.context""",
        (patient_id, "awaiting_bp", "{}")
    )
    await db.commit()

    return f"Weekly check-in, {first}! 📋 What was your blood pressure reading this week? (e.g. 128/82)"


async def trigger_bp_checkin(patient_id: int, db: Connection) -> str:
    return await trigger_checkin(patient_id, db)
