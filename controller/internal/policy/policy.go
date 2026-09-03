package policy

import (
	"errors"
	"fmt"
	"math"
)

type CapacityPoint struct {
	Replicas int     `json:"replicas"`
	RPS      float64 `json:"rps"`
}

type Config struct {
	PolicyID                   string          `json:"policy_id"`
	PolicyVersion              string          `json:"policy_version"`
	CapacityLookup             []CapacityPoint `json:"capacity_lookup"`
	ForecastHorizonSeconds     int             `json:"forecast_horizon_seconds"`
	DecisionIntervalSeconds    int             `json:"decision_interval_seconds"`
	MinReplicas                int             `json:"min_replicas"`
	MaxReplicas                int             `json:"max_replicas"`
	InitialReplicas            int             `json:"initial_replicas"`
	SafetyFactor               float64         `json:"safety_factor"`
	ScaleDownStabilizationSecs int             `json:"scale_down_stabilization_seconds"`
	MaxScaleDownStep           int             `json:"max_scale_down_step"`
	MaxScaleUpStep             int             `json:"max_scale_up_step"`
}

func (c Config) Validate() error {
	if c.PolicyID == "" || c.PolicyVersion == "" {
		return errors.New("policy identity is required")
	}
	if c.MinReplicas < 1 || c.MaxReplicas < c.MinReplicas {
		return errors.New("invalid replica bounds")
	}
	if c.InitialReplicas < c.MinReplicas || c.InitialReplicas > c.MaxReplicas {
		return errors.New("initial replicas outside bounds")
	}
	if c.SafetyFactor <= 0 || math.IsNaN(c.SafetyFactor) || math.IsInf(c.SafetyFactor, 0) {
		return errors.New("safety factor must be finite and positive")
	}
	if c.DecisionIntervalSeconds <= 0 || c.ForecastHorizonSeconds <= 0 {
		return errors.New("decision interval and horizon must be positive")
	}
	if c.ScaleDownStabilizationSecs < 0 || c.ScaleDownStabilizationSecs%c.DecisionIntervalSeconds != 0 {
		return errors.New("scale-down stabilization must be nonnegative and divisible by the decision interval")
	}
	if c.MaxScaleDownStep < 1 || c.MaxScaleUpStep < 0 {
		return errors.New("invalid scaling step")
	}
	if len(c.CapacityLookup) == 0 {
		return errors.New("capacity lookup is required")
	}
	previousReplicas, previousRPS := 0, -1.0
	for _, point := range c.CapacityLookup {
		if point.Replicas <= previousReplicas || point.RPS <= previousRPS || math.IsNaN(point.RPS) || math.IsInf(point.RPS, 0) {
			return errors.New("capacity lookup must increase monotonically")
		}
		previousReplicas, previousRPS = point.Replicas, point.RPS
	}
	if c.CapacityLookup[0].Replicas > c.MinReplicas || c.CapacityLookup[len(c.CapacityLookup)-1].Replicas < c.MaxReplicas {
		return errors.New("capacity lookup does not cover replica bounds")
	}
	return nil
}

type Decision struct {
	DecisionSequence          int     `json:"decision_sequence"`
	InputWorkloadRPS          float64 `json:"input_workload_rps"`
	SafetyAdjustedWorkloadRPS float64 `json:"safety_adjusted_workload_rps"`
	RawReplicas               int     `json:"raw_replicas"`
	BoundedReplicas           int     `json:"bounded_replicas"`
	StabilizedReplicas        int     `json:"stabilized_replicas"`
	PriorCommandedReplicas    int     `json:"prior_commanded_replicas"`
	CommandedReplicas         int     `json:"commanded_replicas"`
	Action                    string  `json:"action"`
	ScaleDownHeld             bool    `json:"scale_down_held"`
}

type Engine struct {
	config  Config
	history []int
	command int
	seq     int
}

func NewEngine(config Config) (*Engine, error) {
	if err := config.Validate(); err != nil {
		return nil, err
	}
	return &Engine{config: config, command: config.InitialReplicas}, nil
}

func (e *Engine) RawReplicas(workloadRPS float64) (int, float64, error) {
	if workloadRPS < 0 || math.IsNaN(workloadRPS) || math.IsInf(workloadRPS, 0) {
		return 0, 0, errors.New("workload must be finite and nonnegative")
	}
	adjusted := workloadRPS * e.config.SafetyFactor
	for _, point := range e.config.CapacityLookup {
		if adjusted <= point.RPS+1e-9 {
			return point.Replicas, adjusted, nil
		}
	}
	return 0, adjusted, fmt.Errorf("workload %.6f RPS exceeds validated capacity", adjusted)
}

func (e *Engine) Decide(workloadRPS float64) (Decision, error) {
	raw, adjusted, err := e.RawReplicas(workloadRPS)
	if err != nil {
		return Decision{}, err
	}
	bounded := raw
	if bounded < e.config.MinReplicas {
		bounded = e.config.MinReplicas
	}
	if bounded > e.config.MaxReplicas {
		bounded = e.config.MaxReplicas
	}
	e.history = append(e.history, bounded)
	windowSamples := e.config.ScaleDownStabilizationSecs / e.config.DecisionIntervalSeconds
	stabilized := bounded
	if windowSamples > 0 {
		start := len(e.history) - windowSamples
		if start < 0 {
			start = 0
		}
		for _, candidate := range e.history[start:] {
			if candidate > stabilized {
				stabilized = candidate
			}
		}
	}
	previous, commanded := e.command, e.command
	if stabilized > previous {
		commanded = stabilized
		if e.config.MaxScaleUpStep > 0 && commanded > previous+e.config.MaxScaleUpStep {
			commanded = previous + e.config.MaxScaleUpStep
		}
	} else if stabilized < previous {
		commanded = previous - e.config.MaxScaleDownStep
		if commanded < stabilized {
			commanded = stabilized
		}
	}
	action := "none"
	if commanded > previous {
		action = "scale_up"
	} else if commanded < previous {
		action = "scale_down"
	}
	decision := Decision{
		DecisionSequence: e.seq, InputWorkloadRPS: workloadRPS, SafetyAdjustedWorkloadRPS: adjusted,
		RawReplicas: raw, BoundedReplicas: bounded, StabilizedReplicas: stabilized,
		PriorCommandedReplicas: previous, CommandedReplicas: commanded, Action: action,
		ScaleDownHeld: bounded < previous && commanded >= previous,
	}
	e.command, e.seq = commanded, e.seq+1
	return decision, nil
}
