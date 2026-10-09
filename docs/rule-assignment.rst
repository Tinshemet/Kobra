Rule assignment development experiment
=====================================

The experimental RuleAssigner in src/kobra/rule_assignment.py assigns simple
active, passive and adjectival-state frames from spaCy dependencies. It abstains
on unsupported clauses, quantities and attachments. Rule eligibility is not a
calibrated confidence estimate. The parser itself is a learned model.

Original source and unresolved reasons remain in every proposal. An optional
fallback callback receives the original text; its response is stored as an
unverified model proposal. This experimental module is not installed as the
production READ default. It does not implement final prose distillation or ASK.

Evaluation
----------

Run tools/evaluate_rule_assignment.py with PYTHONPATH=src:tools using the
.venv-candidates interpreter. The output directory must not already exist.
The evaluation freezes code before scoring 600 reused development cases from
batches 1 and 5. It routes unsupported cases to their previously saved model
answers, without new model calls. This simulates the original model as fallback;
it does not measure a model prompted with the new code proposal.

Batch 1: code handles 91/300, all 91 exact. Saved fallback is correct on 31/209.
Combined: 122/300 (40.67%), versus historical 79/300. 43 recoveries, no regressions.

Batch 5: code handles 280/300, all 280 exact. Saved fallback is correct on 13/20.
Combined: 293/300 (97.67%), versus historical 260/300. 33 recoveries, no regressions.

The two historical models/transports and sentence-family distributions differ.
Do not pool them into an estimate of one current production model. Both sets
have been seen during development; 97.67% is not a fresh 95% confirmation.
Zero observed errors among routed code cases is not proof of reliable routing
on unfamiliar language. The unresolved cases demonstrate that model fallback
still makes errors: 7/20 on batch 5 and 178/209 on batch 1.

Evidence: evidence/rule-assignment-1/ contains all per-case outputs, mismatches,
paired recovery/regression flags, summaries, source snapshots and input hashes.
Before this experiment, batch 5's outstanding offline audit was completed:
300 saved responses replayed, frozen hashes verified, 260 exact; no model calls.
The original mass-batch HTML remains an historical stopping-point snapshot.
