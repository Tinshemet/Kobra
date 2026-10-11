READ improvement record
=======================

Batch 1: 79/300 exact (26.33%); 300/300 source ledgers retained.
Offline audit: all 300 responses replayed, with scores and source hashes verified.
Scope: Serpent core grammar, fixed 11-slot projection; not full graph accuracy.

Batch 2: running; all four changes bundled, same llama3.1:8b model.
Preflight correction: 113 passed, 1 failed, 1 skipped (115 total).
The failed nominal PP boundary test is retained and queued for the next cycle.
The run remains frozen. See batch-002/preflight-erratum.json.

Verified historical binding recoveries
--------------------------------------

No new model calls: historical choices held fixed while candidate rules varied.
These ticks are not fresh accuracy or an end-to-end reader improvement estimate.
R001: 2 recoveries, no regressions. R002: 9 recoveries, no regressions.
Combined: 79 -> 90 exactly bound historical cases, 11 recoveries total.
Coverage matches are separately marked in candidate-ticks.csv.

* ✓ R001-content-predicate-fallback / S000072: Check zorbins.
* ✓ R001-content-predicate-fallback / S000277: Check boxes.
* ✓ R002-expanded-nominal / S000064: Mira and Nia check the train.
* ✓ R002-expanded-nominal / S000082: Alex and Nia check the key.
* ✓ R002-expanded-nominal / S000122: Mira and Nia check the lamp.
* ✓ R002-expanded-nominal / S000143: Mira and Nia check the quill.
* ✓ R002-expanded-nominal / S000180: Mira and Nia check the key.
* ✓ R002-expanded-nominal / S000199: Mira and Nia check the server.
* ✓ R002-expanded-nominal / S000234: Mira and Nia check the disk.
* ✓ R002-expanded-nominal / S000251: Mira and Nia check the book.
* ✓ R002-expanded-nominal / S000289: Mira and Nia check the box.

Batch 2 completed
-----------------

82/300 exact (27.33%); 300/300 source ledgers retained.
All 300 responses replayed; source hashes verified.
Invalid selections: 0. Candidate requirements covered: 1082/1088 (99.45%).
Selected-rule coverage is in batch-002/rule-coverage.csv; these are not causal flips.
Batch scores use different sentences and family mixes; +1 percentage point is not a paired effect.

Batch 3 preparation
-------------------

R005 fixes NP/relative-pronoun coverage. R006 guards initial function words.
M001 switches to Qwen 3.5 4B with explicit decoding controls.
Preflight: 117 passed, 1 optional skipped. The earlier failing test now passes.

Batch 3 completed
-----------------

88/300 exact (29.33%); 300/300 source ledgers retained. All 300 responses replayed.
Candidate coverage: 1087/1087. Required fields omitted in 134 cases; 34 binding errors.
Synthetic transport probe: think=False returned forbidden RED, think=True returned required BLUE.
Nested required-field/array probe also passed with thinking enabled.
Evidence: transport-diagnosis/. Related upstream issue: https://github.com/ollama/ollama/issues/14645

Batch 4 preparation
-------------------

Use verified thinking-enabled mode and enforce runtime schema validation.
Language prompt and candidate construction unchanged from batch 3.
Reasoning-mode change and grammar activation are a bundle, not isolated effects.
Preflight tests: 120 passed, 1 optional skipped.

Batch 4 infrastructure abort
----------------------------

Four completed calls, all generation-limit failures. No full-batch accuracy claim.
The in-flight call was interrupted; all 300 sentences are retired, with source and captures retained.
Thinking mode enforces format but exhausts the configured generation budget on READ.

Verified transport workaround
-----------------------------

/api/generate with think=False passes the nested contradictory-schema probe.
Paired system-priority controls (BLUE/RED) both follow the system instruction.
No READ accuracy cases were used in these synthetic transport probes.
Evidence is saved in transport-diagnosis/generate-*.json.
Batch 5 keeps the language prompt and candidate rules unchanged.

Stopped when the user returned
-----------------------------

Batch 5 completed: 260/300 exact (86.67%), 300/300 source ledgers retained.
The runner reports source hashes unchanged. Offline replay audit is still pending.
No further batch launched. The 95% threshold has not been reached.
Completed fresh batches: 1=79/300, 2=82/300, 3=88/300, 5=260/300.
Batch 4 was an infrastructure abort and has no full-batch accuracy score.
Different family mixes mean these rates are trends, not paired causal gains.
The latest endpoint fix has not yet received an end-to-end paired flip audit.
