External confidence and ASK routing
===================================

GatedRuleReader is an opt-in experimental wrapper around RuleAssigner. It builds
a code proposal first; unsupported sentences may invoke a caller-supplied resolver
with the source, code proposal, WORLD records and history. Its output then passes
through ConfidenceGate. Resolver exceptions or absent answers result in ASK.
The wrapper returns an ASK handoff record, not an executed user interaction.

The model's reported confidence is ignored. Confidence comes from an identified
held-out cohort: correct/total counts produce a 95% Wilson lower bound. The
default threshold is 0.95 with at least 100 calibration cases. This is a cohort
reliability bound, not a sentence-level probability. The caller selects a cohort
from trusted pipeline provenance, never from a model field. Development evidence
(including 280/280 reused cases) is rejected as calibration. No empirical held-out
calibration has been installed; current uncalibrated cohorts route to ASK.

Schema shape, literal source grounding, UNKNOWN/MISSING slots, required context,
nonexistent WORLD IDs and application-supplied rule validators are checked before
acceptance. Recognized pronoun/demonstrative arguments require an explicit binding
to an existing WORLD ID. A valid ID proves existence, not that the model chose the
right entity. Calibration and independent semantic validators are still needed.
The validator interface is an extension point, not a complete semantic verifier.
No unknown proposition can be proven correct merely by satisfying the schema.

Serpent integration
-------------------

The READ batch generator requires Serpent 1.2.0 and writes independent context
requirements and context-exclusions sidecars before any inference. Default policy
is account: nothing is excluded for needing context. Optional --context-policy
self-contained or read-resolvable and --max-ambiguity operate before selection;
the manifest records the filter and all excluded cases are retained. Inputs sent
to READ remain only ID and source text. The evaluation summary breaks down exact
extraction scores by context requirement; it does not automatically excuse an
incorrect extraction or reinterpret historical scores as correct ASK handling.

A separate benchmark of appropriate ASK versus unnecessary ASK, with supplied
history/WORLD and held-out calibration, remains necessary. No new accuracy claim
or fresh model run was made while implementing these changes.

Three-way correctness evaluation
-------------------------------

``tools/evaluate_routing.py`` consumes saved result records alongside independent
gold (never sent to the reader). It reports correct_code, correct_AI and
correct_ASK, plus wrong code/AI, unsafe acceptance, unnecessary ASK and ASK with
an unrelated justification. Correct ASK requires a predeclared context/ambiguity
reason to match; a timeout alone is not a correct diagnosis of missing context.
Grounding IDs are scored as well as grammatical slots. ASK precision and recall
are reported separately; routing every input to ASK cannot produce a passing
score. The gate wrapper records whether a proposal came from code or AI.

Tests exercise all three routes and the error categories with fixture resolvers
and explicitly synthetic calibration. These are contract tests, not measured AI
accuracy. No live three-way accuracy or held-out calibration is claimed.
