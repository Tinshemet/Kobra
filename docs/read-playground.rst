Live local READ playground
=========================

From the Kobra directory run::

    .venv-candidates/bin/python tools/read_playground.py

Then open http://127.0.0.1:8765/ . The same pipeline report now includes a textbox
that sends source text after a 450 ms typing pause. JSON, parser tokens and the
complete result are returned by the actual RuleAssigner and GatedRuleReader.
The generative resolver is always None; no provider or model API is called.
The existing learned spaCy grammar parser is still used. No history or WORLD is
supplied by this first textbox interface.

Code assignment and gate acceptance are displayed separately. There is no
held-out calibration installed, so ASK is currently expected even for successful
code assignments. This is a playground, not an accuracy measurement or executor.

Only the loopback interface is bound; only the report, health and READ endpoints
are served. Cross-origin requests are rejected. Text is bounded at 4000 characters,
not logged or persisted by the server, and displayed as text rather than HTML.
The browser drops stale responses after newer input. The server serializes parser
access. Closing the tab does not stop the Python process; Ctrl-C in the launching
terminal stops it. An alternate port can be chosen with --port.

The HTML still works offline for saved traces. Live input requires opening the
local-server URL rather than the file directly.
