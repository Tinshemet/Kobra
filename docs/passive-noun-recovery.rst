Remaining passive-question recovery (C020)
==========================================

The one unresolved fresh case, "Is the key moved by Mira?", had a different
parser error from C018: Is was ROOT, moved was attr under Is, and key was a NOUN
labeled amod under moved. The parser supplied no patient noun chunk.

RuleAssigner version 7 recognizes this bounded variant. It requires no existing
subject, one VBN lexical predicate attached as attr to BE, a two-token a/an/the
plus NOUN phrase, the exact det/amod attachment pattern, an explicit by-agent,
and the complete passive-question surface with no extra clauses or leftover
material. It reconstructs the patient span directly from the unchanged source.
It does not hardcode key, moved, Mira, or the complete sentence. It does not
promote general attribute complements or infer an answer from WORLD.

Output: act question, predicate moved, agent Mira, patient the key. Other slots
are NONE. The semantic_verified flag remains false; final routing still requires
external calibration and currently remains ASK.

Verification
------------

Three added tests cover the observed case, nearby unsupported shapes, and
controlled parser-error fixtures with different vocabulary. Full suite: 241 run,
240 passed, one optional-jsonschema skip. Paired replay across 2,587 saved cases:

* Sets 10–12: 899 to 900 correct; one flip, no wrong proposals or unresolved cases.
* Sets 6–9: 1,087 correct unchanged; no regressions.
* Older 600: 396 correct unchanged; 204 unresolved, no wrong proposals.

There were zero regressions and no generative AI calls. These are development
replays after inspecting the failure. The original fresh score remains 899/900
(99.89%); no fresh 100% claim is made. Original captures and reports are unchanged.

Why the previous gain was large
------------------------------

144 of the 145 unresolved cases in the saved 1,087 shared one parser pattern;
C018 fixed that pattern once. C019 fixed the remaining double-object assignment.
The next fresh sets used new lexical combinations within the same voice/tense
construction, with an explicit frozen recipe and independent Serpent gold. They
were not broad new workflow tests or a matched-distribution comparison with the
previous inventory. Thus the measured improvement reflects repaired grammar
coverage, not a demonstrated jump in general language or memory-grounding ability.

Evidence: evidence/passive-noun-recovery-1. Reproduce into a new output directory
using the recorded replay tool and baseline hashes. The new HTML report is
reports/read-passive-noun-recovery.html; it keeps this replay distinct from the
original fresh-set report.
