from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PolicyConfig:
    capacity_lookup_rps: tuple[tuple[int, float], ...]
    min_replicas: int = 1
    max_replicas: int = 4
    initial_replicas: int = 1
    safety_factor: float = 1.0
    scale_down_stabilization_s: int = 30
    decision_interval_s: int = 1
    max_scale_down_step: int = 1
    max_scale_up_step: int | None = None

    def validate(self) -> None:
        if self.min_replicas < 1 or self.max_replicas < self.min_replicas:
            raise ValueError("invalid replica bounds")
        if not (self.min_replicas <= self.initial_replicas <= self.max_replicas):
            raise ValueError("initial replicas outside bounds")
        if self.safety_factor <= 0:
            raise ValueError("safety factor must be positive")
        if self.decision_interval_s <= 0 or self.scale_down_stabilization_s < 0:
            raise ValueError("invalid timing configuration")
        if self.scale_down_stabilization_s % self.decision_interval_s:
            raise ValueError("stabilization must be divisible by decision interval")
        counts = [count for count, _ in self.capacity_lookup_rps]
        limits = [limit for _, limit in self.capacity_lookup_rps]
        if counts != sorted(counts) or limits != sorted(limits):
            raise ValueError("capacity lookup must increase monotonically")
        if counts[0] > self.min_replicas or counts[-1] < self.max_replicas:
            raise ValueError("capacity lookup does not cover replica bounds")


@dataclass(frozen=True)
class Decision:
    decision_index: int
    input_workload_rps: float
    safety_adjusted_workload_rps: float
    raw_replicas: int
    bounded_replicas: int
    stabilized_replicas: int
    prior_commanded_replicas: int
    commanded_replicas: int
    action: str
    scale_down_held: bool


class PolicyEngine:
    """Stateful deterministic replica policy shared by oracle/forecast inputs."""

    def __init__(self, config: PolicyConfig):
        config.validate()
        self.config = config
        self.commanded = config.initial_replicas
        self.bounded_history: list[int] = []
        self.decision_index = 0

    def raw_replicas(self, workload_rps: float) -> tuple[int, float]:
        if workload_rps < 0:
            raise ValueError("workload cannot be negative")
        adjusted = workload_rps * self.config.safety_factor
        for count, capacity in self.config.capacity_lookup_rps:
            if adjusted <= capacity + 1e-9:
                return count, adjusted
        raise ValueError(f"workload {adjusted:.6f} RPS exceeds validated capacity")

    def decide(self, workload_rps: float) -> Decision:
        raw, adjusted = self.raw_replicas(workload_rps)
        bounded = min(self.config.max_replicas, max(self.config.min_replicas, raw))
        self.bounded_history.append(bounded)

        window_samples = self.config.scale_down_stabilization_s // self.config.decision_interval_s
        if window_samples > 0:
            window = self.bounded_history[-window_samples:]
            stabilized = max(window)
        else:
            stabilized = bounded

        previous = self.commanded
        if stabilized > previous:
            if self.config.max_scale_up_step is None:
                commanded = stabilized
            else:
                commanded = min(stabilized, previous + self.config.max_scale_up_step)
        elif stabilized < previous:
            commanded = max(stabilized, previous - self.config.max_scale_down_step)
        else:
            commanded = previous

        action = "scale_up" if commanded > previous else "scale_down" if commanded < previous else "none"
        decision = Decision(
            decision_index=self.decision_index,
            input_workload_rps=workload_rps,
            safety_adjusted_workload_rps=adjusted,
            raw_replicas=raw,
            bounded_replicas=bounded,
            stabilized_replicas=stabilized,
            prior_commanded_replicas=previous,
            commanded_replicas=commanded,
            action=action,
            scale_down_held=bounded < previous and commanded >= previous,
        )
        self.commanded = commanded
        self.decision_index += 1
        return decision


def run_policy(config: PolicyConfig, workload: Iterable[float]) -> list[Decision]:
    engine = PolicyEngine(config)
    return [engine.decide(value) for value in workload]
