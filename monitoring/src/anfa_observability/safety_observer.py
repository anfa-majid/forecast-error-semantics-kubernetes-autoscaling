from __future__ import annotations
import json, threading, time, urllib.error, urllib.request

class SafetyPublisher:
    def __init__(self, run_id, endpoint, duration_seconds, t0_monotonic_ns, grace_ms=150, timeout_seconds=1.0, output_path=None):
        self.run_id=run_id;self.endpoint=endpoint;self.duration_seconds=duration_seconds
        self.t0_monotonic_ns=t0_monotonic_ns;self.grace_ms=grace_ms;self.timeout_seconds=timeout_seconds
        self.output_path=output_path
        self.counts={};self.lock=threading.Lock();self.error=None;self.records=[]
        self.thread=threading.Thread(target=self._run,name='anfa-safety-observer',daemon=False)
    def start(self): self.thread.start()
    def note_dispatch(self, source_second):
        with self.lock:self.counts[source_second]=self.counts.get(source_second,0)+1
    def join(self):
        self.thread.join()
        if self.error: raise RuntimeError(f'safety observation publishing failed: {self.error}')
    def _run(self):
        sequence=-1
        try:
            for sequence in range(self.duration_seconds):
                deadline=self.t0_monotonic_ns+(sequence+1)*1_000_000_000+self.grace_ms*1_000_000
                remaining=deadline-time.monotonic_ns()
                if remaining>0:time.sleep(remaining/1e9)
                with self.lock:count=self.counts.pop(sequence,0)
                observation={'run_id':self.run_id,'sequence':sequence,'window_start_ms':sequence*1000,
                    'window_end_ms':(sequence+1)*1000,'dispatch_count':count,'observed_demand_rps':float(count)}
                if self.output_path:
                    with open(self.output_path,'a',encoding='utf-8',newline='\n') as handle:
                        handle.write(json.dumps(observation,separators=(',',':'))+'\n');handle.flush()
                body=json.dumps(observation,separators=(',',':')).encode()
                request=urllib.request.Request(self.endpoint,data=body,method='POST',headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=self.timeout_seconds) as response:
                    if response.status!=202:raise RuntimeError(f'HTTP {response.status} at sequence {sequence}')
                    response.read()
                self.records.append(observation)
        except urllib.error.HTTPError as error:
            try: response_body=error.read().decode('utf-8','replace').strip()
            except Exception: response_body='<unreadable>'
            self.error=RuntimeError(f'HTTP {error.code} at sequence {sequence}: {response_body}')
        except BaseException as error:self.error=RuntimeError(f'at sequence {sequence}: {error}')
