"""Ported front-door rules; see evidence/front-door-provenance.json.

Historical measurements in copied docstrings are not Kobra results.
"""

from typing import Optional, Sequence
from . import _english_lexicon as L

CLAUSE_MARKS = (",", ";", ".", "—", "–", "&&", "||")
CLAUSE_WORDS = L.CLAUSE_WORDS
_CUT_DETS = L.CUT_DETERMINERS
_CUT_NEG = L.CUT_NEGATION


def _vocab(board):
    if board is None:
        raise ValueError("An explicit domain vocabulary is required")
    nouns = set(board.nouns)
    ops = {w for w in board.operations if not w.endswith("s")} | set(board.dual_verbs)
    marker_words = {
        w
        for p in (tuple(L.CORRECTIONS) + tuple(L.RETRACTIONS) + L.WRAPPERS + L.COURTESY)
        for w in p.split()
    }
    closed = set()
    for name in (
        "NEGATION",
        "AFFIRMATION",
        "HEDGES",
        "EMPHATIC",
        "BACKCHANNEL",
        "APOLOGY",
        "TROUBLE",
        "FOCUS_PARTICLES",
        "LIGHT_VERBS",
        "TRANSFER_VERBS",
        "OBJECT_PRONOUNS",
        "SINGULAR_PROFORMS",
        "PLURAL_PROFORMS",
        "SELECTOR_PREPOSITIONS",
        "LOCATIVE_PREPOSITIONS",
        "CUT_DETERMINERS",
        "REASON_MARKER_WORDS",
        "DISTINCT",
        "PLURAL_PRONOUNS",
        "SIMILE",
        "ORDINALS",
    ):
        closed.update(str(x).lower() for x in getattr(L, name))
    known = (
        set(L.OBJECT_OPENERS)
        | set(L.GRAMMAR)
        | nouns
        | ops
        | marker_words
        | set(L.AUXILIARIES)
        | set(L.WH_WORDS)
        | set(L.PARTICLES)
        | set(L.FILLED_PAUSE)
        | closed
        | set(board.protected_words)
    )
    return L.OBJECT_OPENERS, nouns, ops, known


def _statuses(board):
    return set(board.statuses)


INDEFINITES = L.INDEFINITES
COPULAS = L.TESTIMONY_COPULAS
NEG_MODALS = L.NEG_MODALS
NEG_DO = L.NEG_DO
_RELATIVIZERS = L.RELATIVIZERS
CONTRACTIONS = L.CONTRACTIONS
OPENERS = L.OPENERS
EVENTS = L.EVENTS
EVENT_PHRASES = L.EVENT_PHRASES

import re
from typing import List, NamedTuple, Tuple


class View(NamedTuple):
    text: str
    back: List[int]
    notices: List[str]
    original: str


class Repair(NamedTuple):
    """What the sim check found. `word` is the repair ONLY when exactly one candidate was
    licensed by its slot; otherwise it is empty and `ask` says why, which is the operator's
    bounce/ask ruling (2026-09-09) made visible instead of silent."""

    word: str
    prints: tuple
    ask: str
    cands: tuple


def _phrase_force(phrase: str) -> str:
    """What a closed phrase DOES — the reason the door may not create one by repair.

    ⇒ It is not decoration in the notice. ROUTE has to ask a question the operator can answer,
      and *"did you mean `forget it`?"* is a different question from *"did you mean to CANCEL
      the previous order?"*. The second is the one that matters.
    """
    from ._english_lexicon import WRAPPERS as _W
    from ._english_lexicon import COURTESY as _C
    from . import _english_lexicon as _sr

    if phrase in set(_sr.RETRACTIONS):
        return f"'{phrase}' cancels what stands"
    if phrase in set(_sr.CORRECTIONS):
        return f"'{phrase}' redirects the request"
    if phrase in set(_W):
        return f"'{phrase}' turns an order into a question"
    if phrase in set(_C):
        return f"'{phrase}' raises the authority asked for"
    return f"'{phrase}' changes the act"


_UNICODE_SPACES = {
    160,
    5760,
    8192,
    8193,
    8194,
    8195,
    8196,
    8197,
    8198,
    8199,
    8200,
    8201,
    8202,
    8239,
    8287,
    12288,
}


def _despace(text: str) -> str:
    """A NON-BREAKING SPACE (and its kin) is a SPACE (2026-09-06). `vm\xa0stop\xa0biggest_vm` is
    what pasting from a web page or a rendered doc gives you — the tokenizer saw one long token and
    the patient was lost. Not the Serpent inventing noise: real people paste. One character for one
    character, so every offset stays byte-exact and this composes with every pass below."""
    if not any((ord(c) in _UNICODE_SPACES for c in text)):
        return text
    return "".join((" " if ord(c) in _UNICODE_SPACES else c for c in text))


def read(request: str, board=None, known=None) -> View:
    """One pass, at the entrance. Clean text returns the identity view. `known` — extra standing
    object NAMES (the world's declared vms/networks) the SEPARATOR pass may treat as closed for
    de-fusing (`db-down` -> `db down`). They are fed ONLY to the separator pass, NEVER to typo
    recognition, so the operator's rule holds: a typo'd name is still the name (`alpah` stays)."""
    _req = str(request)
    text = _despace(_req)
    _folded = sum((1 for a, b in zip(_req, text) if a != b))
    notes_d = (
        [f"folded {_folded} unicode space{('' if _folded == 1 else 's')} to ' '"]
        if _folded
        else []
    )
    edits_s, notes_s = _separator_pass(text, board, known)
    if edits_s:
        text = _apply(text, edits_s)[0]
    edits0, notes0 = _split_pass(text, board, known)
    if edits0:
        text0, back0 = _apply(text, edits0)
        inner = _read_stages(text0, board)
        back = [back0[b] for b in inner.back]
        return View(
            inner.text,
            back,
            notes_d + notes_s + notes0 + inner.notices + _shape_pass(inner.text),
            _req,
        )
    inner = _read_stages(text, board)
    return View(
        inner.text,
        inner.back,
        notes_d + notes_s + inner.notices + _shape_pass(inner.text),
        _req,
    )


def defused(request: str, board=None, known=None) -> str:
    """The SEPARATOR-ONLY view of the original bytes (2026-09-06) — hyphen/underscore fusions of
    KNOWN closed words (and declared standing objects) opened to spaces, and NOTHING else.
    Every separator edit is a single-char swap, so the result is the SAME LENGTH as `request`
    and every offset into it is an offset into the original. That is what makes it safe as the
    RULE LAYER's text: annotate_roles regexes this string while the rows it labels carry ORIGINAL
    offsets, so the two must stay in the same coordinate space. `_split_pass` is deliberately NOT
    run here — it changes length, which would break that correspondence."""
    _req = _despace(str(request))
    edits, _ = _separator_pass(_req, board, known)
    return _apply(_req, edits)[0] if edits else _req


from ._english_lexicon import FUNCTION_WORDS as _FUNCTION_WORDS

_FLAG = re.compile("(?<!\\S)--?[a-z][a-z0-9]*(?:-[a-z0-9]+)*", re.I)


def _shape_pass(text: str):
    """DETECT the code-world shapes; never rewrite them (operator rulings, 2026-09-07).

    A path is already decomposable by its own structure — `/etc/web/temp.cfg` is root -> etc ->
    web -> temp, type cfg — so it only needs to be RECOGNISED; whoever cares about it will take it
    apart, and a wrong path is caught downstream. camelCase, snake_case and a run-on are the same
    kind of thing: conventionally CODE, an identifier whose other side we cannot see. The
    orchestrator is language-independent and code-independent, so splitting one would inject a
    meaning we cannot justify — `getUserName` and `alphaSHOULDbERESTARTEDNOW` are the same shape
    and we genuinely cannot tell them apart. Detecting says what the token IS and leaves the
    decision to a layer that can ask.

    Emits notices only. Byte-identical output, so it composes with every pass and costs no offset.
    """
    out: List[str] = []
    seen = set()
    for tok in text.split():
        t = tok.strip(",;:!?\"'`")
        if len(t) < 3 or t.lower() in seen:
            continue
        if re.match("^[a-z][a-z0-9+.-]*://", t, re.I):
            shape = "a url"
        elif "/" in t or "\\" in t:
            shape = "a path"
        elif re.search("\\.[a-z]{2,4}$", t, re.I) and t.count(".") == 1:
            shape = "a filename"
        elif re.search("[$|]|&&|[a-z]=[^ ]", t, re.I):
            shape = "a shell expression"
        elif re.match("^--?[a-z]", t, re.I):
            shape = "a flag / option"
        elif re.search("[a-z][A-Z]", t):
            shape = "camelCase — an identifier"
        elif re.fullmatch("[a-z0-9]+(?:_[a-z0-9]+)+", t):
            shape = "snake_case — an identifier"
        else:
            continue
        seen.add(t.lower())
        out.append(f"{t!r} looks like {shape} — left whole")
    return out


def _shape_spans(text: str):
    """Char spans of whitespace tokens that are CODE SHAPES — the same set `_shape_pass` names
    (url · path · filename · shell expression · flag · camelCase · snake_case). A repair pass must
    not touch a fragment INSIDE one.

    ⇒ FOUND 2026-09-23 by the marathon re-audit: the tokenizer (`[a-z']+`) splits
      `cach3\\_server` into `cach` + `server`, and stage 3's sim check read `cach` as `each`
      — repairing a fragment of an identifier the door itself declares "left whole" in the very
      same pass. `_shape_pass` ran LAST and only annotated; the shapes now GUARD the repair too.
      Same detection, turned from a notice into a span the repair passes skip.
    """
    spans: List[Tuple[int, int]] = []
    for m in re.finditer("\\S+", text):
        t = m.group(0).strip(",;:!?\"'`")
        if len(t) < 3:
            continue
        if (
            re.match("^[a-z][a-z0-9+.-]*://", t, re.I)
            or "/" in t
            or "\\" in t
            or (re.search("\\.[a-z]{2,4}$", t, re.I) and t.count(".") == 1)
            or re.search("[$|]|&&|[a-z]=[^ ]", t, re.I)
            or re.match("^--?[a-z]", t, re.I)
            or re.search("[a-z][A-Z]", t)
            or re.fullmatch("[a-z0-9]+(?:_[a-z0-9]+)+", t)
        ):
            spans.append((m.start(), m.end()))
    return spans


def _separator_pass(text: str, board=None, known_extra=None):
    """A hyphen or underscore JOINING two KNOWN words (closed-set, or a declared standing object in
    `known_extra`) is a fusion separator, read as a space (`do-not-stop` -> `do not stop`,
    `db-down` -> `db down`). Only a KNOWN-KNOWN pair splits (with the same particle+particle guard
    as `_split_pass`, so `back-up` stays `backup`), so an UNDECLARED name is never broken. A
    single-char replacement keeps every offset byte-exact. Sim-check principle for separators."""
    low = text.lower()
    opaque = _quoted(low)
    opaque = list(opaque) + [(m.start(), m.end()) for m in _FLAG.finditer(low)]
    _openers, _nouns, _ops, known = _vocab(board)
    if known_extra:
        known = known | {str(k).lower() for k in known_extra}
    from ._english_lexicon import PARTICLES as _parts

    edits: List[Tuple[int, int, str]] = []
    notices: List[str] = []
    for m in re.finditer("[a-z0-9']+(?:[-_\\\\+&]+[a-z0-9']+)+", low):
        rs, re_ = (m.start(), m.end())
        if any((qs <= rs and re_ <= qe for qs, qe in opaque)):
            continue
        parts = list(re.finditer("[a-z0-9']+", m.group(0)))
        _kn = sum((1 for _p in parts if _p.group(0) in known))
        _fn = any((_p.group(0) in _FUNCTION_WORDS for _p in parts))
        if parts[-1].group(0).isdigit():
            continue
        for k in range(len(parts) - 1):
            a, b = (parts[k].group(0), parts[k + 1].group(0))
            if a in _parts and b in _parts:
                continue
            if a.isdigit() or b.isdigit():
                continue
            if _kn >= 2 or _fn or (a in known and b in known):
                s0 = rs + parts[k].end()
                e0 = rs + parts[k + 1].start()
                edits.append((s0, e0, " " * (e0 - s0)))
                notices.append(f"read '{a}{text[s0:e0]}{b}' as '{a} {b}'")
    return (edits, notices)


def _split_pass(text: str, board=None, named=None):
    """An UNKNOWN token that splits into two known words is read apart — where the
    grammar votes (the operator's sim-check principle). Exactly one fitting split wins;
    ambiguity or no vote changes nothing (`cancel` never becomes `can cel`).

    ⇒⇒ **BOTH HALVES MUST BE WORDS THE SYSTEM KNOWS** (2026-09-17). Four of the six fit rules
      are asymmetric — they bind ONE half to a closed set and licensed the other from a
      NEIGHBOUR — and the free half was checked against nothing at all:

          a in openers and (b in nouns or nxt in nouns)     # nxt a noun -> b unconstrained
          b in nouns and (prev in openers or a in openers)  # prev an opener -> a unconstrained

      In `stop the X vm` the next token is `vm`, a noun, so EVERY word opening with `an`/`no`/
      `all`/`me` was torn whatever the remainder: `antiseptic` -> `an tiseptic`, `merchants` ->
      `me rchants`, `cabinet` -> `cabi net`. Measured over 6000 sampled dictionary words in that
      one frame: 188 damaged, 3.13%. The operator-visible ones were worse than the rate —
      `stopping` -> `stop ping` turns a status report into TWO operation verbs, `~/.gorgon/...`
      -> `~/.go rgon/...` corrupts a path, and `backer` -> `back` because the split feeds `er`
      to the filled-pause drop and the word is LOST rather than mangled.

    ⇒ THE CONSTRAINT IS THE DOCSTRING'S OWN FIRST LINE, ENFORCED: *two known words*. A closed
      word, or a DECLARED STANDING OBJECT — which is why `named` exists. The name half is what
      the asymmetric rules were FOR (`thedb vm`, `stopalpha`), and the world is the only thing
      that can say whether `db` is a machine. `_separator_pass` has been given the declared
      objects since 2026-09-02; this pass was not, and that asymmetry was the whole defect.

    ⇒ WHEN NOBODY PASSES `named` THE DOOR GETS STRICTER, NOT WRONGER: with no world in hand a
      split must be two closed words, which is rule 2. That is the safe direction — production
      calls `read()` without the lab today ([[gorgon-handover-2026-09-17]] D2), so it simply
      declines splits it cannot justify instead of guessing at them.
    """
    _named = {str(n).lower() for n in named or ()}
    low = text.lower()
    opaque = _quoted(low)
    toks = [
        (w, s, e)
        for w, s, e in _tokens(low)
        if not any((qs <= s and e <= qe for qs, qe in opaque))
    ]
    words = [t[0] for t in toks]
    openers, nouns, ops, known = _vocab(board)
    from ._noise_prints import explain as _expl
    from ._english_lexicon import BOUNDARY_WORDS as BOUNDARIES
    from ._english_lexicon import PARTICLES as _parts

    known = (
        known
        | {b for b in BOUNDARIES if b.isalpha()}
        | {
            "not",
            "no",
            "these",
            "those",
            "this",
            "that",
            "there",
            "their",
            "they",
            "than",
            "have",
            "has",
            "had",
        }
    )
    heads = {"if", "unless", "when", "whenever", "after", "once"}

    def _half(x: str) -> bool:
        """Is this side of the split a word the system knows? A closed word, or a declared
        standing object. Nothing else — a remainder nobody can name is evidence the token was
        never fused in the first place."""
        return x in known or x in _named

    edits, notices = ([], [])
    from ._english_lexicon import FALSE_FUSIONS as _solid

    for idx, (w, s_, e_) in enumerate(toks):
        if len(w) < 4 or "'" in w or w in known or (w in _solid):
            continue
        prev = words[idx - 1] if idx > 0 else None
        nxt = words[idx + 1] if idx + 1 < len(words) else None
        seg_initial = (
            idx == 0
            or prev in {"then", "and", "but"}
            or text[:s_].rstrip()[-1:] in ".;!?"
        )
        fits = []
        for i in range(1, len(w)):
            a, b = (w[:i], w[i:])
            if len(b) < 2:
                continue
            if len(a) == 1:
                fit = a == "a" and b in known
            elif a in known and b in known:
                fit = not (a in _parts and b in _parts)
            elif a in ops and seg_initial:
                fit = _half(b)
            elif a in openers and (b in nouns or nxt in nouns):
                fit = _half(b)
            elif b in nouns and (prev in openers or a in openers):
                fit = _half(a)
            elif a in heads and seg_initial:
                fit = _half(b)
            else:
                fit = False
            if fit:
                fits.append(i)
        if len(fits) == 1:
            if any(
                (
                    (lambda e: e is not None and len(e) == 1)(_expl(v, w))
                    for v in ops
                    if len(v) >= 4
                )
            ):
                continue
            i = fits[0]
            edits.append((s_ + i, s_ + i, " "))
            notices.append(f"read '{w}' as '{w[:i]} {w[i:]}'")
    return (edits, notices)


def _read_stages(request: str, board=None) -> View:
    """Stages 1-3 (pauses · phrase and word typos · comma restore) over one text."""
    text = str(request)
    low = text.lower()
    opaque = _quoted(low)
    toks = [
        (w, s, e)
        for w, s, e in _tokens(low)
        if not any((qs <= s and e <= qe for qs, qe in opaque))
    ]
    protected = _shape_spans(text)
    edits: List[Tuple[int, int, str]] = []
    notices: List[str] = []
    from . import _english_lexicon as _iso

    for w, s, e in toks:
        if w in _iso.FILLED_PAUSE:
            m = re.match("[,\\s]+", low[e:])
            if m:
                e = e + m.end()
            elif s > 0:
                m2 = re.search("[,\\s]+$", low[:s])
                if m2:
                    s = m2.start()
            edits.append((s, e, ""))
            notices.append(f"dropped filled pause '{w}'")
    from . import _english_lexicon as _sr
    from ._english_lexicon import WRAPPERS
    from ._english_lexicon import COURTESY

    phrases = [
        p.split()
        for p in tuple(_sr.CORRECTIONS) + tuple(_sr.RETRACTIONS) + WRAPPERS + COURTESY
        if len(p.split()) >= 2
    ]
    taken = [(s, e) for s, e, _ in edits] + protected
    for pwords in phrases:
        for i in range(len(toks) - len(pwords) + 1):
            window = toks[i : i + len(pwords)]
            if all((w == pw for (w, _s, _e), pw in zip(window, pwords))):
                taken.append((window[0][1], window[-1][2]))
    _, _, _, _known = _vocab(board)
    from ._english_lexicon import FALSE_TYPOS as _FALSE_TYPOS

    _cands_at = {}
    for pwords in phrases:
        for i in range(len(toks) - len(pwords) + 1):
            window = toks[i : i + len(pwords)]
            fuzzy = None
            for (w, s, e), pw in zip(window, pwords):
                if w == pw:
                    continue
                if (
                    fuzzy is None
                    and len(w) >= 4
                    and (len(pw) >= 4)
                    and (w not in _known)
                    and (w not in _FALSE_TYPOS)
                    and _damerau1(w, pw)
                ):
                    fuzzy = (w, s, e, pw)
                else:
                    fuzzy = False
                    break
            if not fuzzy:
                continue
            w, s, e, pw = fuzzy
            if any((not (e <= ts or te <= s) for ts, te in taken)):
                continue
            _cands_at.setdefault((s, e), (w, [], []))[1].append(" ".join(pwords))
            _cands_at[s, e][2].append((window[0][1], window[-1][2]))
    for (s, e), (w, phs, _spans) in sorted(_cands_at.items()):
        _seen, _uniq = (set(), [])
        for ph in phs:
            if ph not in _seen:
                _seen.add(ph)
                _uniq.append(ph)
        notices.append(
            f"could not apply '{w}' here — it is one edit from {' or '.join((repr(x) for x in _uniq))}, and that would change what the request does ({'; '.join((_phrase_force(x) for x in _uniq))}); ask"
        )
    taken2 = [(s_, e_) for s_, e_, _ in edits] + list(_cands_at) + protected
    for w, s_, e_ in toks:
        if len(w) < 4 or "'" in w:
            continue
        if any((not (e_ <= ts or te <= s_) for ts, te in taken2)):
            continue
        got = _recognise(w, toks, s_, board)
        if got.word:
            taken2.append((s_, e_))
            edits.append((s_, e_, got.word))
            _why = " + ".join(got.prints) if got.prints else "exact"
            notices.append(f"read '{w}' as '{got.word}' ({_why})")
        elif got.ask == "ambiguous":
            notices.append(
                f"could not read '{w}' — it fits {' and '.join(got.cands)} equally; ask"
            )
        elif got.ask == "unlicensed":
            notices.append(
                f"could not read '{w}' here — it looks like {' or '.join(got.cands)}, but nothing in this slot licenses the repair; ask"
            )
    if edits:
        mid, back1 = _apply(text, edits)
    else:
        mid, back1 = (text, list(range(len(text) + 1)))
    _mute = [sp for _k, (_w, _p, sps) in _cands_at.items() for sp in sps]
    cuts = [
        c
        for c in merge_cut_points(mid, board)
        if not any((a < c < b for a, b in _mute))
    ]
    if not cuts:
        return View(mid, back1, notices, text)
    edits2 = []
    for at in cuts:
        if 0 < at <= len(mid) and mid[at - 1] == " ":
            edits2.append((at - 1, at, ", "))
        elif at < len(mid) and mid[at] == " ":
            edits2.append((at, at + 1, ", "))
        else:
            edits2.append((at, at, ", "))
        word = mid[at:].split()[0] if mid[at:].split() else ""
        notices.append(f"read a clause break before '{word}'")
    new, back2 = _apply(mid, edits2)
    back = [back1[b] for b in back2]
    return View(new, back, notices, text)


def _recognise(w, toks, at, board):
    """The sim check. Each closed-set candidate is tried in its slot; the grammar votes.

    opener  -> the next word is a noun (`eveyr vm` -> every; `did you eveyr stop` -> no)
    pronoun -> the previous word is an operation verb (`put thrm` -> them)
    verb    -> clause-initial position (`then launhc beta` -> launch)
    noun    -> an opener stands within the two words before it (`the dmz netwrk`)
    Exactly one fitting candidate wins; ties and no-fits change nothing.
    """
    openers, nouns, ops, known = _vocab(board)
    states = _statuses(board)
    from ._english_lexicon import FALSE_PRINTS as _english

    if w in known or w in _english:
        return Repair("", (), "", ())
    words = [t[0] for t in toks]
    i = next((j for j, t in enumerate(toks) if t[1] == at))
    prev = words[i - 1] if i > 0 else None
    nxt = words[i + 1] if i + 1 < len(words) else None
    _PRONOUNS = {"it", "them", "me", "us", "one", "ones", "everything"}
    _COPULAS = {"is", "are", "was", "were", "be", "been"}
    from ._noise_prints import explain as _explain

    _DUALS = board.dual_verbs
    fits = {}
    explained = {}
    for cand in openers | nouns | ops | states:
        if len(cand) < 4 and cand not in _PRONOUNS:
            continue
        _prints = _explain(cand, w)
        if not _prints:
            continue
        explained[cand] = _prints
        if cand in _PRONOUNS:
            if prev in ops:
                fits[cand] = _prints
        elif cand in states:
            from ._english_lexicon import CUT_DETERMINERS as _DETS

            if (
                any((words[j] in _COPULAS for j in range(max(0, i - 3), i)))
                and prev not in _DETS
            ):
                fits[cand] = _prints
            elif nxt in nouns:
                fits[cand] = _prints
        elif cand in openers:
            if nxt in nouns:
                fits[cand] = _prints
        elif cand in nouns and cand not in _DUALS:
            if prev in openers or (i >= 2 and words[i - 2] in openers):
                fits[cand] = _prints
        elif cand in ops or cand in _DUALS:
            if i == 0 or prev in {"then", "and", "but"}:
                fits[cand] = _prints
            else:
                from ._english_lexicon import AUXILIARIES as _AUXQ
                from ._english_lexicon import SUBJECT_PRONOUNS as _SUBJQ

                if words and words[0] in _AUXQ and (prev in _SUBJQ):
                    fits[cand] = _prints
                elif cand in _DUALS and (
                    prev in openers or (i >= 2 and words[i - 2] in openers)
                ):
                    fits[cand] = _prints
    _unlic = tuple(
        sorted((c for c in explained if c not in fits and len(explained[c]) <= 1))
    )
    if not fits:
        return Repair("", (), "unlicensed" if _unlic else "", _unlic)
    _least = min((len(v) for v in fits.values()))
    if _least > 1:
        return Repair("", (), "", ())
    _best = [(c, pr) for c, pr in fits.items() if len(pr) == _least]
    if len(_best) == 2:
        _c1, _c2 = sorted((c for c, _ in _best))
        if _c2 == _c1 + "s":
            _sing = {"is", "was"} & set(words)
            _plur = {"are", "were"} & set(words)
            if _sing and (not _plur):
                _best = [(c, pr) for c, pr in _best if c == _c1]
            elif _plur and (not _sing):
                _best = [(c, pr) for c, pr in _best if c == _c2]
    if len(_best) != 1:
        return Repair("", (), "ambiguous", tuple(sorted((c for c, _ in _best))))
    return Repair(_best[0][0], _best[0][1], "", ())


def _tokens(low: str):
    return [(m.group(0), m.start(), m.end()) for m in re.finditer("[a-z']+", low)]


def _quoted(low: str):
    """Quoted regions are opaque. The lookarounds keep apostrophes (don't) out of it."""
    spans = [
        (m.start(), m.end()) for m in re.finditer("(?<![a-z])'[^']*'(?![a-z])", low)
    ]
    spans += [(m.start(), m.end()) for m in re.finditer('"[^"]*"', low)]
    spans += [(m.start(), m.end()) for m in re.finditer("`[^`]*`", low)]
    return spans


def _damerau1(a: str, b: str) -> bool:
    """Exactly one substitution, adjacent transposition, insertion or deletion."""
    if a == b:
        return False
    la, lb = (len(a), len(b))
    if la == lb:
        diffs = [i for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            return True
        return (
            len(diffs) == 2
            and diffs[1] == diffs[0] + 1
            and (a[diffs[0]] == b[diffs[1]])
            and (a[diffs[1]] == b[diffs[0]])
        )
    if abs(la - lb) != 1:
        return False
    if la > lb:
        a, b, la = (b, a, lb)
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1 :]


def _apply(text: str, edits: List[Tuple[int, int, str]]):
    """Apply non-overlapping edits; back[i] = original offset of view char i."""
    edits = sorted(edits)
    out: List[str] = []
    back: List[int] = []
    at = 0
    for s, e, rep in edits:
        out.append(text[at:s])
        back.extend(range(at, s))
        out.append(rep)
        back.extend((s + min(k, max(e - s - 1, 0)) for k in range(len(rep))))
        at = e
    out.append(text[at:])
    back.extend(range(at, len(text)))
    back.append(len(text))
    return ("".join(out), back)


def _outside_quotes(text: str, pat: str):
    """Every match of `pat` in `text` that is NOT inside a quotation.

    ⇒ QUOTES ARE OPAQUE — the law `_first_cut` states and keeps — but the ROUGH mark split did
      not, so a clause mark inside a pasted command tore the citation in half before any clause
      rule could see it: `run the command 'svn revert --recursive .'` split at the period and the
      quote never closed (marathon Class A, 2026-09-06). Same marks, same order; only the quoted
      regions are skipped, so a request with no punctuation inside quotes is unaffected.
    """
    import re as _re

    opaque = _quoted(text.lower())
    for m in _re.finditer(pat, text):
        if any((qs <= m.start() and m.end() <= qe for qs, qe in opaque)):
            continue
        yield m


def merge_cut_points(request: str, board) -> List[int]:
    """Absolute offsets where a clause break belongs but no punctuation exists.

    ⇒ N3 (operator-approved): the front door RESTORES the missing comma at these
      offsets, so pass 1's span walk — and every other reader — sees the boundary the
      splitter already knows about. One copy of the rules (`_first_cut`); this walk
      only maps them to request offsets.
    """
    import re as _re

    pts: List[int] = []
    seps = sorted(
        [_re.escape(m) for m in CLAUSE_MARKS] + [_re.escape(w) for w in CLAUSE_WORDS],
        key=len,
        reverse=True,
    )
    at = 0
    segments = []
    for m in _outside_quotes(request, "|".join(seps)):
        segments.append((at, m.start()))
        at = m.end()
    segments.append((at, len(request)))

    def rec(s_: int, e_: int) -> None:
        piece = request[s_:e_]
        cut = _first_cut(piece, board)
        if cut is None:
            return
        left, right = (piece[:cut].strip(" ,"), piece[cut:].strip(" ,"))
        if not left or not right:
            return
        pts.append(s_ + cut)
        rec(s_, s_ + cut)
        rec(s_ + cut, e_)

    for s_, e_ in segments:
        rec(s_, e_)
    return sorted(pts)


def _first_cut(piece: str, board):
    """Where the missing comma would have been — the CLAUSE MERGE, priced 2026-08-19.

    Without punctuation *"if alpha is stopped launch it"* stays ONE clause: is_condition
    withholds the whole thing from pass 2, the imperative channel fails (it opens on
    `if`), and the second span's attachment goes with it — no-punct owned 7 lost spans,
    4 lost acts, 10 lost attachments on the certified v2 run, plus both voice residuals.

    Every cut is grammar from a closed class that already exists, never meaning:
      1 a leading COURTESY literal ends where the literal ends
      2 a mid-clause WRAPPER literal (`tell me …`) starts its own clause
      3 `anyway` releases what stands behind it
      4 a mid-clause condition head ({if, unless} ∪ EVENTS, whether-`if` guarded) opens
        a subordinate — cut in front of it
      5 a piece-initial condition head's subordinate ends after its PREDICATE, at the
        first determiner-shaped imperative (`… is stopped ▸ launch it`); before the
        predicate has been seen, nothing cuts — a long subject cannot fake it
      6 a second imperative (a base-form operation word taking a determiner object)
        is its own clause (`don't stop the web vm ▸ stop the db vm`)
      8 a GOAL head (`make sure`, `ensure`, `verify that` — ACHIEVE_MARKERS) takes a
        CLAUSE, not an object: the noun phrase after it is a SUBJECT and the first
        base-form op word after that is its PREDICATE, not a second imperative — rule 5's
        discipline, extended. A CUT MUST NOT SPLIT A NOUN PHRASE FROM THE PREDICATE THAT
        RESTRICTS IT: `exactly 3 vms ▸ carry the 'prod' label` lost `label=prod` and
        became `count(vm)=3` — the DELETION shape (language benchmark rung 7, 08-22).
        Once that predicate is seen, a later imperative cuts as before.
    Quotes are opaque. A piece none of this touches returns whole — fail closed.
    Deliberately NOT here: bare-name lists without commas (scan's NP reading) and value
    respeaks without commas (self_repair's) — named out of scope, not forgotten.
    """
    import re as _re

    text = piece
    low = text.lower()
    if not low.strip():
        return None
    opaque = _quoted(low)
    toks = [
        (m.group(0), m.start(), m.end())
        for m in _re.finditer("[a-z']+", low)
        if not any((qs <= m.start() and m.end() <= qe for qs, qe in opaque))
    ]
    if len(toks) < 3:
        return None
    words = [t[0] for t in toks]
    from ._english_lexicon import COURTESY
    from ._english_lexicon import WRAPPERS
    from ._english_lexicon import AUXILIARIES
    from . import _english_lexicon as _iso
    from . import _english_lexicon as _T
    from ._english_lexicon import GRAMMAR

    NON_VERB_SEGMENTS = board.non_verbs
    for phrase in COURTESY:
        if low.strip().startswith(phrase) and len(low.strip()) > len(phrase):
            return low.find(phrase) + len(phrase)
    from ._english_lexicon import WH_WORDS as _WH

    if words[0] in AUXILIARIES or (words[0] in _WH and (not is_condition(text))):
        return None
    for phrase in WRAPPERS:
        at = low.find(f" {phrase}")
        if at > 0 and (not any((qs <= at < qe for qs, qe in opaque))):
            return at + 1
    for i, (w, s, e) in enumerate(toks):
        if w == "anyway":
            if i > 0:
                return s
            if len(toks) > 1:
                return e
    from ._english_lexicon import NAMING_CUES as _NC

    heads = {"if", "unless"} | set(_T.EVENTS)
    for i in range(1, len(toks)):
        w, s, _e = toks[i]
        if w in heads and words[i - 1] in _NC:
            continue
        if w in heads and (not (w == "if" and words[i - 1] in _iso.WHETHER_HOSTS)):
            cut = toks[i - 1][1] if words[i - 1] in _iso.FOCUS_PARTICLES else s
            if cut > 0:
                return cut
    from ._english_lexicon import ACHIEVE_MARKERS

    goal_headed = any((low.lstrip().startswith(m) for m in ACHIEVE_MARKERS))
    conditioned = (
        words[0] in {"if", "unless", "when", "whenever"} | set(_T.EVENTS) or goal_headed
    )
    _DUAL = board.dual_verbs
    base_ops = {
        w for w in board.operations if not w.endswith("s") and w not in GRAMMAR
    } | set(_DUAL)
    predicate_seen = False
    for i in range(1, len(toks) - 1):
        w, s, _e = toks[i]
        prev, nxt = (words[i - 1], words[i + 1])
        if w in AUXILIARIES or (
            w.endswith("s") and w not in GRAMMAR and (w not in NON_VERB_SEGMENTS)
        ):
            predicate_seen = True
            continue
        if (
            conditioned
            and (not predicate_seen)
            and (w in base_ops)
            and (nxt in _CUT_DETS)
            and (prev not in _CUT_NEG)
            and (prev not in AUXILIARIES)
        ):
            predicate_seen = True
            continue
        if (
            nxt in _CUT_DETS
            and w not in GRAMMAR
            and (w not in _CUT_DETS)
            and (w not in _CUT_NEG)
            and (not w.endswith(("ing", "s")))
            and (prev not in AUXILIARIES)
            and (prev not in _CUT_DETS)
            and (prev not in _CUT_NEG)
            and (prev != "to")
            and (conditioned and predicate_seen or (not conditioned and w in base_ops))
        ):
            return s
    pe = predicate_end(text, board)
    if pe and pe < len(text) and (len(text[pe:].split()) >= 3):
        return pe
    return None


def predicate_end(clause: str, board) -> Optional[int]:
    """The CHAR offset right after a testimony predicate's structural end, or None.

    ⇒ For the CUT RULES (pass2 rule 7, the D1-exposed no-comma cell): a testimony
      predicate has a computable end for the closed shapes — negated copula + gerund
      (`is not working` ▸), negated modal/do + verb (`won't start` ▸), the indefinite
      frame's head (`something is wrong` ▸ before its with-phrase). What follows can
      then be released as the elaboration. None when no shape matches — no vote.
    """
    import re as _re

    toks = [
        (m.group(0).lower(), m.start(), m.end())
        for m in _re.finditer("[\\w:']+", str(clause))
    ]
    words = [t[0] for t in toks]
    if len(words) >= 3 and words[0] in INDEFINITES and (words[1] in COPULAS):
        if "with" not in words:
            return None
        nouns = board.nouns
        w_at = words.index("with")
        for j in range(w_at + 1, len(words)):
            if words[j] in nouns:
                return toks[j][2]
        return None
    for at, word in enumerate(words):
        if at == 0:
            continue
        if any((w in _RELATIVIZERS for w in words[:at])):
            return None
        negated_copula = (
            word in COPULAS
            and at + 1 < len(words)
            and (words[at + 1] in ("not", "never"))
        )
        if word in NEG_MODALS or word in NEG_DO or negated_copula:
            head_at = at + (2 if negated_copula else 1)
            if head_at >= len(words):
                return None
            if negated_copula and (not words[head_at].endswith("ing")):
                return None
            if not negated_copula:
                if words[head_at] not in {
                    w for w in board.operations if not w.endswith("s")
                }:
                    return None
            return toks[head_at][2]
    return None


def words_of(clause: str) -> List[str]:
    """The clause as tokens, with auxiliary contractions expanded so POSITION can be read."""
    import re

    out: List[str] = []
    for raw in re.findall("[a-z][a-z0-9']*|[0-9]+", str(clause).lower()):
        token = raw.strip("'")
        if not token:
            continue
        out.extend(CONTRACTIONS.get(raw, CONTRACTIONS.get(token, (token,))))
    return out


def _after_openers(words: Sequence[str]) -> List[str]:
    """Drop leading particles that carry no proposition — `please`, `and`, `so`, `ok`."""
    i = 0
    while i < len(words) and words[i] in OPENERS:
        i += 1
    return list(words[i:])


def is_condition(segment: str) -> bool:
    """Does this segment state a CONDITION on another act rather than an act of its own?

    ⇒⇒ **A CONDITION IS NOT A SECOND DIALOGUE ACT, AND READING IT AS ONE IS THE DEFECT THIS
      WHOLE AREA KEEPS PRODUCING.** *"whenever a vm stops, take a snapshot"* is ONE Instruct
      held conditionally; the first cut of `annotate` emitted TWO Instructs, because
      `speech_act` reads the condition clause as directive-act — it carries `stops`, which is
      a manifest verb.
    ⇒ **SO THE TEST IS POSITIONAL AND NOT SEMANTIC:** a segment that OPENS on a subordinator
      hangs off another. The same bound that stopped `if alpha is stopped` reading as teaching,
      one layer out — and `SUBORDINATING` and `temporal.EVENTS` are both already declared.
    """
    from . import _english_lexicon as SA
    from . import _english_lexicon as T

    low = str(segment).lower().strip()
    for phrase in T.STANDING:
        if low.startswith(phrase):
            low = low[len(phrase) :].strip(" ,")
    head = _after_openers(words_of(low))
    if not head:
        return False
    first = head[0]
    return (
        first in {"if", "unless"}
        or first in T.EVENTS
        or first in {"whenever"}
        or (first == "when" and events_in(low, SA))
        or any((low.startswith(p) for p in T.ALWAYS_STANDING_PHRASES))
    )


def _words(text: str) -> Tuple[str, ...]:
    """Tokens, with a number glued to a unit kept whole — `9pm` is one word, not nine and pm."""
    return tuple(
        re.findall("[a-z][a-z0-9_']*|[0-9]+[a-z:.]*[a-z0-9]*|[0-9]+", str(text).lower())
    )


def events_in(text: str, speech_act=None) -> bool:
    """Does something HAPPENING start this? The world-called half.

    ⇒ ⚠ **`when` IS ADMITTED ONLY AS AN ADJUNCT**, never as the interrogative. *"when did you
      stop it"* is inverted over the addressee and asks about the past; *"when a vm stops"* has
      a subject and no inversion, and is a condition. The same pair cost a defect on 2026-08-16
      read the other way round, so the test is written from that finding rather than from the
      word.
    """
    low = f" {str(text).lower()} "
    if any((f" {p} " in low for p in EVENT_PHRASES)):
        return True
    words = _words(text)
    for i, w in enumerate(words):
        if w in EVENTS:
            return True
        if w == "when" and i + 2 < len(words):
            if speech_act is None:
                continue
            if words[i + 1] not in speech_act.AUXILIARIES:
                return True
    return False
