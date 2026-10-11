Question roles, grounding policy and fresh sets 10–12
====================================================

RuleAssigner version 6 adds two bounded repairs. C018 accepts a complete passive
question surface (BE + patient NP + optional not + VBN + by + agent NP + ?)
when the parser labels the participle acl under the auxiliary's subject. It
requires complete noun chunks, exact order and no unexplained intervening text.
Relative clauses with another predicate remain unresolved. C019 repairs two
object labels for explicitly declared dative-alternation verbs using recipient
then patient order and contiguous full noun phrases. Source text is unchanged.

Saved development results
-------------------------

The unchanged 1,087 reference cases improve from 942 to 1,087 correct proposals:
C019 contributes one observed flip, C018 contributes 144. No regressions or wrong
code proposals remain in that replay. The older 600-case development set improves
from 387 to 396, with nine flips and no regressions; 204 still abstain. These are
reused development results, not fresh accuracy. All individual ticks are stored
in evidence/question-role-fix-2. Earlier captures remain immutable.

Fresh confirmation within limited grammar
-----------------------------------------

The canonical generator pool was exhausted. Rather than relabel old cases fresh,
a frozen external recipe uses unchanged Serpent simple_clause constructors and
existing vocabulary with disjoint verb/patient bindings. Sets 10, 11 and 12 each
select 300 cases from a 576-case pool with the existing balanced planner. No
Kobra predictions affect selection. Prior normalized inputs are excluded.
This is a new lexical-binding inventory, not a matched-distribution comparison,
new vocabulary holdout or broader real-work test. Serpent core was not changed.

All Kobra modules, tools, adapter, scorer and recipe were hashed before generation.
The reader received source text only. Frozen gold and teacher context metadata
were loaded after capture. Three audits recomputed scores and verified frozen
source/reference hashes; all sets share source and parser hashes. There are 900
unique inputs, disjoint from previous sets 1–9.

* Set 10: 300/300 correct (100%), zero wrong, zero unresolved.
* Set 11: 300/300 correct (100%), zero wrong, zero unresolved.
* Set 12: 299/300 correct (99.67%), zero wrong, one unresolved.
* Combined: 899/900 correct (99.89%); raw retention 900/900 by design.

No generative model was called. spaCy remains a learned dependency parser.
All three sets exceed 97.5% under the existing literal-slot scorer. This does
not establish complete semantic accuracy, tense representation, workflow
coverage, archive/library/ledger grounding accuracy or correct ASK rates.
All final routes remain ASK because held-out calibration has not been installed.
These final ASK routes are not counted as correct ambiguity deflections.

The sole unresolved case is "Is the key moved by Mira?". spaCy labels key as
amod under moved and moved as attr under Is, giving C018 no qualifying subject
or acl edge. It safely abstains. This is a parsing coverage gap, not missing
WORLD answer facts. The fresh run is preserved without a post-test repair.
C018 covers 114 correct fresh cases; this is coverage, not causal ablation.
C019 has no fresh examples in the voice/tense-only recipe.

Grounding authority
-------------------

GatedRuleReader now blocks model fallback before invocation for explicit missing
context, unresolved local references, unbound reference cues, stale/conflicting
knowledge and ambiguous lexical mentions. It strips model identity fields and
requires independently supported deterministic bindings. Existing code-generated
local links remain valid. Grammar-only model fallback remains available.
Parsing a question about Mira does not require answering it or proving a WORLD
fact. The source retains names as mentions when identity lookup is unnecessary.

This boundary is not a complete discourse resolver. General previous-turn,
participant and ordinal binding remain incomplete; quoted reference words and
complement "that" conservatively block unresolved grammar fallback. Direct
ConfidenceGate.assess remains a trusted caller API for supplied bindings. Exact
knowledge lookup relies on caller-provided snapshots; persistence, refresh,
archive ratification and an ASK conversation loop are still separate work.

Nine focused policy tests pass. The full suite ran 238 tests: 237 passed and one
optional-jsonschema test skipped. Existing compatibility tests now assert early
ASK before model invocation where ambiguity is already known.

Artifacts
---------

reports/read-sets-010-012.html contains results, limitations, all 145 development
flips, all 900 fresh parses and the unresolved case with expected slots.
evidence/read300/series-010-012 contains aggregate JSON, failures and its report
builder. Per-set artifacts contain frozen gold, captures, source snapshots and
audits. evidence/question-role-fix-2 contains both development replays and the
reader freeze manifest. No server is needed to open the report.
