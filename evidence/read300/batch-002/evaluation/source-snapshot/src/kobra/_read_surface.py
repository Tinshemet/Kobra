"""Preserved READ noun-anchor and reason-clause rules, with client-supplied nouns.

These are fallible linguistic observations, not resolved facts or instructions.
Source and modifications are recorded in evidence/read-surface-provenance.json.
"""

import re
from typing import List, NamedTuple
from . import _english_lexicon as L

_CAUSE = L.REASON_CAUSE
_CONCESSION = L.REASON_CONCESSION
_PURPOSE_SO = L.REASON_PURPOSE_SO
_TRANSFER = L.TRANSFER_VERBS
_DETS = set(L.DEFINITE) | set(L.INDEFINITE) | set(L.CUT_DETERMINERS)
_PRONOUNS = L.OBJECT_PRONOUNS


class Reason(NamedTuple):
    family: str  # cause · concession · purpose
    span: str  # the evidence bytes, by the certified span convention
    start: int
    end: int


def _tail(text: str, at: int) -> str:
    out = text[at:].strip()
    return out.rstrip(".!?,;").strip()


def reasons_in(sentence: str, nouns: frozenset[str]) -> List[Reason]:
    """Every reason clause in the sentence, at its offsets. Deterministic, marker-driven."""
    low = sentence.lower()
    out: List[Reason] = []
    taken: List[tuple] = []

    def _claim(start: int, end: int) -> bool:
        if any(s < end and start < e for s, e in taken):
            return False
        taken.append((start, end))
        return True

    for fam, markers, keep in (
        ("concession", _CONCESSION, False),
        ("cause", _CAUSE, False),
        ("purpose", _PURPOSE_SO, True),
    ):
        for m in markers:
            for hit in re.finditer(r"(?<![\w])%s\b" % re.escape(m), low):
                body = _tail(sentence, hit.end())
                if not body or len(body.split()) < 2:
                    continue  # `so` needs a clause, not a particle
                start = (
                    hit.start()
                    if keep
                    else hit.end()
                    + (len(sentence[hit.end() :]) - len(sentence[hit.end() :].lstrip()))
                )
                span = sentence[hit.start() :].strip().rstrip(".!?,;") if keep else body
                if _claim(hit.start(), hit.start() + len(span)):
                    out.append(
                        Reason(
                            fam,
                            span,
                            start if not keep else hit.start(),
                            (start if not keep else hit.start()) + len(span),
                        )
                    )
    # the infinitival purpose — `to` + a bare non-thing word, never a transfer's argument
    for hit in re.finditer(r"(?<![\w])to\s+([a-z][\w-]*)", low):
        head = hit.group(1)
        if (
            head in _DETS
            or head in _PRONOUNS
            or head in nouns
            or head.isdigit()
            or re.fullmatch(r"\d+[a-z]*", head)
        ):
            continue
        before = low[: hit.start()].split()
        if any(w in _TRANSFER for w in before[-3:]):
            continue  # `move it to …` — the verb's argument
        body = _tail(sentence, hit.start())
        if len(body.split()) < 3:
            continue  # `to free` alone is not a stated reason
        if _claim(hit.start(), hit.start() + len(body)):
            out.append(Reason("purpose", body, hit.start(), hit.start() + len(body)))
    return sorted(out, key=lambda r: r.start)


def anchors_in(request: str, nouns: frozenset[str]) -> List[str]:
    """EVERY DECLARED NOUN THE REQUEST USES — anchors found without asking anyone.

    ⇒ The naming question returns paraphrases: *"make sure there are exactly two machines
      left"* came back as `sentence` / `things` / `group`, none of which are IN the request, so
      nothing could be scanned and the whole reading was empty. But the manifest already lists
      the words that name a thing, so the anchors can be READ.

    The model is still needed for what the manifest cannot list — a pronoun-headed set like
    *"the ones that do not answer"* — so its answers are added to these, never replaced by them.

    ⇒⇒ ⚠ **A DECLARED NOUN MAY BE MORE THAN ONE WORD, AND THIS SCANNED SINGLE TOKENS.** The
      manifest declares `restore point`, `hardware profile` and `golden image`, and none of the
      three could ever be found — `[\\w']+` cannot match across a space. `_kind_of` was written
      for exactly this case and says so in its own docstring — *"longest noun wins, 'restore
      point' before 'point'"* — and **that branch was unreachable from here**, which is the
      built-and-never-called defect in its purest form.

      What it cost, on the manifest we ship:
        *"delete every restore point older than a week"*   -> ZERO anchors. Read as NOTHING.
        *"clone the golden image into 3 vms"*              -> template `identity = image`,
                                                              so the template is CALLED image
      The first is a destructive request that reads as empty; the second is a confidently
      wrong name. Neither reports a problem.

    ⇒ **LONGEST WINS, AND ONE PASS DOES IT.** The alternation is sorted longest-first and
      Python's `|` is leftmost-first, so `golden image` is claimed whole and the `image` inside
      it is never offered a second time. Request order is preserved because `finditer` walks
      left to right — the clause split downstream depends on it.
    """
    if not nouns:
        return []
    low = request.lower()
    pattern = re.compile(
        r"(?<![\w'])("
        + "|".join(re.escape(n) for n in sorted(nouns, key=len, reverse=True))
        + r")(?![\w'])"
    )
    found: List[str] = []
    for match in pattern.finditer(low):
        word = match.group(1)
        if word not in found:
            found.append(word)
    return found
