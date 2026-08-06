"""Deterministic appointment scheduling for the patient-access workflow.

The language model may help transcribe a request, but it never invents clinic
availability. Dates, slots, double-booking protection and state changes are all
handled here against the shared database.
"""

import re
from datetime import date, datetime, timedelta

from db import Connection


MORNING_SLOTS = ("09:00", "10:00", "11:00")
AFTERNOON_SLOTS = ("13:00", "14:00", "15:00")
ALL_SLOTS = MORNING_SLOTS + AFTERNOON_SLOTS
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

APPOINTMENT_COLUMNS = (
    "id", "patient_id", "patient_name", "appointment_date", "appointment_time",
    "clinician_name", "visit_type", "status", "created_at", "updated_at",
)
CLINICIANS = ("Dr. Mensah", "Dr. Ama Boateng", "Dr. Kwesi Asante")


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def appointment_intent(text: str) -> str | None:
    """Return book/reschedule/cancel/status when a message is appointment work."""
    value = _normalise(text)
    appointment_words = ("appointment", "clinic visit", "see the doctor", "see doctor")
    has_appointment = any(word in value for word in appointment_words)
    if has_appointment and any(word in value for word in ("cancel", "remove", "call off")):
        return "cancel"
    if any(word in value for word in ("reschedule", "move my appointment", "change my appointment")):
        return "reschedule"
    if has_appointment and any(word in value for word in ("when is", "what time", "details", "check my")):
        return "status"
    if has_appointment or any(word in value for word in ("book me", "book a visit", "schedule a visit")):
        return "book"
    return None


def requested_period(text: str) -> str | None:
    value = _normalise(text)
    if any(word in value for word in ("morning", "anɔpa", "anopa", "before noon")):
        return "morning"
    if any(word in value for word in ("afternoon", "evening", "awia", "after lunch")):
        return "afternoon"
    return None


def requested_clinician(text: str, default: str) -> str:
    """Resolve only approved clinic names; never invent a clinician from prose."""
    value = _normalise(text).replace(".", "")
    for clinician in CLINICIANS:
        searchable = clinician.lower().replace(".", "")
        full_name = searchable.removeprefix("dr ")
        surname = full_name.split()[-1]
        if searchable in value or f"dr {surname}" in value:
            return clinician
    return default


def parse_requested_date(text: str, today: date | None = None) -> date | None:
    """Parse the small, explicit date vocabulary used by the booking flow."""
    today = today or date.today()
    value = _normalise(text)

    iso = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", value)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None

    if any(word in value for word in ("day after tomorrow", "the next day after tomorrow")):
        return today + timedelta(days=2)
    if any(word in value for word in ("tomorrow", "ɔkyena", "akyena")):
        return today + timedelta(days=1)
    if re.search(r"\btoday\b", value):
        return today

    for weekday, target in WEEKDAYS.items():
        if re.search(rf"\b{weekday}\b", value):
            days_ahead = (target - today.weekday()) % 7
            return today + timedelta(days=days_ahead or 7)

    month_names = "|".join(MONTHS)
    day_first = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})(?:\s+(20\d{{2}}))?\b", value)
    month_first = re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?\b", value)
    match = day_first or month_first
    if match:
        if day_first:
            day_value, month_value, year_value = match.group(1), match.group(2), match.group(3)
        else:
            month_value, day_value, year_value = match.group(1), match.group(2), match.group(3)
        year = int(year_value) if year_value else today.year
        try:
            parsed = date(year, MONTHS[month_value], int(day_value))
            if not year_value and parsed < today:
                parsed = date(year + 1, MONTHS[month_value], int(day_value))
            return parsed
        except ValueError:
            return None
    return None


def validate_appointment_date(value: date, today: date | None = None) -> str | None:
    today = today or date.today()
    if value < today:
        return "That date has already passed. Please choose a future clinic day."
    if value.weekday() >= 5:
        return "The clinic books appointments Monday to Friday. Please choose a weekday."
    return None


def slots_for_period(period: str | None) -> tuple[str, ...]:
    if period == "morning":
        return MORNING_SLOTS
    if period == "afternoon":
        return AFTERNOON_SLOTS
    return ALL_SLOTS


def format_date(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%A, %d %B %Y")


def format_time(value: str) -> str:
    return datetime.strptime(value, "%H:%M").strftime("%-I:%M %p")


def parse_slot_choice(text: str, offered: list[str]) -> str | None:
    value = _normalise(text)
    number = re.search(r"\b([1-6])\b", value)
    if number:
        index = int(number.group(1)) - 1
        if 0 <= index < len(offered):
            return offered[index]

    clock = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", value)
    if clock:
        hour = int(clock.group(1))
        minute = int(clock.group(2) or 0)
        suffix = clock.group(3)
        if suffix == "pm" and hour < 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
        candidate = f"{hour:02d}:{minute:02d}"
        if candidate in offered:
            return candidate
    return None


def _appointment_from_row(row) -> dict:
    return dict(zip(APPOINTMENT_COLUMNS, row))


async def available_slots(
    db: Connection, clinician_name: str, appointment_date: str, period: str | None = None,
) -> list[str]:
    cursor = await db.execute(
        """SELECT appointment_time FROM appointments
           WHERE clinician_name=? AND appointment_date=? AND status='confirmed'""",
        (clinician_name, appointment_date),
    )
    booked = {row[0] for row in await cursor.fetchall()}
    return [slot for slot in slots_for_period(period) if slot not in booked][:3]


async def get_appointment(db: Connection, appointment_id: int) -> dict | None:
    cursor = await db.execute(
        """SELECT a.id, a.patient_id, p.name, a.appointment_date, a.appointment_time,
                  a.clinician_name, a.visit_type, a.status, a.created_at, a.updated_at
           FROM appointments a JOIN patients p ON p.id=a.patient_id WHERE a.id=?""",
        (appointment_id,),
    )
    row = await cursor.fetchone()
    return _appointment_from_row(row) if row else None


async def list_appointments(
    db: Connection, patient_id: int | None = None, include_past: bool = True,
) -> list[dict]:
    where = []
    params: list[object] = []
    if patient_id is not None:
        where.append("a.patient_id=?")
        params.append(patient_id)
    if not include_past:
        where.append("a.appointment_date>=?")
        params.append(date.today().isoformat())
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    cursor = await db.execute(
        f"""SELECT a.id, a.patient_id, p.name, a.appointment_date, a.appointment_time,
                   a.clinician_name, a.visit_type, a.status, a.created_at, a.updated_at
            FROM appointments a JOIN patients p ON p.id=a.patient_id
            {clause}
            ORDER BY a.appointment_date ASC, a.appointment_time ASC""",
        tuple(params),
    )
    return [_appointment_from_row(row) for row in await cursor.fetchall()]


async def next_appointment(db: Connection, patient_id: int) -> dict | None:
    cursor = await db.execute(
        """SELECT a.id, a.patient_id, p.name, a.appointment_date, a.appointment_time,
                  a.clinician_name, a.visit_type, a.status, a.created_at, a.updated_at
           FROM appointments a JOIN patients p ON p.id=a.patient_id
           WHERE a.patient_id=? AND a.status='confirmed' AND a.appointment_date>=?
           ORDER BY a.appointment_date ASC, a.appointment_time ASC LIMIT 1""",
        (patient_id, date.today().isoformat()),
    )
    row = await cursor.fetchone()
    return _appointment_from_row(row) if row else None


async def create_appointment(
    db: Connection, patient_id: int, appointment_date: str, appointment_time: str,
    clinician_name: str, visit_type: str,
) -> dict:
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO appointments
           (patient_id, appointment_date, appointment_time, clinician_name, visit_type,
            status, created_at, updated_at)
           VALUES (?,?,?,?,?,'confirmed',?,?)""",
        (patient_id, appointment_date, appointment_time, clinician_name, visit_type, now, now),
    )
    await db.commit()
    return await get_appointment(db, cursor.lastrowid)


async def reschedule_appointment(
    db: Connection, appointment_id: int, appointment_date: str, appointment_time: str,
    clinician_name: str | None = None,
) -> dict | None:
    if clinician_name:
        await db.execute(
            """UPDATE appointments SET appointment_date=?, appointment_time=?, clinician_name=?,
                       status='confirmed', updated_at=? WHERE id=?""",
            (appointment_date, appointment_time, clinician_name, datetime.now().isoformat(), appointment_id),
        )
    else:
        await db.execute(
            """UPDATE appointments SET appointment_date=?, appointment_time=?, status='confirmed',
                       updated_at=? WHERE id=?""",
            (appointment_date, appointment_time, datetime.now().isoformat(), appointment_id),
        )
    await db.commit()
    return await get_appointment(db, appointment_id)


async def update_status(db: Connection, appointment_id: int, status: str) -> dict | None:
    await db.execute(
        "UPDATE appointments SET status=?, updated_at=? WHERE id=?",
        (status, datetime.now().isoformat(), appointment_id),
    )
    await db.commit()
    return await get_appointment(db, appointment_id)


def appointment_confirmation(appointment: dict, action: str = "booked") -> str:
    return (
        f"✅ Your appointment is {action} for {format_date(appointment['appointment_date'])} "
        f"at {format_time(appointment['appointment_time'])} with {appointment['clinician_name']} "
        f"at Accra Family Clinic. Reference: VC-{appointment['id']:04d}."
    )


async def offer_slots(
    db: Connection, clinician_name: str, requested_date: date, period: str | None,
) -> tuple[list[str], str]:
    error = validate_appointment_date(requested_date)
    if error:
        return [], error
    date_value = requested_date.isoformat()
    slots = await available_slots(db, clinician_name, date_value, period)
    if not slots:
        return [], f"There are no available {period or ''} slots on {format_date(date_value)}. Please choose another weekday."
    choices = "\n".join(f"{index}. {format_time(slot)}" for index, slot in enumerate(slots, 1))
    return slots, f"Available times on {format_date(date_value)}:\n{choices}\nReply with the number or time you prefer."


async def handle_appointment_turn(
    db: Connection, patient_id: int, patient_name: str, clinician_name: str,
    visit_type: str, current_flow: str, context: dict, message: str,
) -> tuple[str, str, dict] | None:
    """Handle one appointment turn, returning reply/new flow/new context."""
    intent = appointment_intent(message)
    in_flow = current_flow.startswith("appointment_")
    if not intent and not in_flow:
        return None

    first = patient_name.split()[0] if patient_name else "there"
    selected_clinician = context.get("clinician_name") or requested_clinician(message, clinician_name)

    if current_flow == "appointment_awaiting_cancel":
        if _normalise(message) in ("cancel", "confirm", "yes", "yes cancel", "confirm cancel"):
            appointment = await update_status(db, int(context["appointment_id"]), "cancelled")
            if appointment:
                return (
                    f"Your appointment on {format_date(appointment['appointment_date'])} at "
                    f"{format_time(appointment['appointment_time'])} has been cancelled.",
                    "idle", {},
                )
        return ("No problem—your appointment is still confirmed.", "idle", {})

    if intent == "status":
        appointment = await next_appointment(db, patient_id)
        if not appointment:
            return ("You do not have an upcoming appointment. Tell me which weekday you prefer and I can book one.", "idle", {})
        return (
            f"Your next appointment is {format_date(appointment['appointment_date'])} at "
            f"{format_time(appointment['appointment_time'])} with {appointment['clinician_name']}. "
            f"Reference: VC-{appointment['id']:04d}.",
            "idle", {},
        )

    if intent == "cancel":
        appointment = await next_appointment(db, patient_id)
        if not appointment:
            return ("You do not have an upcoming appointment to cancel.", "idle", {})
        return (
            f"Your appointment is {format_date(appointment['appointment_date'])} at "
            f"{format_time(appointment['appointment_time'])}. Reply CANCEL to confirm cancellation.",
            "appointment_awaiting_cancel", {"appointment_id": appointment["id"]},
        )

    mode = context.get("mode", "book") if in_flow else (intent or "book")
    appointment_id = context.get("appointment_id")
    if intent == "reschedule" and not in_flow:
        appointment = await next_appointment(db, patient_id)
        if not appointment:
            mode = "book"
        else:
            mode = "reschedule"
            appointment_id = appointment["id"]
            selected_clinician = requested_clinician(message, appointment["clinician_name"])

    if current_flow == "appointment_awaiting_slot":
        offered = list(context.get("slots", []))
        selected = parse_slot_choice(message, offered)
        if not selected:
            choices = ", ".join(f"{i + 1} for {format_time(slot)}" for i, slot in enumerate(offered))
            return (f"Please choose one of the available times: {choices}.", current_flow, context)
        try:
            if mode == "reschedule" and appointment_id:
                appointment = await reschedule_appointment(
                    db, int(appointment_id), context["appointment_date"], selected,
                    selected_clinician,
                )
                action = "rescheduled"
            else:
                appointment = await create_appointment(
                    db, patient_id, context["appointment_date"], selected,
                    selected_clinician, visit_type or "Clinic consultation",
                )
                action = "booked"
        except Exception as exc:
            if "unique" not in str(exc).lower() and "constraint" not in str(exc).lower():
                raise
            slots, reply = await offer_slots(
                db, selected_clinician, date.fromisoformat(context["appointment_date"]), context.get("period"),
            )
            return (f"That time was just taken. {reply}", current_flow, {**context, "slots": slots})
        if not appointment:
            return ("I could not update that appointment. Please ask the clinic team for help.", "idle", {})
        return (appointment_confirmation(appointment, action), "idle", {})

    requested_date = parse_requested_date(message)
    period = requested_period(message) or context.get("period")
    if not requested_date:
        action = "move your appointment" if mode == "reschedule" else "book your appointment"
        return (
            f"Of course, {first}. Which weekday would you prefer to {action}? You can say, for example, Tuesday morning.",
            "appointment_awaiting_date",
            {"mode": mode, "appointment_id": appointment_id, "clinician_name": selected_clinician},
        )

    slots, reply = await offer_slots(db, selected_clinician, requested_date, period)
    if not slots:
        return (
            reply,
            "appointment_awaiting_date",
            {"mode": mode, "appointment_id": appointment_id, "clinician_name": selected_clinician},
        )
    return (
        reply,
        "appointment_awaiting_slot",
        {
            "mode": mode,
            "appointment_id": appointment_id,
            "clinician_name": selected_clinician,
            "appointment_date": requested_date.isoformat(),
            "period": period,
            "slots": slots,
        },
    )


async def latest_changed_since(
    db: Connection, patient_id: int, changed_since: str,
) -> dict | None:
    cursor = await db.execute(
        """SELECT a.id, a.patient_id, p.name, a.appointment_date, a.appointment_time,
                  a.clinician_name, a.visit_type, a.status, a.created_at, a.updated_at
           FROM appointments a JOIN patients p ON p.id=a.patient_id
           WHERE a.patient_id=? AND a.updated_at>=?
           ORDER BY a.updated_at DESC LIMIT 1""",
        (patient_id, changed_since),
    )
    row = await cursor.fetchone()
    return _appointment_from_row(row) if row else None
