Meduza in the proposed RESOLVE architecture
==========================================

Recorded 2026-10-11. Meduza is the user's spelling; existing source modules use
Medusa. This records the missing design boundary, not a migrated compiler/runtime.

Ownership and the two paths
---------------------------

Kobra owns the language and program-authoring semantics, as already recorded in
architecture-decisions.rst. Gorgon owns concrete tools and downstream execution.
Their boundary remains versioned data, not imports of each other's internals.

New natural-language work:

    READ meaning and evidence
      -> RESOLVE objective, hypotheses and decomposition
      -> Meduza program construction and validation
      -> ROUTE approval of the proposed handoff
      -> executor, with per-call checks
      -> observations/verdicts returned as data to RESOLVE

Existing saved program:

    load program and pinned dependencies
      -> validate and ROUTE under current grants
      -> execute

Executing a saved program does not reinterpret its source as a new English
request. Reusing it still requires current applicability and execution checks.

RESOLVE's internal graph represents unknowns, alternatives and dependencies.
Meduza represents a selected executable procedure or a supported goal/check.
They have different jobs: the graph is not a second runtime language, and a
Meduza program cannot be used as a replacement for all unresolved reasoning.
Answers, attributed statements, ASK and unsupported results need not be programs.

Existing behavior verified by source inspection
----------------------------------------------

The implementation remains in Gorgon; it has not been copied or imported here.
Source paths below are relative to /home/tinshemet/Desktop/gorgon/files:

* planner/ir/intent.py: FETCH retrieves, ENSURE verifies, ACHIEVE may pursue a
  state change. The caller's intent bounds eligible operations. A read-only tool
  call and a mutating tool call cannot be distinguished by the CALL keyword alone.
* planner/ir/execute.py: ENSURE and ACHIEVE evaluate predicates. A failed check
  returns unsatisfied or unachieved respectively; execution itself does not prove
  arbitrary goal achievement. An explicit IFAILS block is rechecked afterwards.
* planner/ir/derive.py: derive returns statements for supported gaps, None when
  it cannot derive a solution, and [] when no work is required. These three
  outcomes must remain distinct at the new boundary.
* planner/ir/lower.py: leaf_schema offers one operator's schema from the shared
  manifest; assembly and review exist. This is a concrete reuse candidate for
  code-constructed JSON and narrow model decisions.
* planner/ir/classes.py: public exposes receiver-specific method descriptions;
  receiver checks that method rendering reconstructs the original arguments.
  set-valued references are distinguished from individual receivers.
* engines/medusa/engine.py: the existing engine mounts world capabilities and
  packages, and supports author/route callbacks. A failed deterministic path can
  request promotion rather than independently taking a larger reasoning budget.

These are source observations, not new benchmark results. Historical notes about
class files and project-level packages are design leads, not proof those complete
features are currently implemented. No Meduza runtime tests were run in this
boundary review; Gorgon's existing uncommitted work was left untouched.

How RESOLVE uses it
------------------

1. READ supplies supported meaning, roles, qualifiers and grounded references.
   Missing user intent stays ASK; an execution dial cannot supply that meaning.
2. RESOLVE identifies the next evidence or goal obligation and looks for an
   applicable method using manifests and recorded evidence.
3. A deterministic method constructs the program where possible. For unfamiliar
   work, a model proposes a decomposition or selects a bounded method; code
   constructs the artifact and keeps source/goal links.
4. Class selection is a separate bounded decision over the public methods of
   the relevant receiver. Do not put every class implementation into a global
   authoring prompt. Necessary constraints remain enforced by the harness.
5. Validate types, bindings, scalar/set cardinality, intent, effects, dependencies
   and predicates before handing the artifact to ROUTE. Unsupported meanings
   must not be silently erased to fit the existing Meduza subset.
6. The executor enforces each underlying call, including calls inside methods,
   packages and recovery blocks. A reusable method is not a trusted region.
7. Return observations and verdicts with program/action identity, artifact and
   world revisions, timestamps and provenance. RESOLVE updates its evidence graph
   and either advances, derives a supported correction or considers another plan.

FETCH is not omniscient truth. ENSURE proves only what its predicate and evidence
actually establish. ACHIEVE is neither unlimited authorization nor a general
solver. Historical tool reliability, semantic confidence and achieved-objective
verification remain separate quantities; none is a model self-confidence score.

Compilation and classes
-----------------------

Prefer reusing or extracting a reviewed language compiler over inventing a second
DSL. A minimal adapter preserves existing language behavior with less initial
migration risk; extracting language-only modules into Kobra better matches final
ownership but requires dependency separation and conformance tests. Begin with
fixtures and a data contract, then choose the migration slice based on the actual
imports. Do not move the complete engine and lab manifest into Kobra wholesale.

The compiler must refuse unsupported graph nodes and report which obligation it
cannot express. Not every surface construct lowers into a tiny core: FETCH,
conditionals, predicate combinators and set behavior must retain their semantics.

A reusable class method should carry a public signature, version, preconditions,
effects, postcondition, evidence requirements, capability dependencies and test
history. Preserve the earlier class-file proposal's auditable expansion: pin and
expose the body before execution, or require an equivalent recursively checked
artifact boundary. Tested once does not mean correct in every new context.

All cockpit limits continue to apply. Planning/complexity bound decomposition;
Reins bounds model choices; Intent bounds permitted goal changes; Learning governs
method promotion; scope, effects and budgets apply to every expanded operation.
Persistence governs saved/triggered execution. No dial turns a failed ENSURE into
a successful verdict or makes an unknown method executable.

First RESOLVE implementation milestone
-------------------------------------

The next milestone is the READ -> objective/evidence -> Meduza boundary with an
injected compiler and executor protocol, not a replacement runtime. Start with
one retrieval obligation, one verification obligation and one explicitly permitted
state-change obligation. Preserve all input evidence and return typed unsupported
results where the compiler cannot represent it.

Acceptance checks must cover: no loss of qualifiers; no grounding reassignment;
FETCH/ENSURE cannot gain mutation authority; missing capability remains explicit;
scalar/set mismatch; failed or stale verification; exact method-version binding;
and a saved program execution path that does not call READ again.

After this seam works, add the unfamiliar-task hypothesis/decomposition experiment
from the research proposal. Wiring three existing methods is integration evidence,
not proof of general reasoning. The primary research question remains whether
RESOLVE can generate useful novel work and revise it against observations.
