READ pilot with Serpent and Llama 3.1 8B
======================================

MockResolver returns the identical READ result. MockRouter returns UNSUPPORTED
with route.mock diagnostics and no capability. Neither stage reasons, authorizes,
or executes. These are opt-in test doubles, not production stage implementations.

OllamaProvider uses the documented chat endpoint with a JSON response schema,
separate system/user messages, no tools, temperature 0, seed 0, 8192 context tokens,
and a 2048 output-token cap. It rejects truncated replies and does not retry.
Transport has a 120-second timeout and 2 MB response cap. Source consulted
2026-10-08: https://docs.ollama.com/api/chat . Token settings do not guarantee
reproducibility across server versions/hardware; model digest and server version
are recorded before inference.

The student exams in evidence were exported using Serpent's student_exam API
from frozen v1 general-assistant and transcripts packs. Gold was not changed.
Only sentence text reaches the student model. The runner rejects contextual exams
rather than silently discarding their history. The initial profile has empty domain
vocabulary, recorded in the manifest; this measures the generic default only.

Run from the Kobra repository with Ollama serving the installed llama3.1:8b::

    PYTHONPATH=src .venv/bin/python tools/read_serpent.py \
      --exam evidence/serpent-general-assistant-exam.json \
      --output evidence/read-pilot-general-local --limit 20

    PYTHONPATH=src .venv/bin/python tools/read_serpent.py \
      --exam evidence/serpent-transcripts-exam.json \
      --output evidence/read-pilot-transcripts-local --limit 20

Output directories must be new. Each capture saves input IDs, source/exam/code
hashes, model identity, raw requests/replies, final interpretations, errors, and
latency. Partial case records are flushed as they finish; capture_complete means
capture finished, not semantic review completed. The two 20-case prefixes are
convenience pilot samples, not representative or held-out accuracy estimates.

Evaluation limits
-----------------

The runner measures structural acceptance only. Empty or hallucinated prose may
pass these checks. Uncited text is a review signal, not a semantic omission score.
Review each case against the original sentence and evaluator-only Serpent gold
for omissions, unsupported additions, object/relation errors, negation, conditions,
quantities, attribution, and reference uncertainty. Preserve category judgments
and explanations before publishing any semantic score. No automatic graph scorer
or model judge is substituted for that review.

Gorgon's saved declaration-contract scores and Serpent graph scores cannot be
subtracted from Kobra point-based results. Regression remains unmeasured until
both versions have matched inputs and a shared reviewed scoring definition.
Gorgon's paused evaluation remains untouched.

Execution evidence
------------------

The 2026-10-08 session could not start or access Ollama: socket operations were
prohibited. The blocked capture records zero inference attempts. No live READ
accuracy claim is supported. Offline checks: 57 tests passed, including transport
payload, truncation rejection, no retry, invalid-evidence short-circuit, mock
identity preservation, and runner capture/serialization. See
``evidence/read-pilot-tests.log``. Ruff F/E9 checks passed on the new files.

Review: checked gold separation, failure capture, no execution/capability in mocks,
and preservation of existing artifacts. This was a self-review, not an independent
audit. READ prompts and linguistic algorithms were left unchanged for the pilot.
