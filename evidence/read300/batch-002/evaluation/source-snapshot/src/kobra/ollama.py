"""Bounded Ollama transport; no retries, response repair, or tool execution."""

import json
from urllib.request import Request, urlopen


def decoding_schema(schema):
    """Project large upper bounds out of llama.cpp's finite-repeat grammar.

    Some runners reject repetitions >= 2000 and silently decode unconstrained.
    READ's binders still enforce the ORIGINAL limits after generation. Preserve
    types, required fields, enums and small bounds; never truncate source text.
    This is a decoding aid, not a replacement for application validation.
    """
    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, child in value.items():
            if key in ("properties", "patternProperties", "$defs", "definitions"):
                result[key] = {name: visit(subschema) for name, subschema in child.items()}
                continue
            if key in ("minLength", "minItems") and type(child) is int and child >= 2000:
                raise ValueError("schema minimum exceeds compatible grammar repetition limit")
            if key in ("maxLength", "maxItems") and type(child) is int and child >= 2000:
                continue
            # Values here are instance data, not subschemas.
            result[key] = child if key in ("enum", "const", "default", "examples") else visit(child)
        return result

    return visit(dict(schema))


class OllamaProvider:
    def __init__(self, model="llama3.1:8b", url="http://127.0.0.1:11434", timeout=120):
        self.model = model
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.last_exchange = None

    def _request(self, path, payload=None):
        request = Request(
            self.url + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("Ollama response exceeded byte limit")
        return json.loads(body)

    def identity(self):
        tags = self._request("/api/tags")
        matches = [m for m in tags["models"] if m["name"] == self.model]
        if len(matches) != 1:
            raise ValueError(
                f"Model {self.model!r} is not installed under that exact name"
            )
        return {"server": self._request("/api/version"), "model": matches[0]}

    def complete(self, *, prompt, text, schema):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            "format": decoding_schema(schema),
            "stream": False,
            "options": {
                "temperature": 0,
                "seed": 0,
                "num_predict": 2048,
                "num_ctx": 8192,
            },
        }
        self.last_exchange = {"request": payload, "validation_schema": dict(schema),
                              "schema_projection": "llama-repeat-compatible-1"}
        reply = self._request("/api/chat", payload)
        self.last_exchange["response"] = reply
        if reply.get("done") is not True or reply.get("done_reason") != "stop":
            raise ValueError(
                "Ollama did not finish normally (possibly truncated output)"
            )
        proposal = json.loads(reply["message"]["content"])
        if not isinstance(proposal, dict):
            raise ValueError("Ollama proposal must be an object")
        return proposal

    def select(self, *, prompt, text, schema, name, residual_field=True):
        """Collect flat selection calls; host constructs the frame list, no execution."""
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": prompt},
                         {"role": "user", "content": text}],
            "tools": [{"type": "function", "function": {
                "name": name, "description": "Select source candidates for linguistic slots.",
                "parameters": decoding_schema(schema)}}],
            "stream": False,
            "options": {"temperature": 0, "seed": 0, "num_predict": 1024, "num_ctx": 8192},
        }
        self.last_exchange = {"request": payload, "validation_schema": schema}
        reply = self._request("/api/chat", payload)
        self.last_exchange["response"] = reply
        if reply.get("done") is not True or reply.get("done_reason") != "stop":
            raise ValueError("selection did not finish normally")
        calls = reply.get("message", {}).get("tool_calls", [])
        if not isinstance(calls, list) or not 1 <= len(calls) <= 4:
            raise ValueError("expected one to four selection tool calls")
        frames, unrepresented = [], []
        for call in calls:
            function = call.get("function", {})
            if function.get("name") != name or not isinstance(function.get("arguments"), dict):
                raise ValueError("invalid selection tool or arguments")
            frame = dict(function["arguments"])
            if residual_field:
                if "unrepresented" not in frame:
                    raise ValueError("missing unrepresented selection")
                residual = frame.pop("unrepresented")
                if residual != "NONE":
                    unrepresented.append(residual)
            frames.append(frame)
        return {"frames": frames, "unrepresented": unrepresented}


class ConstrainedSelectionProvider(OllamaProvider):
    """AI chooses slots; a decoding grammar enforces code-built finite menus."""

    def select(self, *, prompt, text, schema, name, residual_field=True):
        if residual_field or name != 'arrange_read':
            raise ValueError('constrained selections support arrangement only')
        envelope = {'type':'object','properties':{
            'frames':{'type':'array','items':schema,'minItems':1,'maxItems':4}},
            'required':['frames'],'additionalProperties':False}
        instruction = prompt.replace('by calling arrange_read', 'as JSON').replace(
            'one flat tool call', 'one frame').replace('make separate calls', 'make separate frames')
        instruction += '\nReturn only {"frames":[...]} JSON, with each frame containing all listed slots. Do not call tools.\n'
        payload = json.loads(text)
        payload['slot_menus'] = {key:value['enum'] for key,value in schema['properties'].items()}
        result = self.complete(prompt=instruction,text=json.dumps(payload,ensure_ascii=False),schema=envelope)
        if set(result) != {'frames'}:
            raise ValueError('unexpected constrained selection fields')
        return {'frames':result['frames'],'unrepresented':[]}
