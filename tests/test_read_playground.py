import json
from pathlib import Path
import sys
from threading import Thread
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from read_playground import make_server


class PlaygroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(0)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def post(self,value,**headers):
        return urlopen(Request(self.url+'/api/read',data=json.dumps(value).encode(),headers={'Content-Type':'application/json',**headers}),timeout=10)
    def test_actual_code_json_without_ai(self):
        with self.post({'text':'The parcel was carried by Lena.'}) as response:r=json.load(response)
        self.assertFalse(r['generative_ai_called'])
        self.assertEqual(r['code_proposal']['frames'][0]['agent'],'Lena')
        self.assertEqual(r['final_result']['route'],'ASK')
        self.assertIn('uncalibrated_cohort',r['final_result']['reasons'])
    def test_unresolved_context_remains_visible(self):
        with self.post({'text':'Move it.'}) as response:r=json.load(response)
        self.assertIn('ungrounded_reference:patient',r['final_result']['reasons'])
    def test_invalid_and_long_input_rejected(self):
        for value in ({'text':''},{'text':'x'*4001},{'text':42},{'text':'Hi','model':'anything'}):
            with self.assertRaises(HTTPError) as e:self.post(value)
            self.assertEqual(e.exception.code,400)
    def test_cross_origin_rejected(self):
        with self.assertRaises(HTTPError) as e:self.post({'text':'Cancel the subscription.'},Origin='https://example.com')
        self.assertEqual(e.exception.code,403)
    def test_html_and_no_arbitrary_files(self):
        with urlopen(self.url) as r:self.assertIn(b'id="live-read-text"',r.read())
        with self.assertRaises(HTTPError) as e:urlopen(self.url+'/src/kobra/confidence_gate.py')
        self.assertEqual(e.exception.code,404)
