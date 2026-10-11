"""THE NOISE PRINT CATALOGUE — the declared ways a word gets corrupted on its way to us.

⇒ WHY A CATALOGUE AND NOT A FUZZY MATCHER (operator, 2026-09-07)

Denoising is not deciphering. A cipher guarantees a plaintext and is invertible by construction;
noise DESTROYS information, COMPOSES several corruptions at once, and may have no coherent original
at all — the person may have been confused, or changed their mind mid-sentence. So an edit-distance
threshold answers the wrong question. "Is this within two edits of `running`?" is a similarity
score. The question that licenses a repair is: **is the difference explained by corruptions we have
declared?** A print that is not in this catalogue is not a near miss to be tolerated — it is the
signal to ASK.

That makes the catalogue's real output a trichotomy, and it is the same one ROUTE emits:
    every edit explained  → the repair has EVIDENCE, and the prints are the evidence
    an edit unexplained   → we cannot read it → ASK, naming what we could not account for
    (and the caller refuses when two candidates are both explained — ambiguity is never resolved
     here; see `explain_all`.)

⇒ DERIVED FROM MEASURED NOISE, NOT INVENTED. Every print below was mined from 1,766 held-out and
tuned marathon turns (1,157 corrupted tokens explained). The share each carries is recorded on it.
The largest single family was MIXED at 27% — real corruptions compose — which is why this module
explains a word EDIT BY EDIT rather than matching whole-word shapes. A composition of declared
prints is itself declared; a composition containing one undeclared edit is not.

CASE is deliberately absent: a case-mangled token still matches case-insensitively, so it never
blocks recognition and needs no print.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

VOWELS = frozenset("aeiou")

# ⇒ LEET — the digit-and-symbol-for-letter substitutions actually observed (`cr34t3`, `r1nning`,
#   `th3`, `0n`, `c@n`). A closed table, not a rule: only what the world has been seen to type.
#   A symbol may stand for MORE THAN ONE letter (`1` is both `i` and `l`), so the value is a set —
#   a dict of single letters silently dropped one of them.
LEET: Dict[str, frozenset] = {
    "0": frozenset("o"),
    "1": frozenset("il"),
    "3": frozenset("e"),
    "4": frozenset("a"),
    "5": frozenset("s"),
    "6": frozenset("g"),
    "7": frozenset("t"),
    "8": frozenset("b"),
    "9": frozenset("g"),
    "@": frozenset("a"),
    "$": frozenset("s"),
    "!": frozenset("i"),
    "|": frozenset("l"),
}

# ⇒ QWERTY ADJACENCY — a typo that lands on a neighbouring key is a different print from a typo
#   that lands anywhere else: the first is a slip of the hand, the second needs another
#   explanation. Declared for the one layout we have evidence for.
_QWERTY_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def _adjacency() -> Dict[str, frozenset]:
    adj: Dict[str, set] = {}
    for r, row in enumerate(_QWERTY_ROWS):
        for c, ch in enumerate(row):
            near = set()
            if c:
                near.add(row[c - 1])
            if c + 1 < len(row):
                near.add(row[c + 1])
            for dr in (-1, 1):
                if 0 <= r + dr < len(_QWERTY_ROWS):
                    other = _QWERTY_ROWS[r + dr]
                    for cc in (c - 1, c, c + 1):
                        if 0 <= cc < len(other):
                            near.add(other[cc])
            adj[ch] = near
    return {k: frozenset(v) for k, v in adj.items()}


KEY_NEIGHBOURS = _adjacency()


class Print(NamedTuple):
    """One declared corruption. `share` is its measured frequency in the mined marathon turns."""

    name: str
    doc: str
    share: str


PRINTS: Tuple[Print, ...] = (
    Print(
        "drop-vowel", "a vowel is left out — `runnin`, `stpped`, `dwn`, `whch`", "26%"
    ),
    Print("drop-consonant", "a consonant is left out — `snaphot`, `actuall`", "12%"),
    Print(
        "double",
        "a letter is repeated or an extra one slips in — `snapshott`, `allll`",
        "15%",
    ),
    Print(
        "key-adjacent",
        "a letter lands on a neighbouring QWERTY key — `gamna`",
        "part of 6%",
    ),
    Print(
        "substitute",
        "a letter is swapped for a non-neighbour — `shill` for `shell`",
        "6%",
    ),
    Print("transpose", "two adjacent letters swap — `snaphsot`, `grbunash`", "4%"),
    Print(
        "leet", "a digit or symbol stands in for a letter — `cr34te`, `r1nning`", "4%"
    ),
    Print("truncate", "the word is cut short — `stat` for `status`, `templ`", "4%"),
    Print(
        "stray-key",
        "an extra keypress lands next to a key really struck — `restaert`",
        "part of 15%",
    ),
)
BY_NAME: Dict[str, Print] = {p.name: p for p in PRINTS}


def _edit_script(clean: str, obs: str) -> Optional[List[Tuple[str, int, int]]]:
    """Damerau-Levenshtein backtrace: the ops that turn `clean` into `obs`.

    Returns (op, i, j) triples over the two strings, or None if the distance exceeds the cap — a
    corruption further away than this is not a corrupted WORD, it is a different word, and saying
    so is the honest answer.
    """
    n, m = len(clean), len(obs)
    if abs(n - m) > 4 or max(n, m) > 40:
        return None
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if clean[i - 1] == obs[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if (
                i > 1
                and j > 1
                and clean[i - 1] == obs[j - 2]
                and clean[i - 2] == obs[j - 1]
            ):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    if d[n][m] > 4:
        return None
    ops: List[Tuple[str, int, int]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if (
            i > 1
            and j > 1
            and clean[i - 1] == obs[j - 2]
            and clean[i - 2] == obs[j - 1]
            and d[i][j] == d[i - 2][j - 2] + 1
        ):
            ops.append(("transpose", i - 2, j - 2))
            i -= 2
            j -= 2
        elif (
            i > 0
            and j > 0
            and d[i][j] == d[i - 1][j - 1] + (clean[i - 1] != obs[j - 1])
        ):
            if clean[i - 1] != obs[j - 1]:
                ops.append(("substitute", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("delete", i - 1, j))
            i -= 1
        else:
            ops.append(("insert", i, j - 1))
            j -= 1
    ops.reverse()
    return ops


def explain(clean: str, observed: str) -> Optional[Tuple[str, ...]]:
    """Which declared prints account for `observed` being a corruption of `clean`?

    Returns the prints (a composition is itself an explanation) or **None when any single edit is
    not a declared print** — the caller must then ASK rather than repair. Never picks between
    candidates and never scores: it answers only "is this explained".
    """
    c, o = clean.lower(), observed.lower()
    if c == o:
        return ()
    ops = _edit_script(c, o)
    if ops is None:
        return None
    found: List[str] = []
    for op, i, j in ops:
        if op == "transpose":
            found.append("transpose")
        elif op == "delete":
            # ⇒ THE FRONT OF A WORD IS NOT LOST (2026-09-08). Truncation cuts the END — `runnin`,
            #   `templ`, `stat`. Nobody drops the first letters of a word; a token missing them is
            #   a DIFFERENT WORD. Without this, `remove` <- `move` is two mechanical drops and the
            #   substitution cap never sees it — the front door rewrote `move db to dmz` as
            #   `remove db to dmz` SEVEN times in one ruler, turning a transfer into a deletion.
            if i == 0:
                return None
            # a run of deletions off the end is the word being cut short, not letters going missing
            if i >= len(c) - 2 and j >= len(o):
                found.append("truncate")
            else:
                found.append("drop-vowel" if c[i] in VOWELS else "drop-consonant")
        elif op == "insert":
            ch = o[j]
            prev = o[j - 1] if j else ""
            nxt = o[j + 1] if j + 1 < len(o) else ""
            # ONLY a genuine repeat is declared. A stray letter that matches no neighbour is not
            #   a slip of the hand, it is a DIFFERENT WORD — treating it as a print explained
            #   `beta` <- `betamax` as three repeats, which would rewrite a real product name.
            if ch == prev or ch == nxt:
                found.append("double")
            elif ch in KEY_NEIGHBOURS.get(prev, ()) or ch in KEY_NEIGHBOURS.get(
                nxt, ()
            ):
                found.append(
                    "stray-key"
                )  # `restaert` — an extra key next to one really struck
            else:
                return None
        elif op == "substitute":
            a, b = c[i], o[j]
            if a in LEET.get(b, ()):
                found.append("leet")
            elif b in KEY_NEIGHBOURS.get(a, ()):
                found.append("key-adjacent")
            elif b.isalpha():
                found.append("substitute")
            else:
                return None  # a symbol standing for nothing declared
    # a contiguous cut off the end is ONE act of truncation, not one per letter — counting each
    #   letter made `template` <- `templ` breach the bound below and go unexplained.
    collapsed: List[str] = []
    for f in found:
        if f == "truncate" and collapsed and collapsed[-1] == "truncate":
            continue
        collapsed.append(f)
    found = collapsed
    # ⇒ AT MOST ONE LETTER-FOR-LETTER SUBSTITUTION. The mechanical prints — a dropped letter, a
    #   repeat, a swap, a cut — rarely land on ANOTHER REAL WORD; they leave a wreck. Substituting
    #   one letter for another is the print that turns a word into a different word, and two of
    #   them almost always do: `restart` <- `restore` is two substitutions, and admitting it
    #   rewrote `restart` across ELEVEN sealed corpus cases (caught by capture --diff, 2026-09-07).
    #   Leet is exempt — a digit standing for a letter cannot produce a real word.
    _swaps = sum(1 for f in found if f in ("substitute", "key-adjacent"))
    if _swaps > 1:
        return None
    # ⇒ A BOUND, OR THE CATALOGUE EXPLAINS ANYTHING. Enough declared prints compose into any word
    #   from any other: `running` <- `walking` came back as four substitutions. A corruption is a
    #   corruption of a word; past roughly a third of the word it is a different word, and the
    #   honest answer is that we cannot read it.
    if len(found) > max(1, len(c) // 3):
        return None
    return tuple(found)


def explain_all(observed: str, candidates) -> List[Tuple[str, Tuple[str, ...]]]:
    """Every candidate whose corruption is explained, with its prints — RANKED, never chosen.

    Ambiguity is not resolved here. One explained candidate is a repair with evidence; two or more
    is an ASK that can name both; none is an ASK that can say what could not be accounted for.
    Fewer prints ranks first only so a caller can present the simplest reading first.
    """
    out = []
    for cand in candidates:
        prints = explain(cand, observed)
        if prints is not None:
            out.append((cand, prints))
    out.sort(key=lambda x: (len(x[1]), x[0]))
    return out
