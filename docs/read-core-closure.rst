READ deterministic parsing milestone: closed within tested scope
===============================================================

Decision
--------

Close the current deterministic rule-expansion milestone at RuleAssigner version
7. The bounded parsing core meets the requested repeated fresh-set threshold.
Do not label unrestricted READ, production routing or memory grounding complete.
This is a scope boundary, not evidence that every unresolved input is ambiguous.
Earlier development data still contains 204 unresolved cases outside this narrow
confirmation scope. No parser rules were changed during this closure run.

Fresh confirmation
------------------

Set 13: 300 new normalized-distinct sentences, 300 correct literal-slot code
proposals, zero wrong and zero unresolved. They were selected from the unseen
remainder of the 12 existing lexical bindings, using unchanged Serpent grammar.
The code, scorer, adapter and recipe were frozen before selection; teacher gold
was loaded after capture. The audit recomputed scores and verified source and
reference hashes. The version 7 reader made no generative AI calls.

Earlier fresh version 6 sets scored 300/300, 300/300 and 299/300. The one failure
was fixed in version 7 and replayed separately. Do not combine these versions as
one frozen-model trial, or relabel the corrected 900/900 replay fresh evidence.
Set 13 covers C018 in 44 correct cases; C020 is not exercised in this fresh set.
Its evidence remains the saved regression case and controlled structural tests.

Source retention is 300/300 by design. Full suite: 241 tests, 240 passed and one
optional-jsonschema skip. Final routes remain ASK because calibration is absent;
this is not a measured correct-ASK rate. No server was started.

Serpent coverage review
-----------------------

Current local Serpent inventory was enumerated using clean surface options,
with source hashes and actual examples captured separately from READ accuracy:

* Canonical grammar: 2,607 cases across 21 families.
* Operator clean, terse and hesitant: 115 cases each, 21 families each.
* Personal assistant and software project: 52 cases each, 11 families each.
* Gorgon, general assistant and transcripts: 150 cases each, 11 families each.
* Conversations: 333 cases across three families.
* Context scenarios: 16 fixtures (four tasks times unique, ambiguous, withheld
  and correction conditions). These are not 16 independent natural workflows.

These counts are separate inventories, may overlap, and are not additive unique
coverage or evaluated READ success counts. The three conversation families are
statements, questions and uncertainty using bounded first/second-person forms.
The transcript vector with clean options is not evidence of noisy transcription
coverage. Serpent's source graphs encode richer relations than the current
literal-slot scorer, including order, quantities, scope and references.

Examples from the actual operator inventory include:

* Open the configuration file.
* If the tests fail, stop the deployment.
* Use staging instead of production.
* Inspect all failed files except the configuration file.
* Create two Ubuntu VMs with 4 GB of RAM each.
* Define "check-pass" as validating the configuration file.
* Run the tests every 3 hours.

Next-data decision
------------------

No new generic language templates or new broad domain vectors are needed now.
Use the existing operator and general-assistant vectors for a bounded next-stage
assessment. Evaluate source-graph relations as well as literal slots before
claiming sequencing, negation, resource allocation or constraints are correct.
Do not execute generated requests.

A focused integration fixture set is needed before claiming memory/ASK readiness:
unique live identity; aliases; duplicate/conflicting names; stale snapshots;
ledger correction and supersession; ratified versus pending archive entries;
local versus cross-turn references; absent context. Supply independent expected
identity IDs and ASK reasons, plus exact history/library/archive snapshots.
Score parsing, deterministic binding and ASK correctness separately. Do not
teach the generator from READ predictions. Existing 16 context fixtures are a
starting point, not archive/library lifecycle coverage.

Implemented boundaries remain: code extracts source roles; deterministic evidence
is authoritative for grounding; missing or ambiguous grounding blocks AI and
hands off to ASK. General history/participant/ordinal resolution, persistent
archive update/ratification, calibration and the ASK interaction loop are not
certified by this closure. Keep these explicit in the integration backlog rather
than implying the entire system is production-ready.

Evidence
--------

reports/read-closure.html is the readable closure and inventory review.
evidence/read300/batch-013 contains all new inputs, gold, captures and audit.
evidence/read-closure-1 contains freeze hashes, inventory examples, contextual
samples, tests and closure status. Older evidence and recipes are unchanged.
