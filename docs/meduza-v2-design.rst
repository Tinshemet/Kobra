Meduza 0.2: a language for resolved work
======================================

Status: concrete design draft, 2026-10-11. The JSON grammar and fixtures are
implemented; the compiler, semantic checker and runtime below are specified but
not implemented. This is not a replacement for the running legacy Medusa engine.

Decision
--------

Keep Meduza as a real, inspectable procedure language. READ now supplies structured
meaning and grounding, so Meduza need not recover these from prose. RESOLVE
supplies reasoning decisions and their dependencies; code constructs the program.
The model can propose unfamiliar plans, but does not have to serialize a complete
program, remember every binding or invent a capability interface.

Two viable directions were considered:

* Wrap the current Gorgon IR unchanged. This is the smallest integration, preserves
  existing behavior and makes a useful migration baseline. It also preserves
  implicit references, global configuration dependencies and incomplete evidence
  identity in the wire contract. Reject it as the final design if these features
  cannot express the required READ provenance or reliable resume semantics.
* A versioned language-only contract with a reviewed legacy adapter. This is the
  selected direction. It makes data, identity, evidence and execution effects
  explicit while preserving the main operations. The costs are an adapter,
  conformance fixtures and semantic migration checks. Reject individual new forms
  if they lose legacy meaning or increase authoring failures without benefit.

Do not replace Meduza with unrestricted generated Python, or call the RESOLVE
hypothesis graph an executable program. Unselected hypotheses remain reasoning
state. Generated implementation code, when enabled, is a separate tested artifact
behind a capability manifest, not a string evaluated by the Meduza interpreter.

Language contract
-----------------

The canonical artifact is JSON with schema meduza.program/0.2-draft. A human
.medusa view can be parsed/rendered against the same IR in the future. Human
syntax is not finalized by this draft; illustrative keyword names are not a
second implemented parser. Preserve meaning, not byte-for-byte formatting, across
future parse/render round trips. Legacy Medusa remains an explicit input version.

A program records identity/revision, FETCH/ENSURE/ACHIEVE mode, origin artifact
hash and RESOLVE decision ID, objective hash, pinned dependency versions/hashes,
policy reference, typed parameters, finite local limits and a statement body.
Each statement records a stable ID and source-point/decision origins. Hashes and
IDs are claims until resolved against actual artifacts; schema validity alone
cannot authenticate them. Runtime grants are separate from the program.

READ-to-program preservation
----------------------------

The compilation input includes the complete resolve-distillation-3 artifact plus
RESOLVE decisions. Preserve source text, metadata, retained material, point IDs,
roles, grammar, qualifiers, local references, WORLD bindings and context evidence.
Every meaningful point needs a disposition: realized by named program nodes,
answered as data, retained as an assertion, or unresolved/unsupported. Compilation
must not silently drop an inconvenient qualifier. Noise labels are not authority
to erase an interpretation issue.

READ owns ambiguity and reference grounding. Missing user intent returns ASK;
missing world evidence can justify a FETCH obligation. Calibration-blocked input
may be inspected in a development projection but cannot become executable through
Meduza compilation. A supported interpretation is not an execution grant.

Do not convert generic coordination into a required order unless there is an
explicit temporal constraint or a real data/effect dependency. The compiler may
choose a safe serialization, but must distinguish that implementation choice from
what the user expressed. Questions and assertions need not become programs.

Modes and effects are distinct
------------------------------

FETCH returns information. ENSURE obtains enough evidence to check a proposition.
ACHIEVE permits planning toward a stated outcome within an independently granted
scope. Preserve this vocabulary, but do not confuse the mode with permission.

The manifest classifies capabilities as pure, observation, creation, mutation or
external publication, with concrete resource effects. FETCH/ENSURE may use pure
and authorized observation operations, never silently perform a correction.
Observation can consume resources and have operational impact; budgets still apply.
ACHIEVE does not authorize every mutation a tool supports. ROUTE and the executor
intersect mode, intent, scope, cockpit policy and host capability limits.

PUBLISH means return a value to this invocation's caller. Sending email, publishing
externally or writing to another service is an ordinary externally effectful
capability with its own grant, not a side effect hidden behind PUBLISH.

Typed values and references
---------------------------

Use tagged references rather than guessing from a string's leading dollar sign:

    {"literal": "$this-is-text"}
    {"ref": "observation"}
    {"parameter": "target"}
    {"entity": "existing-world-id"}
    {"field": {"value": {"ref": "observation"}, "path": ["payload", "status"]}}

Kinds include scalar values, entity<kind>, record<schema>, evidence<T>, set<T> and
list<T>. The draft grammar uses an unparameterized evidence marker; evaluator
manifests must specify payload schemas. Sets are collections of stable identities
with no semantic ordering; lists have ordering. Cardinality is part of the type,
not a runtime guess. No implicit broadcast, arbitrary Python expressions or
string interpolation into executable code.

NEW binds a set even when count=1. Selecting exactly one requires an explicit
catalog operation that checks cardinality; a scalar input cannot receive a set.
This is an intentional migration change from count-dependent binding shapes.
References from QUERY are data, not automatically WORLD handles. A data value
cannot be cast to an entity identity merely because its text matches a name.

Bindings are single-assignment within lexical scope. Branch-local bindings do not
escape; loop-local bindings are recreated per iteration. Parameters are separate
from locals. Each invocation has fresh bindings. The schema cannot enforce these
rules; the future semantic checker must reject violations.

Ten statement forms
-------------------

* NEW: invoke a declared factory, bind a typed set of created identities, and
  record partial creation. It does not promise atomicity across multiple creates.
* FETCH: invoke an observation capability; bind an evidence-bearing result or a
  declared identity-bearing result whose provenance must be validated.
* QUERY: invoke a pure/read capability and bind non-authoritative report data.
* CALL: invoke a capability or pinned public class method; bind its typed result.
* FOREACH: snapshot a supplied collection, enforce max_items without truncating,
  and run a body per member. An exhaustive goal over a partial collection remains
  unsupported until completeness is established.
* IF: branch on a predicate verdict. Unknown/conflicting outcomes suspend, rather
  than becoming false. Both branches remain explicit in the artifact.
* BREAK: leave the innermost loop only. Outside a loop it is invalid. A partial
  iteration does not satisfy an all-members obligation.
* ENSURE: check a proposition against matching evidence. False fails or suspends
  according to the explicit local policy; unknown/conflict suspend.
* ACHIEVE: expose a bounded goal obligation. Use a proven applicable deriver or
  return NEEDS_RESOLVE. It is not a general solver implemented by the keyword.
* PUBLISH: return a typed value/finding to the caller, preserving claim status.

FOREACH now carries a body rather than a single call; nested effects and bindings
are checked recursively. Unbounded WHILE, dynamic imports, arbitrary evaluation,
implicit parallelism and invisible recovery are outside this draft core. They
must not be smuggled in through a class method. The current research proposal can
still iterate through new, budgeted program revisions between observations.

Predicates, evidence and completion
----------------------------------

Predicates are typed registered tests with explicit arguments, evidence inputs and
maximum evidence age, or ALL/ANY/NOT compositions. A domain evaluator must specify
its property, admissible evidence and result schema. Tests are pure evaluations;
necessary external probes appear as separate FETCH/CALL operations. A test name
is not a function body and cannot execute arbitrary user text.

Verdicts have support/refutation states: true, false, unknown, conflicting.
For composition use a four-valued support/refutation pair (t,f): NOT swaps the
pair; ALL uses (AND t, OR f); ANY uses (OR t, AND f). Do not coerce these states to
Python truthiness. Missing evaluators or unsupported evidence are typed errors,
not false verdicts. Version this algebra in the future evaluator contract.

An evidence record must identify the invocation, action, attempt, observation,
subject, objective obligation, program revision, artifact/world revisions,
observation time, expiry, dependencies and provenance. An evaluated predicate
lists the exact evidence IDs and relevant inputs it consumed.

Action completed, effect observed and objective achieved are separate statuses.
A previous event's positive telemetry cannot verify the next event. Evidence must
match the verification subject/event/artifact and remain valid at evaluation time.
Absence of failure is not proof of a universal property. The POC's repeated-event
false success becomes a required regression case for the future runtime.

ACHIEVE refreshes evidence on every round. It succeeds only when the objective
predicate is true; a method returning successfully is insufficient. Known gap
with no needed changes, known gap with a correction plan, and no applicable
derivation are distinct results. Novel planning returns to RESOLVE, sharing the
same invocation-wide budget; nesting must not reset limits.

Classes and packages
--------------------

A class is an encapsulated domain interface. Its public manifest contains receiver
and argument types, method IDs, result schemas, preconditions, effect bounds,
postconditions, evidence requirements, costs and exact dependency versions.
Factory selection precedes instance-method selection: an object cannot create
itself. A receiver-specific call gets only the relevant public method options and
needed decision context. Code retains all global constraints even when the model
receives a small projection. This preserves the earlier narrow-selection design.

A public method may reference an executor primitive or a verified Meduza procedure.
Resolve and pin transitive dependencies before execution; recursive procedure
cycles are rejected in this draft. Expanded bodies and provenance must be
inspectable. Gates and budgets apply per underlying operation, including recovery.
A method may not declare itself read-only while its body mutates. Expansion also
requires hygienic bindings and stable mapping back to the original call node.

Packages contain manifests, programs, tests and documentation. They do not supply
a second executor. The declared public surface, offered schemas and actual
implementations must agree. Learned methods are candidates until independently
tested under the Learning dial; one successful run is not general validation.

Memory and lifecycle
--------------------

Archive stores versioned knowledge and method evidence; Active Library contains
current world projections; the ledger records program revisions and observations.
Mutable values are not embedded as permanent truths in reusable programs.
Package metadata is not current world evidence, and neither grants authority.

A plan may be revised only through an explicit decision with retained prior
versions, completed effects and unresolved outcomes. Per-action execution keys
include invocation and loop occurrence; retry reuses the original logical action
key, while a genuinely new action gets a new key. Unknown effects require
reconciliation; no generic exactly-once claim is made for external systems.

Saved programs enter through validation and ROUTE, not through English READ.
Changes to dependency versions require revalidation. Runtime outcomes proposed
for the data boundary are completed, partial, needs_observation, needs_resolve,
needs_user, blocked, unsupported, cancelled and outcome_unknown. A failed
verification does not silently request more authority or start a model session.

Dials
-----

The existing 16-dial catalog remains authoritative as a set of requested bounds,
not hardcoded defaults inside the language. Reins, horizon and complexity bound
reasoning and expansion; Learning governs method promotion; Intent governs
subgoal freedom; Delegation, Persistence and unattended time govern lifecycle;
Reach, scope, impact, resources and containment govern actual calls; provenance
rules govern evidence use. Cunning/Cruelty settings do not change predicate truth
or make dishonest output valid. Undefined levels remain unsupported until their
semantics are separately established.

The program names a policy reference; the executor resolves and checks the
current policy at dispatch. Local limits may narrow that policy but never expand
it. Runtime and external acceptance limits remain mandatory even if a program
requests more. No self-issued authorization fields are allowed by the schema.

Migration and implementation order
----------------------------------

1. This draft: grammar, illustrative programs, migration decisions and a schema
   conformance test. No real execution or RESOLVE claim.
2. Language-only semantic checker: symbol scope, types/cardinality, effect closure,
   provenance coverage and exact manifest/dependency resolution.
3. Compiler/renderer plus explicit legacy adapter: preserve old semantics or
   refuse with a migration diagnostic. Never rewrite a check into a correction.
4. Injected executor protocol and mock conformance suite: evidence identity,
   four-valued predicates, bounded ACHIEVE, partial creation, IF/FOREACH scope,
   per-call gates, replay, cancellation and saved-program entry.
5. RESOLVE uses this contract to construct and revise unfamiliar work; evaluate
   the reasoning hypothesis independently from schema and execution correctness.

Reuse candidates: parser/rendering concepts, narrow leaf schemas, public class
method manifests, symbolic selectors, existing derivation algorithms and known
regression cases. Review each dependency before extraction. Do not import the
Gorgon tree into Kobra or claim its old scores apply to the new contract.

Legacy changes are explicit: dollar references become tagged values; flat implicit
bindings become typed lexical bindings; NEW always binds a set; single-call loops
can map into bodies; mixed read/result behavior splits into FETCH/QUERY; implicit
predicate probing becomes explicit observation; IFAILS must become an explicit
checked recovery method or be refused by the adapter. Domain count/reach/disjoint
predicates become catalog tests with preserved semantics. Surface primitives are
not falsely advertised as sugar over count/reach.

Evidence and limitations
------------------------

schemas/meduza-program-0.2.schema.json is a draft shape contract, not a compiler.
examples/meduza-v2 contains hand-authored fixtures with placeholder hashes and
capability names. The schema cannot prove grounding, intent, effect safety,
source faithfulness or task completion. Semantic and runtime conformance tests
are future milestones, not passed tests hidden behind a schema result.

Primary references consulted 2026-10-11:

* https://json-schema.org/draft/2020-12 — schema dialect and validation structure;
  does not supply the semantic validation described above.
* https://www.w3.org/TR/scxml/ — established separation of state/control flow,
  executable content and external invocation; design reference, not a claim that
  this draft implements or conforms to SCXML.
* Local Gorgon planner/ir/{intent,execute,derive,lower,classes,config} and existing
  Meduza boundary review. Historical notes are leads, not new measurements.
