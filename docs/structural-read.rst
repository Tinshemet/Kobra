Structural READ and sentence-local references
============================================

RuleAssigner v2 keeps the previous simple-role path first. On abstention it tries
bounded imperative coordination. This is a selective extension, not a claim to
implement all English grammar or all rules in any reference.

Sources and design basis
------------------------

Universal Dependencies coordination distinguishes verbal from nominal conjuncts,
including comma-only coordination and shared dependents:
https://universaldependencies.org/u/dep/conj.html

Enhanced dependencies describe explicit propagation of shared arguments and
relative-clause referents, while noting that private versus shared complements
cannot always be inferred from basic syntax:
https://universaldependencies.org/u/overview/enhanced-syntax.html

Lee et al. (2013) describe precision-ranked deterministic coreference rules with
agreement constraints and entity-level information. Our small local rule is
inspired by this approach; it is not a reproduction of their full system:
https://aclanthology.org/J13-4004/

spaCy documents dependency-tree traversal and noun chunks. Its English parser's
labels are not interchangeable with every UD label, so the code uses the actual
spaCy labels and records limits rather than treating UD as executable code:
https://spacy.io/usage/linguistic-features#dependency-parse

Implemented rules
-----------------

* C010/C011: split supported imperative action coordination on syntactic predicates,
  preserving offsets and greetings. Commas inside an object list are not actions.
* C012: preserve counted groups with repeated "one with ..." specifications.
  Attributes remain source text, not a domain-specific image/type resolution.
  Count disagreement is explicit and prevents the code route from succeeding.
* C013: preserve an explicit "all in/on the same ..." modifier as a shared
  location constraint. No network, folder or other WORLD identity is invented.
* C015: retain the explicit quantity "all" in the patient noun phrase; other
  unsupported quantifier scopes continue to abstain.
* C014: bind it/them only to a single compatible earlier local object/group by
  number. Competing groups and absent antecedents remain explicit alternatives.

The original pronoun remains in the frame. local_references links its exact span
and frame/slot to an entity ID in local_entities. Those entities are sentence-local
descriptions, not claims of existing WORLD objects. Code-side links alone may
satisfy the gate's local reference check; model-supplied links cannot authorize
local IDs. Partial unresolved proposals remain rejected even if calibration is
supplied. The normal external calibration requirement still applies.

Chunk relations preserve textual coordination. Only explicit "then" yields an
explicit sequence marker; ordinary "and" does not create an execution dependency.
source_ledger reconstructs every original character on this structural path.

Limits and next rule families
----------------------------

This path abstains on negated/modal coordination, conditionals, relative clauses,
control/raising complements, alternatives using or/but, implicit shared objects,
and unsupported prepositional attachments. It currently supports at most four
predicates. General shared-subject propagation, full nominal-group trees, temporal
scope, reflexives, animacy-aware anaphora and conversational reference resolution
remain separate work. Pure number agreement is not a general semantic proof.

Regression examples and paired old-case replays are development evidence, not
fresh confirmation or calibrated natural-language accuracy. The older 11-slot
scorer does not score the newly added chunk metadata or local reference edges;
those require the explicit structural regression checks. No model calls are made.

Development results
-------------------

On the same 600 archived development cases, the old simple rules routed 371
cases to code and matched all 371 under the bounded slot contract. The structural
extension routes 387 and matches all 387: 16 additional correct cases, zero lost
correct cases. These are selected-subset results, not 100% accuracy over 600.
The other 213 cases still do not take the supported code route. This replay does
not establish reference-link or modifier accuracy; separate structural tests
check those new fields. First-run captures retain two failures caused by dropping
"all"; the follow-up quantity rule recovers both. No model calls were made.
