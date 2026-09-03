#!/usr/bin/env python3
"""ANFA Step 6 native-K3s cached-image actuation trial runner."""

import argparse
import csv
import datetime as dt
import json
import pathlib
import subprocess
import threading
import time
import urllib.request


UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC)


def iso(value=None):
    return (value or now()).isoformat(timespec="microseconds")


def run(*args, json_output=False):
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return json.loads(result.stdout) if json_output else result.stdout.strip()


def kubectl(*args, json_output=False):
    return run("sudo", "k3s", "kubectl", *args, json_output=json_output)


def condition_time(pod, condition_type):
    for condition in pod.get("status", {}).get("conditions", []):
        if condition.get("type") == condition_type and condition.get("status") == "True":
            return condition.get("lastTransitionTime")
    return None


def container_status(pod):
    for status in pod.get("status", {}).get("containerStatuses", []):
        if status.get("name") == "benchmark-app":
            return status
    return {}


def container_started(pod):
    return container_status(pod).get("state", {}).get("running", {}).get("startedAt")


def get_pods():
    return kubectl(
        "get", "pods", "-n", "default",
        "-l", "app.kubernetes.io/name=benchmark-app",
        "-o", "json", json_output=True,
    )


def is_ready(pod):
    return condition_time(pod, "Ready") is not None


def wait_exact_ready(count, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pods = get_pods()
        items = pods.get("items", [])
        if len(items) == count and sum(is_ready(p) for p in items) == count:
            return pods
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for exactly {count} Ready Pods")


def probe(url, timeout):
    request = urllib.request.Request(url, method="GET", headers={"Connection": "close"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()
        return {
            "pod_uid": response.headers.get("X-Benchmark-Pod-UID", "").strip(),
            "pod_name": response.headers.get("X-Benchmark-Pod", "").strip(),
            "app_ready_utc": response.headers.get("X-Benchmark-Ready-At", "").strip(),
            "http_status": response.status,
        }


def save_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-replicas", type=int, choices=(2, 3, 4), required=True)
    parser.add_argument("--repetition", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--poll-ms", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--recovery", type=int, default=15)
    parser.add_argument("--url", default="http://127.0.0.1:30080/work")
    args = parser.parse_args()

    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    poll_seconds = args.poll_ms / 1000.0
    valid = False
    probe_stop = threading.Event()
    probe_thread = None
    probe_records = []
    probe_lock = threading.Lock()

    def probe_loop():
        while not probe_stop.is_set():
            cycle = time.monotonic()
            record = {}
            try:
                record.update(probe(args.url, 2))
                record["observed_utc"] = iso()
                record["error"] = ""
            except Exception as exc:
                record.update({
                    "observed_utc": iso(),
                    "pod_uid": "",
                    "pod_name": "",
                    "app_ready_utc": "",
                    "http_status": "",
                    "error": type(exc).__name__,
                })
            with probe_lock:
                probe_records.append(record)
            remaining = poll_seconds - (time.monotonic() - cycle)
            if remaining > 0:
                probe_stop.wait(remaining)

    try:
        kubectl("scale", "deployment/benchmark-app", "-n", "default", "--replicas=1")
        kubectl("rollout", "status", "deployment/benchmark-app", "-n", "default", "--timeout=180s")
        baseline = wait_exact_ready(1, args.timeout)
        if args.recovery:
            time.sleep(args.recovery)
        baseline = get_pods()
        baseline_uids = {p["metadata"]["uid"] for p in baseline["items"]}
        save_json(output / "pods-baseline.json", baseline)

        probe_thread = threading.Thread(target=probe_loop, name="service-probe", daemon=True)
        probe_thread.start()
        forecast = now()
        decision = now()
        scale_sent = now()
        kubectl(
            "scale", "deployment/benchmark-app", "-n", "default",
            f"--replicas={args.target_replicas}",
        )
        scale_ack = now()

        observed = {}
        served = {}
        deadline = time.monotonic() + args.timeout

        while time.monotonic() < deadline:
            cycle = time.monotonic()
            observed_at = now()
            pods = get_pods()
            for pod in pods.get("items", []):
                uid = pod["metadata"]["uid"]
                if uid in baseline_uids:
                    continue
                item = observed.setdefault(uid, {
                    "pod_name": pod["metadata"]["name"],
                    "pod_uid": uid,
                    "pod_created_utc": pod["metadata"].get("creationTimestamp"),
                    "first_observed_utc": iso(observed_at),
                })
                item["node"] = pod.get("spec", {}).get("nodeName")
                for key, value in (
                    ("scheduled_utc", condition_time(pod, "PodScheduled")),
                    ("container_started_utc", container_started(pod)),
                    ("ready_utc", condition_time(pod, "Ready")),
                ):
                    if value and not item.get(key):
                        item[key] = value
                        item[key.replace("_utc", "_observed_utc")] = iso(observed_at)
                status = container_status(pod)
                if status:
                    item["image_id"] = status.get("imageID")
                    item["restart_count"] = status.get("restartCount")

            with probe_lock:
                snapshot = list(probe_records)
            for record in snapshot:
                uid = record.get("pod_uid")
                if uid not in observed or uid in served:
                    continue
                observed_time = dt.datetime.fromisoformat(record["observed_utc"])
                if observed_time >= scale_sent:
                    served[uid] = {
                        **record,
                        "first_request_utc": record["observed_utc"],
                    }

            expected = args.target_replicas - 1
            all_ready = len(observed) == expected and all(v.get("ready_utc") for v in observed.values())
            all_served = len(served) == expected
            if all_ready and all_served:
                valid = True
                break
            remaining = poll_seconds - (time.monotonic() - cycle)
            if remaining > 0:
                time.sleep(remaining)

        if not valid:
            raise RuntimeError("not all new Pods became Ready and served before timeout")

        probe_stop.set()
        probe_thread.join(timeout=5)
        with probe_lock:
            probe_snapshot = list(probe_records)
        probe_after_scale = [
            record for record in probe_snapshot
            if dt.datetime.fromisoformat(record["observed_utc"]) >= scale_sent
        ]
        probe_times = [dt.datetime.fromisoformat(r["observed_utc"]) for r in probe_after_scale]
        probe_gaps_ms = [
            (right - left).total_seconds() * 1000
            for left, right in zip(probe_times, probe_times[1:])
        ]
        with (output / "service-probe.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(probe_snapshot[0]))
            writer.writeheader()
            writer.writerows(probe_snapshot)

        rows = []
        for uid, item in sorted(observed.items()):
            service = served[uid]
            parse = dt.datetime.fromisoformat
            created_observed = parse(item["first_observed_utc"])
            scheduled_observed = parse(item["scheduled_observed_utc"])
            started_observed = parse(item["container_started_observed_utc"])
            ready_observed = parse(item["ready_observed_utc"])
            first_request = parse(service["first_request_utc"])
            created_raw = parse(item["pod_created_utc"])
            scheduled_raw = parse(item["scheduled_utc"])
            started_raw = parse(item["container_started_utc"])
            ready_raw = parse(item["ready_utc"])
            rows.append({
                "target_replicas": args.target_replicas,
                "repetition": args.repetition,
                **item,
                "app_ready_utc": service["app_ready_utc"],
                "first_request_utc": service["first_request_utc"],
                "creation_observed_delay_s": (created_observed - scale_sent).total_seconds(),
                "scheduling_observed_delay_s": (scheduled_observed - scale_sent).total_seconds(),
                "startup_observed_delay_s": (started_observed - scale_sent).total_seconds(),
                "readiness_observed_delay_s": (ready_observed - scale_sent).total_seconds(),
                "effective_serving_delay_s": (first_request - scale_sent).total_seconds(),
                "api_creation_from_scale_s": (created_raw - scale_sent).total_seconds(),
                "scheduling_raw_s": (scheduled_raw - created_raw).total_seconds(),
                "startup_raw_s": (started_raw - scheduled_raw).total_seconds(),
                "container_to_ready_raw_s": (ready_raw - started_raw).total_seconds(),
            })

        with (output / "per-pod.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        summary = {
            "schema_version": 1,
            "valid": True,
            "environment": "azure-k3s-native",
            "cache_treatment": "pre-pulled-if-not-present",
            "baseline_replicas": 1,
            "target_replicas": args.target_replicas,
            "increment": args.target_replicas - 1,
            "repetition": args.repetition,
            "forecast_available_utc": iso(forecast),
            "controller_decision_utc": iso(decision),
            "scale_request_sent_utc": iso(scale_sent),
            "scale_request_ack_utc": iso(scale_ack),
            "decision_delay_ms": (decision - forecast).total_seconds() * 1000,
            "scale_api_roundtrip_ms": (scale_ack - scale_sent).total_seconds() * 1000,
            "trial_readiness_delay_s": max(r["readiness_observed_delay_s"] for r in rows),
            "trial_effective_serving_delay_s": max(r["effective_serving_delay_s"] for r in rows),
            "new_pod_count": len(rows),
            "probe_attempts": len(probe_after_scale),
            "successful_probe_attempts": sum(not r["error"] for r in probe_after_scale),
            "probe_max_observed_gap_ms": max(probe_gaps_ms) if probe_gaps_ms else None,
            "poll_milliseconds": args.poll_ms,
        }
        save_json(output / "trial-summary.json", summary)
        save_json(output / "pods-final.json", get_pods())
        save_json(output / "deployment-final.json", kubectl("get", "deployment/benchmark-app", "-n", "default", "-o", "json", json_output=True))
        save_json(output / "events-final.json", kubectl("get", "events", "-n", "default", "-o", "json", json_output=True))
        print(json.dumps(summary))
    except Exception as exc:
        save_json(output / "invalid-trial.json", {"valid": False, "reason": str(exc), "captured_utc": iso()})
        raise
    finally:
        probe_stop.set()
        if probe_thread and probe_thread.is_alive():
            probe_thread.join(timeout=5)
        kubectl("scale", "deployment/benchmark-app", "-n", "default", "--replicas=1")
        kubectl("rollout", "status", "deployment/benchmark-app", "-n", "default", "--timeout=180s")


if __name__ == "__main__":
    main()
