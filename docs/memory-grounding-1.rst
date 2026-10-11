Deterministic memory grounding: first implemented contract
=========================================================

READ can now bind a pronoun from a client-confirmed ledger reference without
asking a model to choose identity. This is a bounded integration contract, not
unrestricted natural-language discourse resolution or persistent memory storage.

Authority and data flow
-----------------------

The client supplies exact prior turns, current WORLD/library entity records and
context_claims. A reference claim extends the existing ledger claim with reference
and entity_id. For example, prior turn t1 contains "box" and the client records:

    {"id":"c1", "turn_id":"t1", "start":0, "end":3, "quote":"box",
     "status":"confirmed_by_client", "reference":"it", "entity_id":"box-1"}

With current entity box-1 {name: box, number: singular}, "Move it." keeps patient
"it" in the frame and gains groundings {it: box-1}. memory_evidence records the
claim IDs, exact prior spans, candidate IDs, source ledger hash and decisions.
The client confirms reference intent; code checks that intent against evidence.
A quote matching an entity name alone does not establish a pronoun's referent.

Supported references are it/this/that (singular) and them/these/those (plural).
Code checks current entity existence, exact cited text, name or alias agreement,
explicit number, claim status and conflicting candidates. Reported claims do not
settle identity. Disputed claims, missing targets, mismatched names or number,
conflicting confirmed claims and absent confirmation produce explicit ASK reasons.
An explicit same-reference supersession chain handles a correction; newest-turn
recency alone never chooses a referent. A replacement cannot silently change the
reference cue. Existing ledger cycle/span checks still apply.

Sentence-local bindings remain authoritative in their frames. The global public
mention-to-ID map cannot represent distinct local and ledger targets for the same
literal; that collision now abstains. Live and ledger bindings that disagree also
abstain. AI identity suggestions remain subordinate to deterministic checks.
The memory policy version participates in the gate cohort; no calibration is
created from these tests or from schema validation.

Archive and active library
--------------------------

Existing exact current names/aliases bind to active entities. Stale/unavailable
snapshots and ambiguous aliases abstain. Archive ratified definitions remain
lexical meanings, never invented live entity IDs. Pending/imported/negative
records cannot authorize a binding; explicit ratified supersession selects the
new lexical definition. The archive snapshot API is unchanged. This change does
not implement persistent writes, automatic ratification, refresh, or an ASK UI.

Mixed 5,000-case evaluation
--------------------------

Serpent supplied independent clause/reference source graphs. A separate external
fixture recipe supplied explicit memory snapshots, expected identities and ASK
reasons. No READ predictions affected generation or expected answers; Serpent core
was unchanged. The reader received text and caller evidence, not expected outputs
or family labels. Gold was loaded only after capture. No AI was called.

* 1,000 fresh normalized-distinct parsing sentences: 997 correct, three unresolved,
  zero incorrect returned parses. Expanded combinations of existing grammar.
* 1,000 expected identity bindings: 1,000 correct (400 exact live/alias and 600
  confirmed ledger, corrected ledger or ledger-alias cases).
* 2,600 required ASK cases: all carried the declared semantic reason and no
  incorrect binding. These were not scored correct merely because route was ASK.
* 400 ratified/superseded archive definition cases: all selected the expected
  lexical record without manufacturing a live identity.
* Combined contract score: 4,997/5,000 (99.94%). Source retained: 5,000/5,000.

The previous committed reader achieved 2,997/5,000 under this new contract:
600 improvements are actual newly resolved ledger bindings; 1,400 are newly
specific ASK diagnostics. Those 1,400 already abstained before, so this is not
1,400 prevented unsafe actions. No formerly correct case regressed.

There are 5,000 distinct full inputs but only 1,007 distinct current sentences.
The 4,000 memory cases repeat 20 patterns across 200 contexts each, including ID
and revision substitutions and only four noun choices. They are contract stress
fixtures, not 4,000 independent language phenomena, natural-frequency data or a
statistical grounding-confidence calibration. The first capture used frozen code;
a later review added the local/ledger collision guard. Its separate development
replay retained all scores. The pre-review source is preserved for reproduction.

All 5,000 final routes remain ASK because no production calibration is installed.
Correct binding means the underlying proposal/evidence contract passed, not that
an executable request was accepted. No live AI correct-rate is claimed.

Unresolved parsing cases, preserved unchanged:

* Was the sensor not moved by Mira?
* Was the sensor not checked by Alex?
* Was the sensor not moved by Alex?

All abstain at the multiple-predicates/clause-attachment guard. They do not require
WORLD facts to parse. They are logged separately from memory failures.

Validation and limits
---------------------

Full suite: 251 tests, 250 passed, one optional-jsonschema skip. Added tests cover
confirmed references, reported/disputed status, absent IDs, mismatched evidence,
number, correction/conflict, forged spans, supersession cues and local scope.
Artifacts include before/after captures, gold, graphs, all failures, 2,000 ticks,
source hashes and an audit. reports/read-memory-grounding.html is the summary.

Remaining work includes automatic evidence-producing discourse tracking, richer
references (participants, ownership, ordinals and relations), per-frame identity
maps, lifecycle/persistence and separately calibrated acceptance. Confirming a
claim is a caller responsibility; this implementation does not infer truth from
quoted history or automatically turn an assistant claim into accepted memory.
