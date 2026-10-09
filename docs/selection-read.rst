Candidate-selection READ pilot
==============================

SelectingReader is an experimental Reader implementation. Code generates all
contiguous source spans with lexical endpoints, assigns candidate IDs and keeps
their normalized and original offsets. The model receives the sentence and
candidate table, and calls select_read with flat scalar selections. It does not
write evidence quotations, offsets, node IDs or the final interpretation JSON.
Code validates the selections and constructs SelectionReadResult. No tool is
executed against an external application.

The slots are speech act, predicate, agent, patient, recipient, negation,
condition, time, quantity, attribution and modality. Multiple tool calls in one
model response represent multiple actions (maximum four). NONE marks an absent
slot; UNKNOWN and MISSING preserve unresolved decisions. A source candidate can
also be marked unrepresented. The original request accompanies the result.

This is a bounded sentence-level prototype: at most 32 lexical/punctuation
source tokens, contiguous spans only, and no full nested-clause interpretation,
coreference resolution or world reasoning. A long condition or attribution can
be retained as source text without extracting all of its internal meaning.
All lexical spans are candidates; no gold answers or application-specific noun
or verb lists are used to create them. Candidate enumeration is quadratic, so
its scalability to paragraphs is not established. Source IDs prevent fabricated
quotations but do not prevent wrong choices or attachments.

Development and frozen test
---------------------------

Two development inputs (Close the gate; Never paint the door) were used to check
the transport before the 50-case test. The initial nested frames interface
produced stringified arrays. Version read-selection-2 uses flat tool arguments;
code constructs the arrays. Native tool calls follow Ollama's documented API:
https://docs.ollama.com/capabilities/tool-calling (accessed 2026-10-09).

The fixed fixture is tests/fixtures/selection-50.json, authored before inference.
It contains five sentences in each of ten groups: simple clauses, questions,
negation, conditions, time, quantity, attribution, modality, coordination and
voice/reference. Expected values and acceptable noun-phrase variants were fixed
before the run. These are agent-authored references, not independent human gold
or a representative random sample of real requests. Explicit modal declaratives
are classified as assertions under this contract; pronouns are preserved as
source phrases rather than resolved. Some such choices admit other contracts.

Run from the repository::

    PYTHONPATH=src python tools/evaluate_selection.py \
      --output evidence/a-new-selection-run

The runner uses llama3.1:8b by default, one request per sentence, temperature zero,
seed zero and no retries. IdentityFrontDoor isolates selection from normalization
changes. The output directory must be new. It stores the frozen reference,
source hashes, model identity, complete tool requests/responses, candidate
inventories, bound results, per-case scores, errors and timings. Gold is excluded
from model requests. The code checks that source hashes remain unchanged.

Measurement
-----------

Exact-case slot accuracy requires every frame and all eleven slots to match a
predeclared reference alternative, with no unrepresented content or extra frame.
Frame order is ignored through exhaustive one-to-one alignment (at most four
frames). Missing/error cases stay in the 50-case denominator. No model judge or
post-hoc semantic repair is used.

Slot agreement counts correct assignments, including correctly absent slots.
It can look optimistic when many slots are absent, so it is secondary to exact
cases. Required-slot retention excludes absent reference slots; it does not
measure all meaning preservation. Candidate coverage reports how many required
source-slot values were available before selection, separately from how many
the model selected correctly. Extra frames incur extra slot errors. The same
agent reviews output failures; that is not an independent audit.

These metrics cannot establish the overall >99% meaning preservation and >95%
READ accuracy targets. Fifty examples are a diagnostic pilot. A new independently
reviewed confirmation set is needed after using these errors for development.

Observed 50-case result, 2026-10-09
----------------------------------

The run in evidence/selection-50-20261009 completed with exit status 0 and all
source hashes unchanged. This exit status means capture completed, not quality
passed. The model was llama3.1:8b; see manifest.json for the exact digest and
server identity. All 50 raw responses were replayed offline and all scores
matched, without another model call.

* Exact-case slot accuracy: 0/50 (0%).
* Accepted selections: 27/50 (54%); 23 rejected.
* Raw responses containing native tool calls: 45/50 (90%).
* Slot agreement: 223/605 (36.9%), including absent slots.
* Required-slot retention: 47/226 (20.8%); not full meaning preservation.
* Candidate coverage: 171/171 required source-slot values available (100%).
* Median model/request time: 5.10 seconds; total: 278.11 seconds.

Eighteen cases selected words or invalid IDs outside the permitted ID list;
five failed to produce the expected native tool-call structure. Among accepted
cases, source/role selection remained poor. For example, Open the window chose
Open as predicate but the as patient. Lena repaired the bicycle selected repaired
the bicycle as predicate and the entire sentence as agent. No accepted case had
all reference slots correct, even before penalizing unrepresented content.

The unit command was PYTHONPATH=src python -m unittest discover -s tests -v:
exit 0, 87 run, 86 passed, 1 optional schema-library check skipped. Its log is
in evidence/selection-development-20261009/tests.log. These unit results do not
measure model quality. The first offline audit attempt encountered a tuple/list
serialization comparison mismatch; comparing JSON-normalized dataclasses resolved
that audit-only issue. Neither captured predictions nor scores changed.

The pilot does not support this implementation as a reliable READ replacement.
It demonstrates that generating a tool call and selecting correct linguistic
arguments are different capabilities. The exhaustive candidate inventory had
coverage, but its opaque IDs and many overlapping spans may burden selection;
that explanation is a hypothesis, not an established cause. Future interface or
candidate-ranking changes should preserve this run and use separate development
and confirmation data. No 99%/95% achievement is claimed.
