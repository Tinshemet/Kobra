Kobra: agreed responsibilities and current work
==============================================

Recorded 2026-10-08 from the user's direction on 2026-10-07.

Kobra is an independent linguistic-to-reasoning harness for small models, with
reliability and security as design goals. Gorgon is a future client, not the
definition of Kobra's language or acceptance criteria.

* Front door prepares, normalizes and denoises text while preserving provenance.
* READ distills what the user expressed into one sentence per point, retaining
  objects, relationships, goals, statements, constraints and uncertainty.
* RESOLVE owns reasoning and thinking over that interpretation and evidence.
* ROUTE owns security decisions about the proposed result and its handoff.

Front door and READ largely preserve their existing linguistic code. They are
being separated from Gorgon-specific vocabulary, imports and runtime state.
READ's prose points carry a small structural wrapper; structural validity alone
does not establish faithfulness or prevent hallucination. RESOLVE must keep
stated content separate from its inferences and assumptions.

Medusa ownership
----------------

Kobra owns the Medusa language. Authoring a new Medusa program passes through
the front door / READ / RESOLVE / ROUTE pipeline. Executing an existing Medusa
program is outside that pipeline; execution does not reinterpret its source
as a new natural-language request. This ownership decision does not assign
Gorgon's concrete VM/network tools to Kobra or implement a Medusa runtime here.
Detailed compiler/runtime interfaces remain a later work item.

Progress
--------

The user accepted the Stage 1 direction and draft with the Medusa ownership
clarification. The twelve draft examples remain development fixtures, not
independently certified gold or held-out evaluation cases. Their draft files
and historical review record are preserved.

Stage 2 now provides EnglishFrontDoor with explicit immutable DomainVocabulary.
The existing normalization rules are retained, including their limitations.
Clause restoration and predicate-boundary helpers were separated from pass2
and planner lookups. Client operation words, noun forms, status values, known
names, dual verbs and protected words must be supplied explicitly. No model or
world lookup is performed by normalization.

Next: validate the front door on reviewed cross-domain cases, then connect its
original-offset map to the distilled READ contract and generalize READ. The
current READ and RESOLVE pipeline protocols remain generic placeholders.
