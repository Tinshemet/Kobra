READ: distilled-output path
===========================

Status: first operational boundary, not a completed migration of Gorgon's READ.

An experimental source-grounded linguistic alternative is now available as
StructuredReader. See structured-read.rst for its graph contract, comparison
runner and proposed semantic acceptance criteria. DistillingReader remains the
prose baseline described here.

DistillingReader accepts the existing TextView and calls an explicitly supplied
ModelProvider once. The provider proposes natural-language points with exact
evidence quotations, point relationships and uncertainty. It receives the entire
normalized request so conditions and scope are not lost through isolated calls.
The prompt version is read-distillation-1; changes require new evaluation data.

The structured wrapper does not prescribe which objects, goals, statements or
relationships the language may express. Their content remains prose. Kobra owns
point IDs and source text; a provider cannot supply replacements for those fields.

Evidence binding
----------------

The model identifies exact quotations and zero-based occurrence numbers. This
avoids asking it to calculate character offsets; code locates each occurrence,
including overlapping matches, and projects its boundaries through the front
door map. Nonexistent evidence and evidence solely inside inserted characters
are rejected. Each point retains original source spans; ReadResult also keeps
the TextView, normalized boundaries and front-door notices for inspection.

The original source is the supplied request. A model proposal cannot rewrite it
or claim evidence from an unsupplied source. The front-door map is trusted stage
output; its semantic correctness is not re-proved by READ. Mapped intervals may
contain removed text between boundaries. Multi-source and conversation inputs
remain future work; external context is not looked up by this reader.

Validation and omissions
------------------------

Missing/extra fields, wrong types, invalid links, fabricated quote locations and
configured size violations reject the whole proposal with ReadContractError.
Provider failures propagate instead of becoming an apparently successful empty
interpretation. There are no automatic retries or fallback answers. Transport
timeouts and output-token limits must be implemented by the provider adapter.

Uncited alphanumeric input is reported in ReadResult.uncovered as a lexical
omission signal. This can expose a dropped prohibition or condition, but does
not establish completeness: a point can cite the entire prompt and still
misrepresent it. No-point output for nonblank input also gets an explicit
diagnostic. These results are not automatically authorized or semantically
approved. RESOLVE must receive the full ReadResult, including its diagnostics.
Blank normalized input skips the model; original input and front-door notices
are still retained, including when denoising removed the original content.

Every result reports semantic_review = not_evaluated. The implementation does
not claim to detect all contradictions, instructions hidden in quoted material,
false entailments or missing meaning. One sentence per point remains a semantic
requirement; punctuation counting is not used as a substitute for that check.

Relationship to existing READ
-----------------------------

Gorgon's pass1.run_scanned returns Declared object rows, while read_and_settle
mixes extraction with world lookup, learned knowledge and kind resolution. An
unchanged call to either is not a faithful implementation of Kobra's complete
distilled-point contract. The existing anchor-and-scan approach is a useful
precedent for separating model proposals from deterministic grounding.

The ported front-door and clause-boundary rules remain unchanged in this
work. The original scan.anchors_in and reasons.read helpers are now ported too,
with their rule bodies preserved and noun vocabulary supplied explicitly instead
of through Board. They supply noun anchors and cause/concession/purpose candidates
to the provider and remain visible in ReadResult.observations. Their heuristics
are fallible; candidates do not force points or become established facts.
Fifteen captured source cases check this bounded relocation. Other READ scanners
and specialized linguistic readers have not been replaced or declared obsolete.
This new output boundary is the integration
target for their incremental generalization; it is not a claim that a new
prompt reproduces their behavior. Directly copying read_and_settle would import
RESOLVE responsibilities. Forcing its object rows into prose would lose parts
of the broader request. Those alternatives were therefore not used for this
first boundary.

Checks and next work
--------------------

Tests inject hand-authored provider responses, including the twelve draft
examples, to check binding and rejection behavior. They are not model-generated
predictions or an accuracy benchmark. The earlier 542-case front-door regression
checks continue to run. No live model service is called.

Next, generalize the remaining READ object/relation extraction helpers,
connect their evidence to this boundary, and evaluate real small-model outputs
against independently reviewed examples. No world resolution, security decision,
Medusa compilation or downstream execution is implemented in this reader.
