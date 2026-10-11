"""Clock phrase detection, preserving Gorgon behavior; not calendar validation."""

import re
from typing import Optional, Tuple
from .clock_vocabulary import (
    UNITS,
    COARSE,
    FREQUENCY_ADVERBS as FREQUENCY,
    DEICTIC,
    WEEKDAYS,
    MONTHS,
    RECURRING,
)

CLOCK = re.compile(r"^(?:[0-2]?\d[:.][0-5]\d(?:am|pm)?|[0-2]?\d(?:am|pm))$")

RECURRENCE, INSTANT, EVENT = "recurrence", "instant", "event"


def _words(text: str) -> Tuple[str, ...]:
    """Tokens, with a number glued to a unit kept whole — `9pm` is one word, not nine and pm."""
    return tuple(
        re.findall(
            r"[a-z][a-z0-9_']*|[0-9]+[a-z:.]*[a-z0-9]*|[0-9]+", str(text).lower()
        )
    )


def clock_in(text: str) -> str:
    """RECURRENCE, INSTANT, or "" — does this name a time, and does it come round again?

    ⇒ **THE DISTINCTION IS WHAT THE STORE CAN HOLD.** `every: <span>` takes a recurrence and
      has no field for a one-off moment, so the two are told apart here rather than downstream
      where only one of them would fit.

    >>> clock_in("take a snapshot every night")
    'recurrence'
    >>> clock_in("stop every vm at 9pm")
    'instant'
    >>> clock_in("launch every vm that is currently stopped")
    ''
    """
    words = _words(text)
    if not words:
        return ""
    for i, w in enumerate(words):
        # ⇒⇒ **`every` IS ONLY A RECURRENCE WHEN A TIME FOLLOWS IT**, which is the entire
        #   difference between *"every night"* and *"every vm"*. `scan.UNIVERSAL` owns the
        #   other reading and neither has to know about the other — the word is the same and
        #   the noun decides, exactly as `the verb decides what the noun is` does one layer up.
        if w in RECURRING:
            tail = words[i + 1 : i + 3]
            if any(t in UNITS or t in COARSE or t in WEEKDAYS for t in tail):
                return RECURRENCE
            # ⇒ `every 2 hours` — a number between the quantifier and its unit.
            if (
                len(tail) > 1
                and tail[0].isdigit()
                and (tail[1] in UNITS or tail[1] in COARSE)
            ):
                return RECURRENCE
        if w in FREQUENCY:
            return RECURRENCE
    for w in words:
        if w in DEICTIC or w in WEEKDAYS or w in MONTHS or CLOCK.match(w):
            return INSTANT
    return ""


def clock_tail(clause: str) -> Optional[str]:
    """The clock ADJUNCT with its own words, locatable — or None.

    ⇒ `clock_in` classifies but carries no offsets, so *"at 21:30"* scored as a missed
      trigger from the day the eval was born (qual-0005 — the slot was held open by
      design). Closed shapes only: `at` + CLOCK | N am/pm | noon | midnight. `at the
      door` names a PLACE and is refused by the same closed test.
    """
    import re as _re

    low = str(clause).lower()
    m = _re.search(
        r"\bat ((?:[0-2]?\d[:.][0-5]\d(?:\s?[ap]m)?)"
        r"|(?:[0-2]?\d\s?[ap]m)|noon|midnight)\b",
        low,
    )
    return m.group(0) if m else None
