"""Thread-safe dispatch-window accumulator used by the safety-enabled load generator."""
from __future__ import annotations
from dataclasses import dataclass
import json, threading, urllib.request

@dataclass(frozen=True)
class Observation:
    run_id: str
    sequence: int
    window_start_ms: int
    window_end_ms: int
    dispatch_count: int
    observed_demand_rps: float
    def as_dict(self): return self.__dict__.copy()

class DispatchAccumulator:
    def __init__(self, run_id: str, interval_seconds: int = 1):
        if not run_id or interval_seconds <= 0: raise ValueError('run identity and positive interval required')
        self.run_id, self.interval_seconds = run_id, interval_seconds
        self._counts: dict[int,int] = {}; self._finalized = -1; self._lock = threading.Lock()

    def note_dispatch(self, source_second: int):
        if source_second < 0: raise ValueError('source_second must be nonnegative')
        with self._lock:
            if source_second <= self._finalized: raise ValueError('dispatch arrived after its window was finalized')
            self._counts[source_second] = self._counts.get(source_second,0)+1

    def finalize(self, sequence: int) -> Observation:
        with self._lock:
            if sequence != self._finalized + 1: raise ValueError('windows must finalize exactly once in sequence')
            count=self._counts.pop(sequence,0); self._finalized=sequence
        start=sequence*self.interval_seconds*1000
        return Observation(self.run_id,sequence,start,start+self.interval_seconds*1000,count,count/self.interval_seconds)

def post_observation(url: str, observation: Observation, timeout_seconds: float = 1.0):
    body=json.dumps(observation.as_dict(),separators=(',',':')).encode()
    request=urllib.request.Request(url,data=body,method='POST',headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=timeout_seconds) as response:
        if response.status != 202: raise RuntimeError(f'observation rejected with HTTP {response.status}')
        return json.loads(response.read())
