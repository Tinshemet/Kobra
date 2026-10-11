Active library, archive and READ
===============================

Implemented checkpoint: 2026-10-11. This is a generic read-only integration, not
a complete migration of Gorgon or a persistent memory service.

What the three stores mean
--------------------------

The active library describes current objects and relationships. The archive
records learned vocabulary: what a word means, who taught it, whether that meaning
is ratified, and what it replaces. The context ledger records previous turns and
claims. A lexical definition does not establish that an object exists.

Example: archive "jumpbox -> vm" can classify "Create a jumpbox". It cannot bind
that phrase to an existing VM. A current library record with name "Alpha" and ID
"vm-1" can supply an exact candidate for "Restart Alpha". Two records with alias
"Alpha" remain ambiguous. No record grants permission to execute anything.

New integration
---------------

KnowledgeSnapshot accepts separately versioned live, manifest and archive
sources. Live sources explicitly attest current, stale or unavailable. Current
is the caller's assertion; READ neither refreshes nor verifies the remote system.
All inputs and outputs are copied. Source revisions and a content hash accompany
lookup evidence. No process-global store or VM-specific imports are introduced.

Lookup returns all matching candidates, exclusions, status and selected evidence:

* Exact live names and explicit aliases have priority for entity identity.
* Manifest lexical records precede ratified, told archive meanings.
* Pending, imported and superseded entries remain visible but cannot settle.
* Negative entries remain distinguishable from unknown words.
* Multiple eligible meanings remain ambiguous; there is no first-match win.
* Explicit owner lookup follows bounded, cycle-checked class inheritance. Missing
  owner, wrong owner, negative owner and cyclic definitions do not settle.
* General kind/attribute chain interpretation remains unsupported, with evidence
  retained. This implementation does not infer owner context from a sentence.

Pass knowledge=KnowledgeSnapshot(...) to GatedRuleReader. After code assigns
roles, the reader looks up each complete agent/patient/recipient phrase, optionally
removing an initial article. It merges current live entities with caller WORLD;
conflicting records for the same ID or duplicate names across sources yield ASK.
A unique exact live match can add a grounding while leaving source role strings
unchanged. Create/provision/clone/copy descriptions are not automatically bound to
existing objects. These four verbs are a bounded guard, not a full creation grammar.

Archive definitions produce lexical annotations, never WORLD IDs. Unsupported,
ambiguous or negative matching knowledge yields explicit ASK reasons unless live
identity resolves that exact phrase. Unknown vocabulary alone is not proof of an
error: new descriptions may be valid. A stale/unavailable supplied live snapshot
conservatively blocks the knowledge-enabled interpretation.

The optional model receives a copy of lookup evidence. In knowledge-enabled mode,
its grounding and WORLD references must match a unique current candidate for the
proposed role phrase; mere ID existence is insufficient. Cross-turn pronouns
currently lack a supported candidate resolver and remain ASK. The legacy wrapper
without knowledge retains its older behavior, including existence-only grounding
checks. A restricted model role-selection schema is still separate unfinished work.

Calibration cohorts include the knowledge resolution version and snapshot hash.
This deliberately invalidates calibration after knowledge changes. No actual
calibration is installed. The tests use explicitly synthetic fixtures to exercise
ACCEPT/ASK contracts; they are not measured language or model accuracy.

Minimal client example
----------------------

::

    from kobra.knowledge import KnowledgeSnapshot
    from kobra.confidence_gate import GatedRuleReader, ConfidenceGate
    from kobra.rule_assignment import RuleAssigner

    knowledge = KnowledgeSnapshot(live={
        'revision': 'inventory-17', 'source': 'client-adapter',
        'status': 'current',
        'entities': {'vm-1': {'name': 'Alpha', 'aliases': ['lab machine', 'server']}}
    })
    reader = GatedRuleReader(RuleAssigner(), ConfidenceGate(), knowledge=knowledge)
    result = reader.read('Restart the server.')
    # Exact live binding is recorded; absent calibration still yields ASK.

Archive records require explicit id, word, type, source, status and provenance.
Types are class/attribute/unit/value. append_archive(record, revision=...) returns
a new snapshot. A ratified told correction may cite earlier same-word IDs in
supersedes; historical records stay present. This is an in-memory lifecycle, not a
disk write or automatic teaching channel. READ never ratifies natural-language
claims by itself. The client owns the teaching policy.

Legacy coverage audit
---------------------

Covered in this addition: generic live snapshot lookup, all-candidate aliases,
lexical precedence, explicit archive eligibility, negative knowledge, bounded
owner lookup, append-only supplied revisions, evidence transport and gate checks.

Partially covered: WORLD settlement (exact names only); archive settlement
(annotations, not full inherited semantics); owner attributes (lookup API only);
model resolution (candidate validation, not full role/context selection).

Not migrated: executor startup snapshot, targeted tool-effect refresh and event
log; remote failure/retry handling; fleet/network/template/OS relation queries;
archive disk persistence and atomic transactions; natural-language teaching,
correction and forgetting workflows; reciprocal references and exclusions;
source/clone-source settlement; self-address/meta-control handling; affordance
settlement; general previous-turn binding; ASK conversation loop. These are tracked
requirements, not assumed behavior. Sentence-level grammar gaps remain in
read-rule-coverage.rst. READ is not yet closed.

Research and design decision
----------------------------

The source audit compared a full Gorgon import with a generic immutable snapshot
adapter. The adapter was selected because it preserves explicit boundaries without
importing the executor/planner or copying first-match and unavailable-as-empty
behavior. It can be rejected if callers cannot supply stable IDs, revisions and
availability; those clients then need an explicit adapter, not guessed state.

Inspected upstream sources (local Gorgon, 2026-10-11):
files/orchestrator/ai/active_library.py (snapshot/apply/resolve/relations);
files/orchestrator/languages/english/seam/archive.py (Entry.routes, learned,
ancestors, apply_effects); pass1.py (read_and_settle, settle_from_archive).
The old pass order was manifest extraction -> WORLD -> archive unknown-kind fill
-> optional model. It is not identical to Kobra's role/annotation boundary.
Direct operator teaching in old apply_effects could itself ratify a statement;
a second approval was not universally required. This client policy is not copied
into READ automatically.

Primary references reviewed 2026-10-11:
https://www.w3.org/TR/prov-dm/ — source, revision and responsibility metadata help
trace evidence; provenance does not prove truth.
https://www.sqlite.org/transactional.html — atomic transactions are relevant to a
future persistent archive. No database or new persistence dependency was added.

Validation
----------

See evidence/knowledge-lookup-1 for executed tests, independent counterexample
review and actual local example outputs. No live generative model calls, benchmark
corpus changes, Serpent edits, or fresh accuracy measurements are part of this work.

Observed parser gap: the current spaCy-based role path leaves "Restart Alpha."
unresolved. Exact lexical mention evidence still reaches the resolver, but lookup
does not silently repair syntactic roles. The example report preserves this case
alongside a working exact alias case; neither is an accuracy sample.
