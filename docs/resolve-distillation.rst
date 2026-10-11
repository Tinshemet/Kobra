Deterministic distillation for RESOLVE
======================================

The new resolve-distillation-1 contract projects the current gated READ result
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
linguistic distinction, including all tense information. The summary must never
be used as a replacement for the source-backed structured point.

Evidence for simple clauses covers the full source. Supported structural frames
use exact chunk spans plus shared-argument spans. Multiple frames without a
trusted chunk map use full-source support rather than invented offsets. Unmapped
relations and unsupported groundings produce diagnostics; invalid frames preserve
source as unresolved text. ready_for_resolve requires upstream ACCEPT, usable
points and no distillation diagnostics. No new confidence or authorization is
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

The current output version is resolve-distillation-2. Existing points, grounding,
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
