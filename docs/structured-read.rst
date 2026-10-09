Source-grounded linguistic READ prototype
========================================

Status (2026-10-09): experimental implementation, semantic targets unestablished.
The user's targets are greater than 99% meaning preservation and greater than
95% accuracy. Keeping the original text, citing every token, passing schema
validation, and passing unit tests do not establish those targets.

Construction
------------

StructuredReader implements the existing Reader protocol. It makes one complete
request call through Services.model, then binds the returned graph to TextView.
Nodes carry linguistic categories and exact source quotations; edges carry
directed attachments and their own evidence. Kobra owns identities and offsets.
The model cannot introduce paraphrased propositions into the authoritative graph.
Uncertainty text is model-authored commentary, not an established proposition.
Every relationship, including one with status ``proposed``, remains unverified.

Supported categories cover speech acts, predicates, participants, negation,
conditions, exceptions, quantities, time, modality, attribution, quotations and
references. Multiple uncertain reference edges can preserve alternatives. This
prototype does not yet represent mutually exclusive whole-graph readings.
Unsupported categories use an unrepresented node or unknown relationship and
produce diagnostics. Original input always accompanies the graph to RESOLVE.

The binder rejects invalid categories, fabricated quotations, invalid occurrence
numbers, self-links, duplicate relationships, dangling links, and size violations.
Transport errors propagate. There are no silent repairs, retries or world lookups.
Uncited-node text is a lexical omission signal. Edge citations cannot mask missing
node evidence. A blanket node quotation can still conceal semantic omissions;
there is no completeness or entailment proof.

Local decoder compatibility (2026-10-09)
---------------------------------------

The first failures were traced to the local Ollama 0.30.7 runner's grammar
parser: large maxLength/maxItems values generated repetition counts rejected
with ``number of repetitions exceeds sane defaults``. The runner then continued
without its grammar. Minimal user/role/schema probes succeeded; this evidence
does not support changing the chat template. Logs and probes are retained in
``evidence/provider-diagnosis-20261009``.

OllamaProvider now omits maxLength/maxItems >= 2000 from the decoding schema
only. READ's original schema and deterministic binder limits remain unchanged.
Large minimum bounds fail explicitly. Both schemas and the projection version
are saved in exchanges. This permits a generated over-limit response, which
the binder must reject; it does not permit acceptance of over-limit content.
Types, required fields, enums and ordinary bounds still constrain decoding.

An upstream report documents this same failure mechanism:
https://github.com/ggml-org/llama.cpp/issues/25923 (2026-07-20, accessed
2026-10-09). An alternative is replacing/upgrading the shared runner; the narrow
provider projection avoids changing other local applications or source limits.
Its hypothesis is rejected if the projected schema still causes parser errors
or the application accepts data exceeding the original limits.

Using the reader
----------------

Import StructuredReader from kobra and supply it as Pipeline.reader, using the
same front door, model provider, resolver and router interfaces as the baseline.
The resolver must accept StructuredReadResult; a resolver specific to the prose
ReadResult requires an explicit adapter. No default pipeline is silently changed.

The capture runner supports three choices::

    PYTHONPATH=src python tools/read_serpent.py \
      --exam evidence/serpent-general-assistant-exam.json \
      --output evidence/my-new-structured-run --reader structured

Use ``--reader distillation`` for the existing baseline and
``--reader structured-hints`` for extraction with the existing fallible noun and
reason observations. Each run needs a new output directory. Captures include
source hashes, reader choice, model identity, prompts, schema, raw responses,
errors, elapsed time and bound results. No semantic score is manufactured.

Design evidence and alternatives
-------------------------------

The prior discussion's research was reread and these primary sources rechecked
on 2026-10-09:

* Geng et al. (EMNLP 2023), Grammar-Constrained Decoding for Structured NLP Tasks
  without Finetuning, https://aclanthology.org/2023.emnlp-main.674/.
  Supports testing constrained structured extraction. Its tasks do not establish
  Kobra's request-level semantic accuracy. Supplying a schema is also distinct
  from proving semantic constraints during decoding; backend support matters.
* Gashteovski et al. (EMNLP 2017), MinIE: Minimizing Facts in Open Information
  Extraction, https://aclanthology.org/D17-1278/.
  Its semantic annotations motivate retaining qualifications explicitly; no MinIE
  implementation, published score, or coverage claim is imported here.
* Ollama structured-output documentation, accessed 2026-10-09,
  https://docs.ollama.com/capabilities/structured-outputs, recommends including
  the schema in the prompt as well as the format field. The first local smoke
  capture returned prose for all three requests despite the format field.
  Prompt version read-linguistic-2 consequently includes the explicit JSON
  schema. The version-1 failure captures remain preserved separately.

After repairing decoder compatibility, version 2 produced schema-shaped JSON
but still quoted instructions and used nonexistent source occurrences. Version 3
replaces the repeated schema in the prompt with a compact extraction contract
and a worked prohibition example. Its initial three development cases still
include quotation and attachment failures. This is an experimental prompt,
not a validated improvement in complete-request accuracy. All prompt versions
are recoverable from the saved raw exchanges.

Direct prose distillation is already available, easier to express arbitrary
content with, and remains a serious baseline. Its risk is unsupported rewriting.
Structured extraction trades that freedom for inspectable attachments; its risks
are incorrect attachments, representation gaps, larger outputs and truncation.
Adding linguistic hints may reduce misses, but can bias extraction toward bad
candidates. A large hand-written grammar migration is deferred until measured
errors justify particular rules. If the structured alternatives fail to improve
faithfulness at comparable coverage and acceptable latency, the hypothesis is
rejected. The research motivates an experiment, not a performance guarantee.

Proposed semantic acceptance contract
------------------------------------

These definitions are a proposed operationalization of the user's targets, not
an assertion that the earlier Gorgon declaration scorer measures all meaning.
Freeze a reviewed reference set and contract before comparing model outputs.

* Meaning preservation: correctly retained reference meaning units divided by
  all required reference units. A unit includes its polarity, scope, attribution,
  conditions and quantities as applicable. Merely retaining its words or marking
  it unrepresented does not count as successful extraction.
* Accuracy: fully correct requests divided by all requests in the sealed set.
  A fully correct request preserves required meaning, adds no unsupported claims
  or relationships, and handles ambiguity according to the reviewed reference.
  Errors, missing outputs and unjustified abstentions remain in the denominator.
* Also report unsupported additions, attachment errors, unresolved rate, lexical
  coverage, per-feature outcomes, latency and token usage separately. Real
  ambiguity preserved correctly need not be penalized as an abstention.

Report numerators, denominators, uncertainty intervals, split, contract/model
identity, and independently reviewed references alongside any headline. Use
fresh confirmation cases after development. The existing student-only exam
contains inputs, not an independently reviewed semantic gold set for this new
graph. Small smoke captures cannot establish either target. Direct distillation
and graphs require assessment against the same meaning-level reference, rather
than comparison of their incompatible output schemas.

Verification
------------

Run ``PYTHONPATH=src python -m unittest discover -s tests -v`` from this repository.
The added tests exercise invalid source binding, wrong references, uncertainty,
normalization, overlapping quotations, omission diagnostics, failure propagation,
hint ablation and pipeline handoff. They use hand-authored provider replies, not
model predictions. A deliberately wrong but source-grounded attachment is accepted
with semantic_review=not_evaluated to document the boundary of these checks.
