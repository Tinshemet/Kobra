"""English clock vocabulary extracted from Gorgon; see evidence/provenance.json."""

UNITS = frozenset(
    {"second", "seconds", "minute", "minutes", "hour", "hours", "day", "days"}
)

COARSE = frozenset({"night", "nights", "week", "weeks"})

FREQUENCY_ADVERBS = frozenset({"hourly", "daily", "nightly", "weekly"})

DEICTIC = frozenset({"tomorrow", "tonight", "yesterday", "overnight"})

WEEKDAYS = frozenset(
    {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
)

MONTHS = frozenset(
    {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)

RECURRING = frozenset({"every", "each"})
