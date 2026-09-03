import json, threading, time, sys, unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'loadgen'))
from anfa_observability.safety_observer import SafetyPublisher

class Handler(BaseHTTPRequestHandler):
    rows=[]
    def do_POST(self):
        body=self.rfile.read(int(self.headers['Content-Length']));self.rows.append(json.loads(body))
        self.send_response(202);self.end_headers();self.wfile.write(b'{"accepted":true}')
    def log_message(self,*args):pass

class PublisherTests(unittest.TestCase):
    def test_publishes_finalized_sequential_windows(self):
        Handler.rows=[];server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            now=time.monotonic_ns();publisher=SafetyPublisher('run-1',f'http://127.0.0.1:{server.server_port}/v1/safety/observations',2,now-1_900_000_000,grace_ms=0)
            publisher.note_dispatch(0);publisher.note_dispatch(0);publisher.note_dispatch(1);publisher.start();publisher.join()
            self.assertEqual([r['sequence'] for r in Handler.rows],[0,1]);self.assertEqual([r['dispatch_count'] for r in Handler.rows],[2,1])
        finally:server.shutdown();thread.join();server.server_close()

if __name__=='__main__':unittest.main()
