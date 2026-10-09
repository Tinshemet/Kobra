Candidate-first READ with lossless source retention
==================================================

ArrangingReader uses code-selected linguistic candidates and a single batched
model arrangement request. LinguisticCandidates runs spaCy's en_core_web_sm POS,
syntactic dependency, noun-chunk and entity pipeline locally. These are learned,
fallible annotations, not guaranteed grammatical truth. Code proposes verb/state
and particle spans, noun phrases and heads, and qualifier spans for negation,
conditions, time, quantities, attribution and modality. It does not consult the
50-case gold file or maintain a corpus-specific verb/noun dictionary.

The previous reader generated all possible source substrings. This version
narrows each role's menu and uses readable source phrases as selection labels.
Repeated identical phrases receive explicit location suffixes. Candidates retain
unique IDs and offsets internally. The LLM arranges the proposed pieces into
main-action frames through flat arrange_read tool calls; code builds the output
and source bindings. It cannot introduce an unlisted candidate. No application
action is executed.

Alternative considered: hand-build a verb/noun lexicon and heuristics. A trained
parser was chosen to avoid limiting candidates to a manually maintained domain
vocabulary. Its failure mode is incorrect POS/chunking or missing qualifier
spans, which candidate-coverage measurements expose. The previous exhaustive
span generator had full candidate coverage but poor selection. Narrowing menus
can improve arrangement or remove a needed option; the same 50-case comparison
measures both. It does not isolate the separate effects of parser, readable
labels and prompt examples.

Primary references, checked 2026-10-09:

* https://spacy.io/usage/linguistic-features documents learned POS/dependency
  annotation, noun chunks and token offsets. It supports the candidate-building
  mechanism, not a Kobra accuracy claim.
* https://spacy.io/models/en documents the English model pipelines.

Nothing is discarded
--------------------

The result contains the original Request (including conversation_id), the full
TextView and normalization mapping, proposed candidates, arranged frames,
diagnostics, the parsed model proposal when available, and a source ledger.
The ledger partitions every original character, including whitespace,
punctuation, unselected content and content removed by normalization.
Concatenating its fragments must reproduce Request.text exactly.

Fragments carry provisional labels: arranged, unassigned_meaningful,
possibly_missing_context, noise_candidate or garbage_candidate. Those labels
are bookkeeping hypotheses, never deletion instructions. Even punctuation and
replacement/control characters remain unchanged. Frame/slot references indicate
which arranged selections cover each source fragment. An arranged reference is
not proof of correct interpretation. Missing context can become clear in a
later turn; ASK decides whether clarification is needed. This reader does not
implement ASK, persistent conversation storage or world-reference resolution.

Parser errors, provider failures and invalid selections return needs_review with
all original source retained. The error is explicit; no successful empty reading
is fabricated. Omitted model fields become UNKNOWN, not NONE, so other valid
selections can survive without assuming that omitted meaning was absent.
Invalid option strings still reject the proposed frame set; the parsed proposal
and complete source remain available for review. The result never claims
semantic approval.

The prototype remains bounded: source parsing is capped at 20,000 characters
(over-limit input is returned intact for review), at most four arranged frames
are accepted, and span candidates are contiguous. Nested conditions and reported
claims are retained as qualifier spans rather than a complete recursive semantic
graph. Candidate menus themselves may be incomplete. Source retention is not
meaning preservation or linguistic accuracy.

Running and reproducing
-----------------------

The optional candidates dependency installs spaCy; its English model is a
separate download. This session used an isolated .venv-candidates environment,
spaCy 3.8.16 and en_core_web_sm 3.8.0. Exact dependencies are saved under
 evidence/arrangement-development-20261009/environment.txt.

From the repository::

    PYTHONPATH=src .venv-candidates/bin/python tools/evaluate_arrangement.py \
      --output evidence/a-new-arrangement-run

The runner checks that the reference fixture hash matches the prior run. It
uses the same llama3.1:8b model, temperature 0, seed 0, 1024 output-token limit,
8192 context setting and IdentityFrontDoor. One request per sentence, no retries.
The original 50 expected answers are unchanged; this is a reused development
comparison, not fresh held-out evidence. Four separate development sentences
were used before freezing the new run. Prompt version 2 adds role examples after
version 1's development captures confused imperatives and argument roles.

The old slot scorer is imported unchanged. Comparison uses the same frame-slot
contract for both versions. Automatically retained leftover text is not itself
scored as a semantic error, because auxiliary words, punctuation and omitted
meaning cannot be distinguished by raw text coverage. The original baseline
also scores 0 exact cases with its explicit unrepresented flag ignored, so that
comparison convention does not improve the baseline headline. Gold remains
agent-authored rather than independently reviewed.

Artifacts include model/parser identities and hashes, a source snapshot, the
frozen reference, full native tool requests/responses, menus, results, source
ledgers, scores and latency. The runner verifies that source code did not change
mid-run. Candidate coverage is role-specific: a phrase available only under the
wrong role is counted as missing from the needed menu. Lossless source retention
and correct arrangement are reported separately.

Observed same-50 comparison (2026-10-09)
--------------------------------------

The command completed with exit status 0; all code hashes stayed unchanged.
Model digest and reference hash match the preceding selection run. Offline
replay matched all 50 bound results, source ledgers and scores, with no inference.
The captured output directory is evidence/arrangement-50-20261009.

============================== ============== ==============
Measure                        Previous       Candidate-first
============================== ============== ==============
Exact frame-slot cases         0/50 (0%)      15/50 (30%)
Correct slots                  223/605        387/605
Slot agreement                 36.9%          64.0%
Required-slot retention         47/226         132/226
Required-slot retention rate    20.8%          58.4%
Source-candidate coverage       171/171        169/171
============================== ============== ==============

The new ledger reconstructed all 1,487 original characters in 50/50 cases,
including all 13 rejected arrangements. That establishes exact text retention
on these inputs, not 100% semantic preservation. The new reader constructed
37 valid frame results; omitted fields are retained as UNKNOWN, so structural
acceptance alone is not a like-for-like measure of the old strict binder.

The provisional source ledger labels account for 801 arranged characters,
459 unassigned meaningful characters, 5 possibly missing-context characters and
222 noise-candidate characters. None are deleted. No garbage-category input
occurred in the 50-case fixture; separate tests cover control/replacement
characters, Unicode and whitespace. Automatic leftover labels have no gold
classification score and should not be treated as established linguistic facts.

Eleven failed arrangements put a phrase into an unlisted condition slot; one
selected an unavailable predicate, and one an unlisted patient. For example,
the model put tomorrow in both time and condition. Invalid proposals remain
stored in the result alongside the source rather than silently disappearing.
The narrowed menus missed the expected predicates Back up and Print in two
cases; their source text remains in the ledger. These are candidate failures,
separate from wrong choices among available options.

Exact cases by five-case group: simple 4, questions 1, negation 4, conditions 0,
time 0, quantity 2, attribution 1, modality 1, coordination 0, voice/reference 2.
Median request-plus-parser time was 4.05 seconds; total 204.68 seconds. The
98 passing unit tests (99 run, one optional jsonschema check skipped; exit 0)
include parser candidate checks, failure-path retention, missing-field handling
and Unicode/normalization round trips. Log: arrangement-development-20261009/
tests-final.log under evidence/.

Reproduce the offline verification with::

    PYTHONPATH=src .venv-candidates/bin/python tools/audit_arrangement.py \
      evidence/arrangement-50-20261009

The audit writes new report files and refuses to overwrite existing ones. Use
an artifact copy without those generated reports if repeating it. Source and
parser hashes must match the recorded run. This is a same-agent reproducibility
check, not independent reference validation. The 99% meaning-preservation and
95% accuracy targets remain unestablished.
