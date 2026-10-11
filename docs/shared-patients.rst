Shared patients in coordinated commands
=======================================

Checkpoint: 2026-10-11. C016-trailing-shared-patient extends the bounded command
rules. It is not a general ellipsis resolver or a new accuracy claim.

Example
-------

"Create and launch three VMs and restart them."

* c1 contains exactly "Create"; c2 contains "launch three VMs"; c3 contains
  "restart them". Their source spans do not overlap or absorb connectors.
* Create and launch each have patient "three VMs" and quantity "three".
* A shared_arguments edge links c1's patient to the noun phrase in c2.
* Both chunks point to one local entity e1. That entity records created_by c1.
* The later "them" points to e1, not two competing copies of the same group.
* Plain "and" preserves coordination; only an explicit "then" adds a sequence
  marker. READ does not execute these actions.

Surface boundaries are source-only rules. The donor noun phrase still comes from
spaCy's learned role candidates plus existing validation. A successful rule is a
supported interpretation proposal, not proof of intended meaning.

Eligibility
-----------

A run of bare predicates must end with one explicit simple noun phrase. The final
connector must contain "and" (optionally "and then"); earlier commas may enumerate
bare predicates. Semicolons, "then" alone, alternatives and unsupported scope do
not trigger sharing. Each participating action sequence must appear in an explicit
shared_patterns contract. ACTIONS vocabulary membership alone is insufficient.

The default patterns are in src/kobra/shared_patients.py. They include create +
launch, create + configure + launch, download + install, open + read, open + close,
read + print, inspect + repair and create + delete. These are declared bounded
interpretations. They are not a learned or universal verb-valency dictionary.

RuleAssigner(shared_patterns=...) permits client-specific patterns; an empty list
disables sharing. Existing simple and separate-object rules remain available.
Configuration hashes cover rule version, action vocabulary, patterns and parser
name/version; changing them changes calibration cohorts. No real calibration is
installed by this work, and fingerprinting is not semantic validation.

Remain unresolved: "Stop and read a book" (no compatible pattern), shared
pronouns, nominal conjunctions, attached PPs, member enumerations, missing final
objects, negation/conditions, and left-object propagation ("Create three VMs and
launch"). Modifier scope must be implemented separately before propagation.

Archive, library and ledger integration
--------------------------------------

Creation provenance belongs to the entity, not only the first action. Trusted
code metadata propagates creation to every sharing chunk and later local patient
references. Knowledge lookup therefore uses lexical definitions without treating
same-named current library records as that new entity. Even two existing objects
with the same name cannot capture the newly described target. Archive pending,
negative or ambiguous lexical meanings still retain their normal restrictions.

The model cannot assert its own created_by metadata to obtain this exemption.
Only the code proposal supplies trusted creation frames. If the same literal
would denote both a created target and an existing object in different frames,
the current mention-to-ID contract cannot express that distinction: code removes
the global binding and returns knowledge_conflicting_mention_roles. Frame-scoped
WORLD grounding is future work. Model-produced identity
claims still have to satisfy current candidate checks. Prior turns and claims
remain copied into the context ledger on all outcomes. Automatic archive updates,
ASK orchestration, persistence and live refresh remain unfinished; this rule does
not replace them.

Research and alternatives
-------------------------

Universal Dependencies distinguishes shared from private conjunct dependents:
https://universaldependencies.org/u/dep/conj.html#shared-dependents-and-effective-parents-in-coordination
https://universaldependencies.org/u/overview/enhanced-syntax.html#propagation-of-outgoing-dependencies-from-conjuncts
Reviewed 2026-10-11. These guides justify explicit sharing edges; they do not
provide a universal algorithm that decides whether a complement is shared.

We compared copying the last object to every preceding conjunct with an explicit
bounded pattern contract. Actual parser probes give similar object attachment
for "Create and launch three VMs" and "Stop and read a book". The broad rule would
therefore invent an object for stop. The bounded contract was chosen; a supported
pattern producing a private-object interpretation is a counterexample requiring
review, not a reason to relabel the reference or claim confidence from syntax.

Evidence
--------

evidence/shared-patients-1/before.json preserves 15 pre-change development
outputs. after.json records the revised outputs, including unsupported examples.
These examples were selected for development, not sealed fresh evaluation.
The paired archived 600-case replay retains 387 correct code-routed cases, zero
new ticks and zero regressions under the legacy literal-slot metric. It does not
score the new sharing edges. Structural and knowledge integration tests verify
those edges and creation behavior separately. No live model calls were made.
