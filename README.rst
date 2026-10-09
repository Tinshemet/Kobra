Kobra
=====

Kobra is a development skeleton for an application-independent linguistic
pipeline: front door -> READ -> RESOLVE -> ROUTE. Execution belongs to the
calling application. Gorgon integration has not started.

Install with ``python -m pip install .``. Run the tests with
``PYTHONPATH=src python -m unittest discover -s tests -v`` and the wiring example
with ``python examples/minimal_client.py`` after installation.

Current contracts
-----------------

* ``ClientConfig`` identifies the client, configuration revision, vocabulary
  and available capability identifiers. The provisional contract version is 1.
* ``Services`` carries explicitly supplied model, context and policy providers.
  There are no environment lookups, application imports or default providers.
* ``FrontDoor.normalize`` produces a ``TextView`` with original text, working
  text, a Unicode-character boundary map and diagnostics for any transformation.
  ``EnglishFrontDoor`` preserves the existing English normalization rules using
  an explicit ``DomainVocabulary``. ``IdentityFrontDoor`` remains available for
  fixtures that need no normalization.
* ``Reader.read`` and ``Resolver.resolve`` accept client-defined result types.
  ``DistillingReader`` now returns source-bound prose points in a ``ReadResult``,
  with preserved noun/reason observations and possible-omission diagnostics.
  Full legacy READ migration and the RESOLVE representation remain future work.
* ``Router.route`` returns a reasoned ``RouteDecision``: ready, clarify,
  unsupported or refused. Ready decisions name a declared client capability.
  Ready means a route was selected, not that execution was authorized.
* ``Pipeline.interpret`` runs those stages in order and applies a supplied
  policy provider before returning. ``Interpretation`` exposes the request,
  view, reading, resolution, proposed route and final decision.

Provider errors propagate and stop processing. Missing optional providers are
represented by None; stages that need one must handle its absence explicitly.
Context lookup returns candidate IDs, with an empty tuple meaning unresolved.
Richer context provenance, semantic output schemas and serialization are pending.

Providers and stages are trusted application code. They must not dispatch tools
or mutate persistent state during interpretation; this skeleton is not a sandbox.
Stage implementations must preserve prior outputs if they use mutable result
types. Frozen result containers do not deeply freeze client-owned objects.

The example uses an exact-match fixture, not a parser or date resolver. Tests
exercise coordination and contract invariants, not linguistic accuracy or full
compatibility with Gorgon. The API is provisional and may change before v1.

Earlier extracted component
---------------------------

``clock_in`` and ``clock_tail`` remain available independently. They preserve
Gorgon's original behavior, including recognizing invalid times such as 29pm.
They do not validate dates, schedule actions or participate in the new pipeline.
Their original provenance is in evidence/provenance.json; initial-review.json
records only that earlier extraction, not this skeleton.

Next work
---------

Stage 1 direction was accepted on 2026-10-07. The twelve worked examples in
``docs/distillation-examples.rst`` remain development material. The original
draft and review records are preserved in place. The immutable types in ``kobra.distillation`` validate evidence and
links, not semantic correctness. The draft has not been approved as gold.

The front-door implementation now runs without Gorgon imports. Compatibility
checks compare text, offsets and notices with 542 captured source cases, plus
cross-domain isolation checks. This is bounded compatibility evidence, not a
claim of linguistic accuracy. See ``evidence/front-door-review.json``.

Kobra owns the Medusa language. New program authoring goes through the pipeline;
execution of an existing Medusa program is outside it. See
``docs/architecture-decisions.rst`` for the agreed boundaries.

Original-offset tracking is now connected to READ distillation. Next, generalize
the remaining existing READ helpers, then build constrained RESOLVE and
security-focused ROUTE. Persistence,
execution, host integration and concrete policy ownership stay with each client.
Serpent remains an independent evaluation-data producer, not a runtime dependency.

Using the English front door
----------------------------

Supply exact lowercase noun forms (including plurals), operation words, status
values and known object names. No Gorgon vocabulary is enabled implicitly::

    from kobra import (ClientConfig, DomainVocabulary, EnglishFrontDoor,
                       Request, Services)

    front = EnglishFrontDoor(DomainVocabulary(
        nouns=frozenset({"report", "reports"}),
        operations=frozenset({"send", "compare"}),
        statuses=frozenset({"approved", "pending"}),
    ))
    view = front.normalize(Request("um, compare the reports"),
                           Services(ClientConfig("documents", "1")))
    assert view.text == "compare the reports"

Pass this front door to Pipeline in place of IdentityFrontDoor. Vocabulary is
bound to the front-door instance; Services.config.vocabulary is not implicitly
merged because the current flat field does not distinguish linguistic roles.
The language remains English, and inherited denoising heuristics may still be
wrong on unfamiliar input. Original text and notices remain available for review.

READ's distilled-output path
---------------------------

``DistillingReader(vocabulary=front.vocabulary)`` can replace a fixture reader in
Pipeline. Supply a ModelProvider through Services.model. The provider proposes
prose points and exact quotations; Kobra assigns IDs and maps their evidence to
the original request. READ returns ReadResult, including immutable Distillation,
normalization notices, source bindings, linguistic observations and uncited text.

Run ``python examples/read_distillation.py`` after installation for an offline
example using an authored response. No real inference is performed by that demo.
See ``docs/read-implementation.rst`` for the response contract and current limits.
These checks establish source binding and structure, not model accuracy or full
semantic coverage. RESOLVE and ROUTE implementations remain separate work.

Experimental code-first READ
----------------------------

``kobra.rule_assignment.RuleAssigner`` assigns supported grammatical roles in
code using a learned dependency parser. ``kobra.confidence_gate.GatedRuleReader``
adds an optional ambiguity resolver and external confidence/ASK gate. No held-out
calibration is currently installed; uncalibrated proposals go to ASK. See
``docs/external-confidence.rst`` and ``docs/rule-assignment.rst``.

Batch tooling supports Serpent 1.2.0 pre-reader context annotations and explicit
filters. Serpent remains an evaluation dependency, not a runtime READ provider.
