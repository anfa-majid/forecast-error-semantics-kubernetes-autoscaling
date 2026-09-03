from __future__ import annotations

import argparse
import csv
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import append_jsonl, epoch_ns, iso_utc, parse_utc, sha256_file, utc_now, write_json
from .safety_observer import SafetyPublisher


def epoch_ns_to_utc(value: int) -> str:
    return iso_utc(datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc))


@dataclass(frozen=True)
class ScheduledRequest:
    request_id: str
    scheduled_offset_us: int
    source_second: int
    target_rps: float
    scheduled_requests_in_second: int


def load_schedule(path: str | Path) -> list[ScheduledRequest]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"request_id", "scheduled_offset_us", "source_second", "target_rps", "scheduled_requests_in_second"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"request schedule missing columns: {sorted(required - set(reader.fieldnames or []))}")
        rows = [ScheduledRequest(
            request_id=row["request_id"],
            scheduled_offset_us=int(row["scheduled_offset_us"]),
            source_second=int(row["source_second"]),
            target_rps=float(row["target_rps"]),
            scheduled_requests_in_second=int(row["scheduled_requests_in_second"]),
        ) for row in reader]
    if not rows:
        raise ValueError("request schedule is empty")
    if len({row.request_id for row in rows}) != len(rows):
        raise ValueError("duplicate request_id")
    offsets = [row.scheduled_offset_us for row in rows]
    if offsets != sorted(offsets) or offsets[0] < 0:
        raise ValueError("request schedule must be nonnegative and ordered")
    return rows


class JsonlSink:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.handle = Path(path).open("w", encoding="utf-8", newline="\n")
        self.lock = threading.Lock()

    def write(self, record: dict) -> None:
        with self.lock:
            append_jsonl(self.handle, record)

    def close(self) -> None:
        self.handle.close()


def classify_error(error: BaseException) -> tuple[str, bool]:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timeout", True
    if isinstance(error, urllib.error.HTTPError):
        return "http_error", False
    if isinstance(error, urllib.error.URLError):
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return "timeout", True
        return "transport_error", False
    return "client_error", False


def run_request(row: ScheduledRequest, *, target_url: str, timeout_seconds: float, t0_wall_ns: int,
                t0_monotonic_ns: int, identity: dict, sink: JsonlSink,clock_correction_ms:float=0,
                safety_publisher: SafetyPublisher | None = None) -> None:
    scheduled_wall_ns = t0_wall_ns + row.scheduled_offset_us * 1000
    scheduled_monotonic_ns = t0_monotonic_ns + row.scheduled_offset_us * 1000
    remaining = scheduled_monotonic_ns - time.monotonic_ns()
    if remaining > 0:
        time.sleep(remaining / 1e9)
    raw_dispatch_wall_ns = epoch_ns();dispatch_wall_ns=raw_dispatch_wall_ns+int(clock_correction_ms*1e6)
    dispatch_monotonic_ns = time.monotonic_ns()
    if safety_publisher is not None:
        safety_publisher.note_dispatch(row.source_second)
    status_code = None
    response_bytes = 0
    pod_name = ""
    pod_uid = ""
    application_duration_ns = None
    error_class = ""
    error_message = ""
    timed_out = False
    try:
        request = urllib.request.Request(target_url, method="GET", headers={"Connection": "close", "X-ANFA-Request-ID": row.request_id})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            response_bytes = len(body)
            status_code = response.status
            pod_name = response.headers.get("X-Benchmark-Pod", "")
            pod_uid = response.headers.get("X-Benchmark-Pod-UID", "")
            try:
                application_duration_ns = json.loads(body).get("duration_ns")
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass
    except BaseException as error:  # record every outcome before returning to the scheduler
        error_class, timed_out = classify_error(error)
        error_message = str(error)[:1000]
        if isinstance(error, urllib.error.HTTPError):
            status_code = error.code
    raw_completion_wall_ns=epoch_ns();completion_wall_ns=raw_completion_wall_ns+int(clock_correction_ms*1e6)
    completion_monotonic_ns = time.monotonic_ns()
    record = {
        "schema_version": "1.0.0", "record_type": "request", **identity,
        "request_id": row.request_id, "source_second": row.source_second,
        "target_rps": row.target_rps, "scheduled_requests_in_second": row.scheduled_requests_in_second,
        "scheduled_offset_us": row.scheduled_offset_us,
        "scheduled_utc": iso_utc(parse_utc(identity["t0_utc"]) + timedelta(microseconds=row.scheduled_offset_us)),
        "scheduled_epoch_ns": scheduled_wall_ns,"raw_dispatch_epoch_ns":raw_dispatch_wall_ns,"dispatch_epoch_ns": dispatch_wall_ns,
        "raw_completion_epoch_ns":raw_completion_wall_ns,"completion_epoch_ns": completion_wall_ns,"clock_correction_ms":clock_correction_ms,
        "dispatch_offset_us": (dispatch_monotonic_ns - t0_monotonic_ns) // 1000,
        "completion_offset_us": (completion_monotonic_ns - t0_monotonic_ns) // 1000,
        "dispatch_lateness_us": (dispatch_monotonic_ns - scheduled_monotonic_ns) // 1000,
        "latency_us": (completion_monotonic_ns - dispatch_monotonic_ns) // 1000,
        "status_code": status_code, "success": status_code is not None and 200 <= status_code < 300,
        "timeout": timed_out, "error_class": error_class, "error_message": error_message,
        "response_bytes": response_bytes, "pod_name": pod_name, "pod_uid": pod_uid,
        "application_duration_ns": application_duration_ns,
    }
    sink.write(record)


def execute(schedule_path: str, output_path: str, target_url: str, t0_utc: str, timeout_seconds: float,
            max_workers: int, identity: dict, clock_correction_ms: float = 0,
            safety_observation_url: str | None = None, safety_observation_grace_ms: int = 150,
            safety_observation_output: str | None = None) -> dict:
    rows = load_schedule(schedule_path)
    t0 = parse_utc(t0_utc)
    delay_ns = int((t0.timestamp() - (time.time() + clock_correction_ms / 1000)) * 1e9)
    if delay_ns < 2_000_000_000:
        raise ValueError("t0 must be at least two seconds in the future")
    t0_wall_ns = int(t0.timestamp() * 1e9)
    t0_monotonic_ns = time.monotonic_ns() + delay_ns
    duration_seconds = max(row.source_second for row in rows) + 1
    safety_publisher = None
    if safety_observation_url:
        safety_publisher = SafetyPublisher(identity["run_id"], safety_observation_url, duration_seconds,
                                           t0_monotonic_ns, grace_ms=safety_observation_grace_ms,output_path=safety_observation_output)
        safety_publisher.start()
    sink = JsonlSink(output_path)
    try:
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="anfa-load") as executor:
            futures = []
            for row in rows:
                remaining = t0_monotonic_ns + row.scheduled_offset_us * 1000 - time.monotonic_ns()
                if remaining > 0:
                    time.sleep(remaining / 1e9)
                futures.append(executor.submit(run_request, row, target_url=target_url, timeout_seconds=timeout_seconds,
                                               t0_wall_ns=t0_wall_ns, t0_monotonic_ns=t0_monotonic_ns,
                                               identity={**identity, "t0_utc": t0_utc}, sink=sink,clock_correction_ms=clock_correction_ms,
                                               safety_publisher=safety_publisher))
            for future in futures:
                future.result()
            if safety_publisher is not None:
                safety_publisher.join()
    finally:
        sink.close()
    summary = {
        "schema_version": "1.0.0", **identity, "t0_utc": t0_utc, "target_url": target_url, "clock_correction_ms":clock_correction_ms,
        "schedule_sha256": sha256_file(schedule_path), "requests_scheduled": len(rows),
        "safety_observation_enabled": safety_publisher is not None,
        "safety_observations_published": len(safety_publisher.records) if safety_publisher else 0,
        "output_sha256": sha256_file(output_path),
    }
    with Path(output_path).open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    summary.update({
        "requests_recorded": len(records), "completed_successfully": sum(r["success"] for r in records),
        "timeouts": sum(r["timeout"] for r in records), "errors": sum(bool(r["error_class"]) for r in records),
        "maximum_dispatch_lateness_us": max(r["dispatch_lateness_us"] for r in records),
        "started_utc": epoch_ns_to_utc(min(r["dispatch_epoch_ns"] for r in records)),
        "ended_utc": epoch_ns_to_utc(max(r["completion_epoch_ns"] for r in records)),
    })
    write_json(str(Path(output_path).with_suffix(".summary.json")), summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute an exact Step 7 request schedule and log every request")
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--t0-utc", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-workers", type=int, default=512)
    parser.add_argument("--clock-correction-ms", type=float, default=0)
    parser.add_argument("--safety-observation-url")
    parser.add_argument("--safety-observation-grace-ms", type=int, default=150)
    parser.add_argument("--safety-observation-output")
    for name in ("experiment-id", "run-id", "workload-id", "forecast-condition"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    identity = {"experiment_id": args.experiment_id, "run_id": args.run_id, "workload_id": args.workload_id,
                "forecast_condition": args.forecast_condition}
    print(json.dumps(execute(args.schedule, args.output, args.target_url, args.t0_utc, args.timeout_seconds, args.max_workers,
                             identity,args.clock_correction_ms,args.safety_observation_url,args.safety_observation_grace_ms,
                             args.safety_observation_output), indent=2))


if __name__ == "__main__":
    main()
