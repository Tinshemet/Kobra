Kobra implementation state: 2026-10-09
=====================================

Kobra is an experimental interpretation toolkit, not a fully connected assistant.
Pipeline defines front door -> READ -> RESOLVE -> ROUTE with explicitly injected
stages. It checks route capabilities and applies an optional caller policy.
There is no default production reader, concrete general resolver, memory service,
Medusa compiler, or executor wired into that pipeline.

The current experimental READ path is RuleAssigner + GatedRuleReader:
source -> dependency parser -> deterministic role assignment -> optional model
proposal on abstention -> external validation/calibration gate -> ACCEPT or ASK.
This wrapper is opt-in and uses its own read(text, ...) API, not a drop-in
implementation of the generic Pipeline Reader interface. The full earlier
candidate-arrangement reader and its character-by-character source ledger remain
available separately. Historical experiments used IdentityFrontDoor, so their
accuracy does not establish an integrated normalized multi-turn pipeline.

Earlier READ reuse
------------------

Reused linguistic code includes English front-door normalization/denoising,
clause/predicate-boundary helpers, noun-anchor scanning, cause/concession/purpose
observations, and standalone clock parsing. Client vocabulary is supplied
explicitly instead of through Gorgon's Board or planner. Source provenance and
bounded regression fixtures identify the extracted functions. Clock helpers
retain known limitations, including acceptance of invalid clock values.

DistillingReader retains the earlier source-bound prose output path, and
StructuredReader, SelectingReader and ArrangingReader retain subsequent
experimental alternatives. These are not all executed in sequence.

Not migrated: the earlier active library/archive, read_and_settle, automatic
learned-knowledge or WORLD lookup, persistent conversational state, or the full
set of old specialized readers. ContextProvider is a lookup interface. New
code-assignment rules and external gating are additions, not proof of complete
behavioral compatibility with earlier READ.

Context ledger
--------------

context_snapshot records supplied history with stable turn IDs, exact text,
roles and text hashes. It records supplied WORLD entities and source-span mentions
of their names. Those literal matches are not automatic identity resolution.
Explicit caller claims must cite exact prior-turn spans and carry a reported,
confirmed_by_client, disputed or superseded status. Corrections can link to a
recorded replacement without deleting old evidence. No claim extraction or truth
confirmation is performed automatically.

GatedRuleReader records this snapshot on every outcome, including ASK and model
failure, and sends a separate copy to its optional resolver. Resolver mutation
cannot alter retained evidence or the WORLD IDs subsequently checked by the gate.
The client must resupply or persist this context. There is no database, archive
retrieval, automatic fact promotion, or automatic append of each completed turn.
The per-input source ledger and this prior-context ledger have separate purposes.

Confidence and evaluation
-------------------------

The gate ignores model confidence, checks source/WORLD grounding, supports caller
semantic validators, and requires held-out cohort calibration. None is installed,
so it currently abstains on uncalibrated cohorts. ASK is a handoff result, not an
implemented dialogue that asks, receives an answer and retries automatically.
Three-way evaluation distinguishes correct code, correct AI and justified ASK
from wrong accepts, unnecessary ASK and unrelated failure-based ASK. Contract
tests are not empirical model accuracy. The 97.67% result remains a reused-data
routing simulation with saved model answers, not a fresh multi-turn evaluation.

Structural extension (rule-assignment-2)
--------------------------------------

A fallback rule pass now parses bounded imperative coordination, counted member
specifications and explicit shared-location constraints. Unique compatible it/them
references link to earlier sentence-local descriptions, without creating WORLD
objects. Chunks retain original spans and a complete character ledger. Ambiguous
links and unsupported structures remain unresolved. See structural-read.rst for
primary references, regression evidence and the deliberately limited rule scope.
