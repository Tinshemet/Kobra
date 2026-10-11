READ rule coverage and closure checklist
=======================================

Checkpoint: 2026-10-11. This is a bounded engineering inventory, not an exhaustive
English grammar. A finite rule set cannot guarantee every natural-language
interpretation. New constructions must retain evidence and abstain explicitly.

Implemented or partially implemented
------------------------------------

* Surface boundaries: pure code; explicit action vocabulary and separators,
  protected quotes/brackets, complete source ledger. Tests: test_surface_chunks.
  Missing: general sentence segmentation, lexical noun/verb disambiguation,
  nested clause trees and unbounded coordination.
* Basic roles: active, passive, adjective-state and simple speech acts through
  learned dependency candidates plus code rules. Tests: test_rule_assignment.
  This is not yet a parser-independent role system.
* Imperative coordination: up to four explicit actions; counted member lists,
  shared-location constraints, explicit all, local it/them number agreement.
  Tests: test_structural_read. Bounded shared-patient patterns are implemented (shared-patients.rst); general shared arguments and subject propagation,
  animacy, reflexives and competing antecedents need further work.
* Context evidence: previous turns, WORLD records and attributed claims retained.
  Tests: test_context_ledger. Automatic conversational binding is not implemented.
* Validation: shape/source grounding, known reference IDs, trusted local links,
  external cohort gate. Existing routing tests distinguish code, scripted AI and
  appropriate ASK. Structural validity alone cannot prove meaning is correct.

Next rule families, in implementation order
-------------------------------------------

1. Coordination trees and scope: distinguish nominal lists, verbal clauses,
   shared arguments, alternatives and corrections. Preserve and versus then;
   never infer execution order from plain conjunction.
2. Negation, modality, conditions and temporal clauses: explicit scope edges,
   including nested combinations. Current command path abstains on these.
3. Attachment and distribution: prepositional phrases, each/all/both, units,
   ranges, member-specific versus group-wide attributes. Preserve competing
   attachments until evidence selects one.
4. Local references: number plus entity type/animacy, reflexive constraints,
   demonstratives, possessives and antecedent competition. Evidence and rejected
   alternatives must remain inspectable; recency alone is insufficient.
5. Complement and relative clauses: control/raising, quoted or reported content,
   attribution and ellipsis. Embedded instructions must not become top-level acts.
6. Cross-turn role/context resolver: constrained candidates from current text,
   retained turns and WORLD. No invented candidates; invalid or insufficiently
   supported selection becomes ASK. The current resolver interface still accepts
   a general proposal, so restricting its contract remains necessary.
7. Fragment recovery and correction: preserve incomplete instructions and repair
   links across turns, with an ASK handoff that records the missing distinction.

References and use
------------------

UD is a descriptive syntax reference, not executable parsing rules. Use its
coordination and dependent-clause distinctions to design explicit structures:
https://universaldependencies.org/u/dep/conj.html
https://universaldependencies.org/u/overview/complex-syntax.html
https://universaldependencies.org/u/overview/enhanced-syntax.html
https://universaldependencies.org/u/dep/parataxis.html

Coreference agreement and ordered conservative decisions are informed by Lee et
al. (2013), not a reimplementation of that system:
https://aclanthology.org/J13-4004/

The remaining learned dependency component is documented at:
https://spacy.io/usage/linguistic-features#dependency-parse

Acceptance criteria for closing READ
------------------------------------

* Freeze a declared supported grammar and JSON contract; unresolved structures
  must have source spans, reasons and preserved alternatives.
* Independently label complete structure, role/reference links and expected
  disposition before running Kobra. Serpent context metadata must remain separate
  from student inputs unless explicitly supplied as real context.
* Report correct code, correct AI, correct ASK, unnecessary ASK and wrong accepted
  interpretations separately. Source retention is an invariant, not semantic
  preservation. Score scope and links in addition to the legacy literal slots.
* Use reused cases for development ticks/regressions. Use new sealed cases for
  confirmation; never call fixture tests or repeated cases fresh accuracy.
* Evaluate at least 300 unseen cases per confirmation batch, stratified across
  instructions, services, questions, narration and context-dependent inputs.
  State denominator and exclusions. A 95% point score is distinct from a 95%
  Wilson lower bound; calibration must use separate held-out evidence.
* Pin implementation and vocabulary versions in calibration provenance, verify
  source retention, and make the constrained resolver contract enforceable.

READ is not closed at this checkpoint. The pipeline HTML shows actual outputs;
no live model or calibration was installed for the surface boundary change.

Knowledge integration checkpoint
--------------------------------

See knowledge-read.rst for active-library/archive lookup, candidate constraints,
legacy responsibility coverage and the remaining persistence/refresh/relations
gaps. This addition does not close grammar or general conversational resolution.

C016 checkpoint: bounded trailing shared patients now preserve one entity and
creation provenance through knowledge lookup. General shared arguments, scope,
modifiers and cross-turn bindings remain open.
