Deterministic distillation for RESOLVE
======================================

The current resolve-distillation-3 contract projects the current gated READ result
into one structured point per frame. Its main consumer is RESOLVE, so the compact
roles and qualifiers are authoritative representations of the upstream proposal;
a role-labelled summary is provided for inspection. This is not the older
model-authored prose distillation path, which remains available separately.

API
---

    reader = GatedRuleReader(RuleAssigner(), ConfidenceGate(), knowledge=snapshot)
    handoff = reader.read_for_resolve(text, history=turns, context_claims=claims)

For an already computed gated result:

    from kobra.resolve_distillation import distill_for_resolve
    handoff = distill_for_resolve(read_result)

Neither API calls an additional model. The original result remains unchanged.
This exposes a handoff contract; it does not implement RESOLVE reasoning or
replace the legacy generic Pipeline integration automatically.

What RESOLVE receives
---------------------

* Exact original source, its SHA256 and stable request source ID.
* Source-ordered points: act, predicate, explicit arguments, qualifiers,
  readable role summary and exact source evidence.
* Grounded WORLD identities with deterministic knowledge or ledger evidence;
  surface pronouns remain intact rather than being silently rewritten.
* Sentence-local references and entities, distinct from WORLD identities.
* Shared arguments and supporting spans even when outside the receiving chunk.
* Member specifications and modifiers from structural READ.
* Existing relations mapped to point IDs. Coordination source order is not
  promoted into an execution-order constraint.
* Unassigned source text, including connectors, greetings and unsupported input.
  Nothing is silently categorized as garbage.
* Prior-turn memory context, grounding evidence, rules, gate reasons, cohort and
  external score. Gate rejection remains rejection.

NONE slots are omitted from arguments/qualifiers; reinserting NONE reconstructs
the original frame exactly. MISSING and UNKNOWN remain explicit. Negation,
condition, time, quantity, attribution and modality remain on their owning point.
Questions remain questions; assertions remain attributed input, not verified
facts. Original wording is necessary: current slots do not encode every
linguistic distinction, including unsupported scope and discourse distinctions. Version 3 adds explicit
tense, aspect, voice and polarity for the supported grammar. The summary must never
be used as a replacement for the source-backed structured point.

Evidence for simple clauses covers the full source. Supported structural frames
use exact chunk spans plus shared-argument spans. Multiple frames without a
trusted chunk map use full-source support rather than invented offsets. Unmapped
relations and unsupported groundings produce diagnostics; invalid frames preserve
source as unresolved text. ready_for_resolve requires upstream ACCEPT, usable
points, a supported interpretation and no distillation diagnostics. No new confidence or authorization is
created. Current uncalibrated runs remain ASK and ready_for_resolve is false.

Example
-------

"Was the sensor not moved by Mira?" becomes a question point with predicate
"moved", agent "Mira", patient "the sensor" and negation "not". Its summary is:

    Question: predicate="moved"; agent="Mira"; patient="the sensor"; negation="not"

The original question and spans accompany it. This does not assert that Mira
moved the sensor or that she did not move it. RESOLVE receives the expressed
question, without an answer or manufactured WORLD fact.

For "Open and read the file.", two points share patient "the file". The first
point cites both "Open" and the later patient phrase, preserving the shared
argument edge. Its relation to the second point remains coordination_source_order_only.
For "Move it." with a confirmed ledger binding, the patient stays "it" and a
separate identity_binding links it to the existing ID and exact prior-turn quote.

Three passive-question fixes
----------------------------

C021, RuleAssigner version 8, handles the observed parser pattern where BE is
ROOT and the participle is ccomp with the patient attached beneath it. The
existing complete passive-question shape must pass before only that specific
ccomp is exempted from the clause guard. Real subordinate/relative/conditional
clauses still abstain. There is no hardcoded sensor, verb or person name.

Fixed cases: "Was the sensor not moved by Mira?", "Was the sensor not checked
by Alex?", and "Was the sensor not moved by Alex?". All retain question act,
correct agent/patient roles and negation.

Validation
----------

Full suite: 262 tests run, 261 passed, one optional-jsonschema skip. New tests
cover the three failures and nearby genuine clauses; distillation tests cover
negation/questions, shared evidence, exact retention, ledger provenance, input
immutability, unsupported grounding, qualifiers, invalid frames and bad spans.

Reused 5,000-case memory/parsing contract replay: 4,997 to 5,000 correct, three
flips, zero regressions. Each projection reconstructs every original frame and
identity map, retains every source character, and preserves the gate decision.
These are representation invariants, not proof of complete semantic accuracy.
The historical fresh scores and captures remain unchanged. No generative AI
calls were made; all final routes remain ASK without calibration.

Evidence is in evidence/resolve-distillation-1, including compressed full
captures, baseline/source hashes, per-case ticks and examples. The HTML walkthrough
is reports/read-resolve-distillation.html. Broader language coverage, automatic
free-form discourse inference and calibrated acceptance remain separate work.

Version 2: metadata, garbage/noise annotations and open issues
------------------------------------------------------------

Version 2 introduced resolve-distillation-2. Existing points, grounding,
relations, source and gate fields are unchanged. Added fields:

* metadata: producer and versions, READ configuration ID, assignment origin,
  whether generative assignment was used, Unicode offset units, point/relation
  counts, source/accounted/discarded character counts and caller metadata.
* text_accounting.partition: non-overlapping source intervals that concatenate
  exactly to the original input. Categories distinguish point evidence,
  formatting, punctuation, recorded connectors, unresolved and unclassified text.
  Point evidence coverage does not establish complete semantic interpretation.
* text_accounting.garbage, noise, social, unclassified and unresolved: retained
  spans with reasons. Unknown or unsupported input is never automatically garbage.
* text_accounting.annotations: exact caller annotations with provenance, an
  explicit unverified status and whether they overlap point evidence. They cannot
  delete text, override negation, authorize grounding or change gate status.
* text_accounting.open_items: separate parsing, missing-context, reference,
  knowledge, calibration and validation issues with original reason codes.

Optional API arguments:

    reader.read_for_resolve(text,
        metadata={"request_id": "r1", "channel": "text", "language": "en"},
        annotations=[{"start": 0, "end": 18, "text": "[transport-marker]",
                      "category": "garbage", "reason": "transport artifact",
                      "provenance": "caller-transport"}])

The example annotation requires the input to begin with exactly that span.
Metadata is copied into a caller namespace and must be finite JSON; it is not
promoted into identity or routing authority. The implementation does not infer
language, timestamps, speakers or disposable meaning. Garbage/noise/social
labels require caller annotations for now and remain assertions rather than
verified semantic classifications. Their text is retained for future turns.

Validation: 269 tests run, 268 passed, one optional dependency skip. A replay
of 5,000 saved handoffs verified unchanged existing fields and exact source
partitions, with zero characters discarded. This is schema/retention verification,
not a fresh language accuracy claim. New report: reports/read-distillation-metadata.html.

Version 3: interpretation belongs to READ
----------------------------------------

READ owns interpretation and grounded reference decisions. RESOLVE receives
supported meaning; it must not silently finish missing linguistic interpretation.
Unsupported or ambiguous meaning remains an explicit READ ASK condition.

* interpretation.status is supported or unresolved; needs_ASK describes meaning,
  grounding and validation blockers. Calibration reasons are excluded here.
* acceptance records operational acceptance and separate calibration reasons.
  A well-parsed question may have supported interpretation while its legacy route
  is ASK because its cohort lacks calibration. This is not a request to clarify
  an already understood question. Consumers should distinguish these states.
* Each supported point has grammar: tense, aspect, voice, polarity and exact
  auxiliary/voice marker spans. Existing modality and other qualifiers remain.
* The source audit accounts for tokens through literal slots, grammatical markers,
  structural members/modifiers, supported connectors and bounded social prefixes.
  Full-source evidence alone cannot mark every word interpreted. Unrepresented
  words produce uninterpreted_source_material and prevent readiness, even with
  calibration. Caller garbage/noise annotations cannot bypass this audit.
* Identity bindings belong to a frame and argument slot. Different occurrences
  of "it" may have different caller-confirmed identities. The old mention-to-ID
  map is emitted only when it represents all occurrences without conflict.

Confirmed ledger claims may optionally include::

    "reference_scope": {
        "source_sha256": "<SHA256 of the exact current source>",
        "frame": 0,
        "slot": "patient"
    }

A scope applies only to that source, zero-based frame and agent/patient/recipient
slot. It is not inferred confirmation. Exact prior-turn quotes, existing WORLD
IDs, number, status and conflict checks still apply. AI-supplied role bindings
cannot grant identity authority. Created/live repeated-name ambiguity still asks;
per-role storage alone does not resolve intent. Unscoped claims retain their
existing all-matching-roles behavior and conflicting claims abstain.

Examples:

* "Was the sensor not moved by Mira?": question, Mira as agent, sensor as
  patient, negative polarity, past tense, simple aspect, passive voice.
  Interpretation is supported; missing calibration still blocks acceptance.
* "The server is very quiet.": the current slots omit the degree word "very".
  READ exposes that token and asks; source retention does not excuse lost meaning.
* Two scoped confirmed claims can bind frame 0 patient "it" to a box and frame 1
  patient "it" to a lamp. This is tested as a contract fixture, not evidence that
  free-form conversational references can be inferred automatically.

The audit establishes bounded representation coverage, not universal entailment.
It uses exact literal matching, so repeated identical wording is not independently
proved to have the correct scope. Unsupported clauses, qualifiers and discourse
remain ASK. AI-origin proposals without verified code interpretation cannot become
ready_for_resolve through distillation. Legacy route checks remain compatible.

Validation: 276 tests, 275 passed and one optional-jsonschema skip. The saved
5,000-case development replay still matches all existing gold outcomes: 2,400
supported interpretations and 2,600 expected ASK cases, zero regressions. There
are 1,007 distinct current sentences; many contexts repeat memory templates.
All 5,000 legacy routes remain ASK without production calibration. New grammar
features are covered by targeted tests, not 5,000 independently labelled grammar
examples. This is not a new accuracy sample or production calibration.

Evidence: evidence/read-interpretation-1. Walkthrough:
reports/read-interpretation.html. Historical evaluations remain unchanged.
