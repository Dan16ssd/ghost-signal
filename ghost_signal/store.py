"""Small SQLite store: opt-outs, rate limits, duplicate messages, daily AI budget, reminders.

One file (GHOST_DB, default ghost_signal.db) so state survives a restart.
Message texts are never stored, except the words of a reminder the person asked us to keep.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass

from .config import settings

_lock = threading.Lock()
_db: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS optout (number TEXT PRIMARY KEY, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS seen (sid TEXT PRIMARY KEY, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS hits (number TEXT NOT NULL, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS hits_number ON hits (number, at);
CREATE TABLE IF NOT EXISTS usage (day TEXT NOT NULL, kind TEXT NOT NULL, n INTEGER NOT NULL,
                                  PRIMARY KEY (day, kind));
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL, due REAL NOT NULL, what TEXT NOT NULL, lang TEXT NOT NULL,
    label TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'waiting', created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS reminders_due ON reminders (state, due);
CREATE TABLE IF NOT EXISTS meds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL, times TEXT NOT NULL, what TEXT NOT NULL, spoken TEXT NOT NULL,
    lang TEXT NOT NULL, tz TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS doses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    med_id INTEGER NOT NULL, due REAL NOT NULL, next_try REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'waiting',
    ring_pending INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS doses_next ON doses (state, next_try);
CREATE TABLE IF NOT EXISTS family (
    person TEXT NOT NULL, contact TEXT NOT NULL, ok INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
    PRIMARY KEY (person, contact)
);
"""


def open_db(path: str | None = None) -> sqlite3.Connection:
    """(Re)open the database; tests pass ':memory:'."""
    global _db
    with _lock:
        if _db is not None:
            _db.close()
        _db = sqlite3.connect(path or settings.db_path, check_same_thread=False, isolation_level=None)
        _db.executescript(SCHEMA)
        return _db


def _conn() -> sqlite3.Connection:
    return _db if _db is not None else open_db()


def _run(sql: str, args: tuple = ()) -> list[tuple]:
    with _lock:
        return _conn().execute(sql, args).fetchall()


# --- STOP / START -----------------------------------------------------------


def opt_out(number: str) -> None:
    _run("INSERT OR REPLACE INTO optout VALUES (?, ?)", (number, time.time()))
    _run("UPDATE reminders SET state = 'cancelled' WHERE number = ? AND state = 'waiting'", (number,))
    _run("UPDATE meds SET active = 0 WHERE number = ?", (number,))
    _run("UPDATE doses SET state = 'cancelled' WHERE state = 'waiting' AND med_id IN "
         "(SELECT id FROM meds WHERE number = ?)", (number,))


def opt_in(number: str) -> None:
    _run("DELETE FROM optout WHERE number = ?", (number,))


def opted_out(number: str) -> bool:
    return bool(_run("SELECT 1 FROM optout WHERE number = ?", (number,)))


# --- Twilio retries -----------------------------------------------------------


def first_time(sid: str | None) -> bool:
    """True the first time a Twilio MessageSid is seen (Twilio may deliver a webhook twice)."""
    if not sid:
        return True
    with _lock:
        cur = _conn().execute("INSERT OR IGNORE INTO seen VALUES (?, ?)", (sid, time.time()))
        return cur.rowcount == 1


# --- Limits -----------------------------------------------------------------


def allowed(number: str, limit: int, now: float | None = None) -> bool:
    """At most `limit` questions per number per hour."""
    now = time.time() if now is None else now
    with _lock:
        db = _conn()
        db.execute("DELETE FROM hits WHERE at < ?", (now - 3600,))
        (n,) = db.execute("SELECT COUNT(*) FROM hits WHERE number = ? AND at > ?", (number, now - 3600)).fetchone()
        if n >= limit:
            return False
        db.execute("INSERT INTO hits VALUES (?, ?)", (number, now))
        return True


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def used_today(kind: str) -> int:
    rows = _run("SELECT n FROM usage WHERE day = ? AND kind = ?", (_today(), kind))
    return rows[0][0] if rows else 0


def count(kind: str) -> None:
    _run(
        "INSERT INTO usage VALUES (?, ?, 1) ON CONFLICT (day, kind) DO UPDATE SET n = n + 1",
        (_today(), kind),
    )


# --- Reminders ----------------------------------------------------------------


@dataclass
class Reminder:
    id: int
    number: str
    due: float  # unix time
    what: str
    lang: str
    label: str  # due time as the person reads it, e.g. "Fri 28 Nov 20:00"


def add_reminder(number: str, due: float, what: str, lang: str, label: str) -> int:
    with _lock:
        cur = _conn().execute(
            "INSERT INTO reminders (number, due, what, lang, label, created) VALUES (?, ?, ?, ?, ?, ?)",
            (number, due, what, lang, label, time.time()),
        )
        return int(cur.lastrowid)


def _reminders(sql: str, args: tuple) -> list[Reminder]:
    return [Reminder(*row) for row in _run(f"SELECT id, number, due, what, lang, label FROM reminders {sql}", args)]


def waiting(number: str) -> list[Reminder]:
    return _reminders("WHERE number = ? AND state = 'waiting' ORDER BY due", (number,))


def cancel_reminder(number: str, position: int) -> Reminder | None:
    """Cancel the n-th waiting reminder (1-based, as shown by REMIND LIST)."""
    items = waiting(number)
    if not 1 <= position <= len(items):
        return None
    r = items[position - 1]
    _run("UPDATE reminders SET state = 'cancelled' WHERE id = ?", (r.id,))
    return r


def due_reminders(now: float | None = None) -> list[Reminder]:
    now = time.time() if now is None else now
    return _reminders("WHERE state = 'waiting' AND due <= ? ORDER BY due", (now,))


def mark(reminder_id: int, state: str) -> None:
    _run("UPDATE reminders SET state = ? WHERE id = ?", (state, reminder_id))


def inbox(number: str) -> list[Reminder]:
    """Reminders delivered to a web simulator visitor (they have no phone to text)."""
    items = _reminders("WHERE number = ? AND state = 'inbox' ORDER BY due", (number,))
    for r in items:
        mark(r.id, "sent")
    return items


def stats() -> dict:
    (waiting_n,) = _run("SELECT COUNT(*) FROM reminders WHERE state = 'waiting'")[0]
    return {
        "questions_today": used_today("question"),
        "ai_calls_today": used_today("ai"),
        "ai_budget_per_day": settings.max_ai_calls_per_day,
        "reminders_waiting": waiting_n,
    }


# --- Medicine calls ------------------------------------------------------------


@dataclass
class Med:
    id: int
    number: str
    times: str  # "08:00,20:00" local time
    what: str  # as the person wrote it
    spoken: str  # what the call voice says (may be translated, e.g. Lao -> Thai)
    lang: str
    tz: str


@dataclass
class Dose:
    id: int
    med_id: int
    due: float
    next_try: float
    attempts: int
    state: str  # waiting | confirmed | missed | cancelled


_MED_COLS = "id, number, times, what, spoken, lang, tz"
_DOSE_COLS = "id, med_id, due, next_try, attempts, state"


def add_med(number: str, times: str, what: str, spoken: str, lang: str, tz: str) -> int:
    with _lock:
        cur = _conn().execute(
            "INSERT INTO meds (number, times, what, spoken, lang, tz, created) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (number, times, what, spoken, lang, tz, time.time()),
        )
        return int(cur.lastrowid)


def meds_of(number: str) -> list[Med]:
    return [Med(*r) for r in _run(f"SELECT {_MED_COLS} FROM meds WHERE number = ? AND active = 1 ORDER BY id", (number,))]


def med(med_id: int) -> Med | None:
    rows = _run(f"SELECT {_MED_COLS} FROM meds WHERE id = ? AND active = 1", (med_id,))
    return Med(*rows[0]) if rows else None


def stop_med(med_id: int) -> None:
    _run("UPDATE meds SET active = 0 WHERE id = ?", (med_id,))
    _run("UPDATE doses SET state = 'cancelled' WHERE med_id = ? AND state = 'waiting'", (med_id,))


def stop_all_meds(number: str) -> None:
    for m in meds_of(number):
        stop_med(m.id)


def add_dose(med_id: int, due: float) -> int:
    with _lock:
        cur = _conn().execute("INSERT INTO doses (med_id, due, next_try) VALUES (?, ?, ?)", (med_id, due, due))
        return int(cur.lastrowid)


def dose(dose_id: int) -> Dose | None:
    rows = _run(f"SELECT {_DOSE_COLS} FROM doses WHERE id = ?", (dose_id,))
    return Dose(*rows[0]) if rows else None


def doses_to_try(now: float | None = None) -> list[Dose]:
    now = time.time() if now is None else now
    return [Dose(*r) for r in _run(
        f"SELECT {_DOSE_COLS} FROM doses WHERE state = 'waiting' AND next_try <= ? ORDER BY next_try", (now,))]


def dose_tried(dose_id: int, next_try: float, ring_web: bool = False) -> None:
    _run("UPDATE doses SET attempts = attempts + 1, next_try = ?, ring_pending = ? WHERE id = ?",
         (next_try, 1 if ring_web else 0, dose_id))


def set_dose_state(dose_id: int, state: str) -> None:
    _run("UPDATE doses SET state = ?, ring_pending = 0 WHERE id = ?", (state, dose_id))


def ringing_dose(number: str) -> Dose | None:
    """The dose this person was just called (or texted) about and has not confirmed yet."""
    rows = _run(
        f"SELECT {', '.join('d.' + c for c in _DOSE_COLS.split(', '))} FROM doses d JOIN meds m ON m.id = d.med_id "
        "WHERE m.number = ? AND d.state = 'waiting' AND d.attempts > 0 ORDER BY d.due LIMIT 1",
        (number,),
    )
    return Dose(*rows[0]) if rows else None


def web_rings(number: str) -> list[Dose]:
    """Calls waiting to 'ring' in a simulator visitor's browser."""
    rows = _run(
        f"SELECT {', '.join('d.' + c for c in _DOSE_COLS.split(', '))} FROM doses d JOIN meds m ON m.id = d.med_id "
        "WHERE m.number = ? AND d.ring_pending = 1 AND d.state = 'waiting'",
        (number,),
    )
    _run("UPDATE doses SET ring_pending = 0 WHERE med_id IN (SELECT id FROM meds WHERE number = ?)", (number,))
    return [Dose(*r) for r in rows]


def invite_family(person: str, contact: str) -> None:
    _run("INSERT OR REPLACE INTO family VALUES (?, ?, 0, ?)", (person, contact, time.time()))


def accept_family(contact: str) -> list[str]:
    """The contact replied YES: returns the people they now watch over."""
    people = [r[0] for r in _run("SELECT person FROM family WHERE contact = ? AND ok = 0", (contact,))]
    _run("UPDATE family SET ok = 1 WHERE contact = ?", (contact,))
    return people


def pending_invites(contact: str) -> bool:
    return bool(_run("SELECT 1 FROM family WHERE contact = ? AND ok = 0", (contact,)))


def family_of(person: str) -> list[str]:
    return [r[0] for r in _run("SELECT contact FROM family WHERE person = ? AND ok = 1", (person,))]
