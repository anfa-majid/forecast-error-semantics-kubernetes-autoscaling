"""Deterministic reference model for the Step 16 reactive safety layer."""
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass(frozen=True)
class CapacityPoint:
    replicas: int
    rps: float

@dataclass(frozen=True)
class SafetyConfig:
    policy_id: str
    interval_seconds: int
    persistence_seconds: int
    release_hold_seconds: int
    minimum: int
    maximum: int
    capacity: tuple[CapacityPoint, ...]

    @classmethod
    def load(cls, path: Path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = cls(raw["policy_id"], int(raw["observation_interval_seconds"]),
                     int(raw["trigger_persistence_seconds"]), int(raw["release_hold_seconds"]),
                     int(raw["min_replicas"]), int(raw["max_replicas"]),
                     tuple(CapacityPoint(int(p["replicas"]), float(p["rps"])) for p in raw["capacity_lookup"]))
        result.validate()
        return result

    def validate(self):
        if not self.policy_id or self.interval_seconds <= 0:
            raise ValueError("policy identity and positive interval required")
        if self.persistence_seconds < self.interval_seconds or self.persistence_seconds % self.interval_seconds:
            raise ValueError("persistence must be whole positive windows")
        if self.release_hold_seconds < 0 or self.release_hold_seconds % self.interval_seconds:
            raise ValueError("release hold must be whole windows")
        if self.minimum < 1 or self.maximum < self.minimum or not self.capacity:
            raise ValueError("invalid bounds or capacity")
        prior_r, prior_c = 0, -1.0
        for point in self.capacity:
            if point.replicas <= prior_r or point.rps <= prior_c:
                raise ValueError("capacity must increase monotonically")
            prior_r, prior_c = point.replicas, point.rps
        if self.capacity[0].replicas > self.minimum or self.capacity[-1].replicas < self.maximum:
            raise ValueError("capacity does not cover bounds")

    def required_replicas(self, demand_rps: float) -> int:
        if demand_rps < 0:
            raise ValueError("demand must be nonnegative")
        for point in self.capacity:
            if demand_rps <= point.rps + 1e-9:
                return point.replicas
        raise ValueError(f"demand {demand_rps} exceeds validated capacity")

    def ready_capacity(self, replicas: int) -> float:
        for point in self.capacity:
            if point.replicas == replicas:
                return point.rps
        raise ValueError("ready replicas outside capacity lookup")

class SafetyEngine:
    """Safety floor only; the sole controller remains the Deployment scale writer."""
    def __init__(self, config: SafetyConfig):
        self.config = config
        self.overload_windows = 0
        self.hold_windows = 0
        self.floor = config.minimum
        self.active = False
        self.sequence = 0

    def evaluate(self, observed_demand_rps, ready_replicas: int, predictive_replicas: int) -> dict:
        if not self.config.minimum <= predictive_replicas <= self.config.maximum:
            raise ValueError("predictive replicas outside bounds")
        ready_capacity = self.config.ready_capacity(ready_replicas)
        missing = observed_demand_rps is None
        overload = False if missing else observed_demand_rps > ready_capacity + 1e-9
        required = self.config.minimum if missing else self.config.required_replicas(observed_demand_rps)
        protection_needed = False if missing else required > predictive_replicas
        self.overload_windows = self.overload_windows + 1 if overload else 0
        threshold = self.config.persistence_seconds // self.config.interval_seconds
        triggered = overload and self.overload_windows >= threshold
        event = "none"
        if triggered:
            old_floor = self.floor
            self.floor = max(self.floor, required)
            self.hold_windows = self.config.release_hold_seconds // self.config.interval_seconds
            if not self.active:
                event = "intervention_started"
            elif self.floor > old_floor:
                event = "intervention_raised"
            self.active = True
        elif self.active:
            if protection_needed:
                self.hold_windows = self.config.release_hold_seconds // self.config.interval_seconds
            elif self.hold_windows > 0:
                self.hold_windows -= 1
            if not protection_needed and self.hold_windows == 0:
                self.active, self.floor, event = False, self.config.minimum, "intervention_released"
        safety_floor = self.floor if self.active else self.config.minimum
        final = max(predictive_replicas, safety_floor)
        record = {
            "record_type": "safety_decision", "safety_sequence": self.sequence,
            "policy_id": self.config.policy_id, "observation_missing": missing,
            "observed_demand_rps": observed_demand_rps, "ready_replicas": ready_replicas,
            "ready_capacity_rps": ready_capacity, "overload": overload,
            "protection_needed": protection_needed,
            "consecutive_overload_windows": self.overload_windows, "triggered": triggered,
            "event": event, "safety_active": self.active,
            "observed_demand_required_replicas": required, "safety_floor_replicas": safety_floor,
            "predictive_replicas": predictive_replicas, "final_commanded_replicas": final,
            "intervention_changes_command": final > predictive_replicas,
            "release_hold_remaining_seconds": self.hold_windows * self.config.interval_seconds
        }
        self.sequence += 1
        return record
