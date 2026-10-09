Serpent READ improvement process
===============================

The frozen protocol is ``benchmarks/read300/protocol.json``. Serpent 1.1.0
supplies the source sentences and independent source graphs. Its implementation
is not edited. All core construction families are eligible. Selection uses
Serpent's balanced planner after removing previously seen normalized sentences;
there are no filters based on READ performance or candidate availability.

Each batch has 300 new sentences. The implementation is frozen during inference.
Failures, provider errors, and adapter errors stay in the denominator. At least
285 exact cases passes the bounded slot threshold, subject to source retention
and offline audit. The source ledger preserves every original character.

This measures an 11-slot projection, not Serpent's complete graph contract.
The protocol explicitly lists graph distinctions that the slots cannot express.
Attribution is not exercised by this core grammar. Finite grammar reuse is not
structural generalization, and new surfaces do not imply unseen pretraining data.

Evidence layout
---------------

``evidence/read300/batch-NNN/generator-manifest.json`` records the generator,
seed, eligibility, family distribution and source hashes. Source graphs,
student inputs and the frozen scoring reference are separate files. Only the
sentence and code-generated candidate menus enter READ's model call.

Within ``evaluation/``, ``cases.jsonl`` keeps every response and source ledger.
``failures.jsonl`` records each failed sentence, expected and selected slots,
candidate misses and diagnostics. ``progress.json`` updates after each case.
``summary.json`` records batch totals; ``offline-audit.json`` verifies replay.
These artifacts remain immutable after the run, except the live progress file.

Fixes and ticks
---------------

``benchmarks/read300/fixes.json`` records fix IDs, affected failures, explanation,
source changes, and validation evidence as fixes are implemented. Historical
failure files remain untouched; later fix/tick records reference their IDs.

A verified tick means the same sentence was incorrect without the intervention
and correct with it. A development replay is excluded from fresh accuracy. A
later-batch tick requires a paired ablation, run after that batch is complete.
Merely matching a new rule is recorded as coverage, never a verified fix.
Regressions receive equal visibility. ``tools/compare_read_runs.py`` creates
paired sentence records, tick counts, regressions, and net change. When several
changes are bundled, attribution belongs to the bundle unless isolated ablations
establish each rule's effect. Different fresh batches report score trends, not
causal improvements by subtraction alone.

Commands
--------

From the Kobra root::

    PYTHONPATH=src:tools:../serpent ../serpent/.venv/bin/python tools/generate_read300.py --batch 1
    PYTHONPATH=src .venv-candidates/bin/python tools/run_read300.py --batch 1
    PYTHONPATH=src .venv-candidates/bin/python tools/audit_read300.py evidence/read300/batch-001/evaluation

The runner completes one frozen batch. Reviewing failures and implementing fixes
requires the working agent; it is not an autonomous code-changing daemon. No goal
completion is claimed from launching the runner or merely reaching a provisional
score. The finite inventory can eventually be exhausted; that condition must be
reported rather than silently recycling cases or changing the distribution.
