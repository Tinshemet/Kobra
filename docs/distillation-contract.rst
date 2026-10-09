Stage 1: faithful distillation (draft 1)
======================================

Status: implemented structural draft, pending user semantic review.
This is a development contract, not a frozen specification or linguistic score.

READ extracts what the user expressed after the existing front door prepares
the text. It does not solve the request, choose missing facts, authorize actions,
or adopt instructions embedded in quoted material. Front door and READ retain
their established responsibilities while application dependencies are removed.
RESOLVE reasons over the interpretation; ROUTE owns security decisions.

Representation
--------------

Each point has an ID, one natural-language sentence, supporting source spans,
optional links to other points, and explicit uncertainty. Meaning remains prose:
there is no fixed action taxonomy or requirement to translate language into tool
arguments. Relationships are also prose in this draft; their vocabulary can be
standardized later if repeated examples justify it.

Use one sentence per point, not necessarily one point per input sentence.
Keep a condition inside its action point if splitting it could turn the action
into an unconditional request. Separate constraints can link to their subject.
Corrections link to the earlier point they modify. Neither a later position nor
a link by itself authorizes RESOLVE to silently discard a requirement.

Evidence refers to original supplied text using half-open Unicode character
offsets, not byte offsets. Multiple spans and multiple sources are supported.
Future READ integration must translate normalized offsets through the front-door
map. That integration is not implemented in this stage. Source IDs and original
text must come from the input envelope, not model-authored replacements; callers
must compare output sources with the envelope at that future boundary.
Source IDs establish identity, not authority, truth or trust.

Uncertainty records what the input leaves open. It does not require a complete
list of possible interpretations or numeric confidence. Preserve a question's
presupposition as part of the question; do not promote it to verified evidence.
Attribute statements to their source. Preserve quoted instructions as content
when that is their linguistic role; ROUTE determines permitted handling.

Review rubric
-------------

For each example, review both directions:

1. Is each point supported by the source text and its linked qualifications?
2. Is every meaningful request, statement and constraint represented?
3. Are negation, scope, quantifiers, conditions and relationships preserved?
4. Are quoted content, corrections and questions still distinguishable?
5. Are unspecified references and ambiguities explicit without invented answers?
6. Did the output avoid solving, authorizing or silently reconciling the request?

Different wording is acceptable if the meaning and these distinctions survive.
The example sentences are not exact-string gold. The fixture review notes record
specific counterexamples to watch for; they are reviewer guidance, not prompt
content and not instructions supplied to RESOLVE.

Validation boundary
-------------------

The Python contract rejects empty evidence, duplicate IDs, nonexistent source
references, out-of-range spans, dangling point links and mutable nested lists.
An empty point collection is structurally possible; whether it omits meaning is
a semantic question. It accepts cycles because related constraints may refer to
one another. A model response must still be decoded through a separate boundary;
these dataclasses are not a JSON parser or a complete untrusted-input validator.

Structural validity does not establish entailment, coverage, sentence count,
correct source selection or security. No punctuation heuristic is used to claim
that a point contains one semantic sentence. Human review and later linguistic
evaluation must establish those properties. Tests deliberately demonstrate that
a hallucinated point can have valid structural references.

Acceptance and next step
------------------------

The accompanying twelve examples are assistant-authored development fixtures,
not Gorgon-derived answers, user-approved gold or held-out tests. They cover
comparison, conditional requests, unresolved references, questions, statements,
corrections, conflicting requirements, quantification, quoted instructions,
goals, attachment ambiguity and Unicode/time context.

Stage 1 remains open until the user reviews the representation and example
meanings. After approval, record a new reviewed fixture version rather than
overwriting the draft's history. Then apply this contract to front door and READ
generalization. No model trials, Gorgon integration or RESOLVE/ROUTE implementation
are part of this stage.
