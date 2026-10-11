Passive question false-success correction
========================================

C017 (RuleAssigner version 5) fixes the four incorrect code-routed interpretations
in fresh sets 006–009. In those parses the predicate was VBN with a be auxiliary
and an explicit by-agent, but spaCy used aux/nsubj rather than auxpass/nsubjpass.
The old detector treated the surface subject as agent and silently ignored the
recognized by-agent. The new bounded alternative recognizes the combined evidence
in questions. A recognized agent attachment without supported passive evidence
now causes abstention instead of being discarded.

Example: "Are the servers checked by Alex?" now produces predicate checked,
agent Alex, patient the servers and act question. Negation remains not when present.
No sentence, person or domain name is hardcoded. Active perfect questions are not
reversed; by-location phrases are not treated as passive agents.

The design follows the agent/passive distinctions documented by UD:
https://universaldependencies.org/u/dep/obl-agent.html
https://universaldependencies.org/u/dep/aux-pass.html
Reviewed 2026-10-11. Actual spaCy labels differ from UD spelling; this is a targeted
repair over observed parser output, not a full UD parser or universal passive rule.
The alternative of broadly promoting every participial noun modifier to a verb
was not used: that would also change unresolved relative/reduced clauses and
needs its own scope checks.

Verification and remaining categories
------------------------------------

Replaying the unchanged 1,087 references after inspecting their failures yields
942 correct code interpretations, zero wrong and 145 unresolved. Four prior wrong
cases become correct; no prior correct cases regress. The older 600-case paired
replay retains its 387 correct code-routed cases without regression. Both replays
are development evidence, not fresh confirmation. Original captures are unchanged.
The gate remains uncalibrated; no live AI was called and all final outcomes remain
ASK. Five regression tests cover observed errors and nearby constructions.

Remaining unresolved cases:

* Present affirmative passive questions: 41.
* Present negative passive questions: 34.
* Past affirmative passive questions: 37.
* Past negative passive questions: 32.
* Recipient/patient ambiguity: 1 ("Alex shows Mira a key.").

All 144 passive cases share one observed parse pattern: be is ROOT, the subject
is nsubj, and the lexical participle attaches to that subject as acl. The simple
reader's additional-lexical-verb guard therefore abstains. Tense and negation are
subcategories, not four independent bugs. In the remaining case, Mira and a key
are both tagged dobj; assigning their semantic roles requires another rule.
These unresolved cases have not been silently repaired or counted as correct.

reports/read-passive-fix.html contains all corrected frames and all unresolved
sentences grouped by category. evidence/passive-question-fix-1/unresolved.csv is
the same complete list in tabular form. The source ledger remains intact.
