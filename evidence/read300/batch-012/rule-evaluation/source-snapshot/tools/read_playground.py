"""Loopback-only live READ playground. No generative model, persistence or execution."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Lock
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader

MAX_TEXT = 4000
MAX_BODY = 24000


def make_server(port=8765):
    assigner = RuleAssigner()
    reader = GatedRuleReader(assigner, ConfidenceGate(), resolver=None)
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log typed text.

        def allowed(self):
            expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in expected:
                return False
            origin = self.headers.get('Origin')
            return origin is None or origin in {f'http://{h}' for h in expected}

        def send(self, status, payload, content_type='application/json; charset=utf-8'):
            body = json.dumps(payload, ensure_ascii=False).encode() if not isinstance(payload, bytes) else payload
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.allowed():
                return self.send(403, {'error':'Only local same-origin requests are allowed.'})
            path = urlsplit(self.path).path
            if path in ('/', '/read-pipeline-current.html'):
                return self.send(200, (ROOT/'reports/read-pipeline-current.html').read_bytes(), 'text/html; charset=utf-8')
            if path == '/api/health':
                return self.send(200, {'status':'ready','generative_ai':False,'max_text':MAX_TEXT})
            return self.send(404, {'error':'Not found.'})

        def do_OPTIONS(self):
            self.send(403, {'error':'Cross-origin access is disabled.'})

        def do_POST(self):
            if not self.allowed():
                return self.send(403, {'error':'Only local same-origin requests are allowed.'})
            if self.path != '/api/read':
                return self.send(404, {'error':'Not found.'})
            if self.headers.get('Content-Type','').split(';')[0].strip() != 'application/json':
                return self.send(415, {'error':'Send application/json.'})
            try:
                size = int(self.headers.get('Content-Length','-1'))
            except ValueError:
                size = -1
            if not 0 <= size <= MAX_BODY:
                return self.send(413, {'error':'Missing or excessive request length.'})
            self.connection.settimeout(10)
            try:
                value = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeError, TimeoutError):
                return self.send(400, {'error':'Invalid JSON request.'})
            if not isinstance(value, dict) or set(value) != {'text'} or not isinstance(value['text'],str):
                return self.send(400, {'error':'Expected one text string.'})
            text = value['text']
            if not text.strip() or len(text)>MAX_TEXT:
                return self.send(400, {'error':f'Enter 1–{MAX_TEXT} characters of text.'})
            try:
                with lock:
                    result = reader.read(text)
                    tokens = [dict(text=t.text,pos=t.pos_,dependency=t.dep_,head=t.head.text) for t in assigner.nlp(text)]
            except Exception:
                return self.send(500, {'error':'Local parsing failed. No interpretation was accepted.'})
            self.send(200, dict(source=text, generative_ai_called=False,
                parser='spaCy en_core_web_sm (learned grammar parser)',
                code_proposal=result['code_proposal'],tokens=tokens,final_result=result))

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    server = make_server(args.port)
    print(f'READ playground ready: http://127.0.0.1:{server.server_port}/ — generative AI disabled',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=='__main__':
    main()
