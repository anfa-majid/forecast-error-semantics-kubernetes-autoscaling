package safety

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
	PolicyID                 string          `json:"policy_id"`
	PolicyVersion            string          `json:"policy_version"`
	ObservationIntervalSecs  int             `json:"observation_interval_seconds"`
	TriggerPersistenceSecs   int             `json:"trigger_persistence_seconds"`
	ReleaseHoldSecs          int             `json:"release_hold_seconds"`
	MinReplicas              int             `json:"min_replicas"`
	MaxReplicas              int             `json:"max_replicas"`
	CapacityLookup           []CapacityPoint `json:"capacity_lookup"`
}

func (c Config) Validate() error {
	if c.PolicyID == "" || c.PolicyVersion == "" || c.ObservationIntervalSecs <= 0 {
		return errors.New("safety policy identity and positive interval are required")
	}
	if c.TriggerPersistenceSecs < c.ObservationIntervalSecs || c.TriggerPersistenceSecs%c.ObservationIntervalSecs != 0 {
		return errors.New("trigger persistence must be positive whole observation windows")
	}
	if c.ReleaseHoldSecs < 0 || c.ReleaseHoldSecs%c.ObservationIntervalSecs != 0 {
		return errors.New("release hold must be whole observation windows")
	}
	if c.MinReplicas < 1 || c.MaxReplicas < c.MinReplicas || len(c.CapacityLookup) == 0 {
		return errors.New("invalid replica bounds or capacity lookup")
	}
	priorReplicas, priorRPS := 0, -1.0
	for _, point := range c.CapacityLookup {
		if point.Replicas <= priorReplicas || point.RPS <= priorRPS || math.IsNaN(point.RPS) || math.IsInf(point.RPS, 0) {
			return errors.New("capacity lookup must increase monotonically")
		}
		priorReplicas, priorRPS = point.Replicas, point.RPS
	}
	if c.CapacityLookup[0].Replicas > c.MinReplicas || c.CapacityLookup[len(c.CapacityLookup)-1].Replicas < c.MaxReplicas {
		return errors.New("capacity lookup does not cover replica bounds")
	}
	return nil
}

type Observation struct {
	RunID             string  `json:"run_id"`
	Sequence          int     `json:"sequence"`
	WindowStartMS     int64   `json:"window_start_ms"`
	WindowEndMS       int64   `json:"window_end_ms"`
	DispatchCount     int     `json:"dispatch_count"`
	ObservedDemandRPS float64 `json:"observed_demand_rps"`
}

func (o Observation) Validate(intervalSeconds int) error {
	if o.RunID == "" || o.Sequence < 0 || o.WindowStartMS < 0 || o.WindowEndMS-o.WindowStartMS != int64(intervalSeconds*1000) {
		return errors.New("invalid observation identity or window")
	}
	if o.DispatchCount < 0 || o.ObservedDemandRPS < 0 || math.IsNaN(o.ObservedDemandRPS) || math.IsInf(o.ObservedDemandRPS, 0) {
		return errors.New("invalid observed demand")
	}
	expected := float64(o.DispatchCount) / float64(intervalSeconds)
	if math.Abs(expected-o.ObservedDemandRPS) > 1e-9 {
		return errors.New("observed demand does not match dispatch count and window")
	}
	return nil
}

type Decision struct {
	Sequence                    int     `json:"safety_sequence"`
	ObservedDemandRPS           float64 `json:"observed_demand_rps"`
	ReadyReplicas               int     `json:"ready_replicas"`
	ReadyCapacityRPS            float64 `json:"ready_capacity_rps"`
	Overload                    bool    `json:"overload"`
	ProtectionNeeded            bool    `json:"protection_needed"`
	ConsecutiveOverloadWindows  int     `json:"consecutive_overload_windows"`
	Triggered                   bool    `json:"triggered"`
	Event                       string  `json:"event"`
	Active                      bool    `json:"safety_active"`
	ObservedRequiredReplicas    int     `json:"observed_demand_required_replicas"`
	SafetyFloorReplicas         int     `json:"safety_floor_replicas"`
	PredictiveReplicas          int     `json:"predictive_replicas"`
	FinalCommandedReplicas      int     `json:"final_commanded_replicas"`
	InterventionChangesCommand  bool    `json:"intervention_changes_command"`
	ReleaseHoldRemainingSeconds int     `json:"release_hold_remaining_seconds"`
}

type Engine struct {
	config          Config
	overloadWindows int
	holdWindows     int
	floor           int
	active          bool
	sequence        int
}

func NewEngine(config Config) (*Engine, error) {
	if err := config.Validate(); err != nil { return nil, err }
	return &Engine{config: config, floor: config.MinReplicas}, nil
}
func (e *Engine) PolicyID() string { return e.config.PolicyID }

func (e *Engine) capacityForReplicas(replicas int) (float64, error) {
	for _, point := range e.config.CapacityLookup { if point.Replicas == replicas { return point.RPS, nil } }
	return 0, fmt.Errorf("replicas %d outside capacity lookup", replicas)
}

func (e *Engine) requiredReplicas(demand float64) (int, error) {
	if demand < 0 || math.IsNaN(demand) || math.IsInf(demand, 0) { return 0, errors.New("demand must be finite and nonnegative") }
	for _, point := range e.config.CapacityLookup { if demand <= point.RPS+1e-9 { return point.Replicas, nil } }
	return 0, fmt.Errorf("demand %.6f exceeds validated capacity", demand)
}

func (e *Engine) Evaluate(observation Observation, readyReplicas, predictiveReplicas int) (Decision, error) {
	if err := observation.Validate(e.config.ObservationIntervalSecs); err != nil { return Decision{}, err }
	if predictiveReplicas < e.config.MinReplicas || predictiveReplicas > e.config.MaxReplicas { return Decision{}, errors.New("predictive replicas outside bounds") }
	readyCapacity, err := e.capacityForReplicas(readyReplicas); if err != nil { return Decision{}, err }
	required, err := e.requiredReplicas(observation.ObservedDemandRPS); if err != nil { return Decision{}, err }
	overload := observation.ObservedDemandRPS > readyCapacity+1e-9
	protectionNeeded := required > predictiveReplicas
	if overload { e.overloadWindows++ } else { e.overloadWindows = 0 }
	triggered := overload && e.overloadWindows >= e.config.TriggerPersistenceSecs/e.config.ObservationIntervalSecs
	event := "none"
	if triggered {
		oldFloor := e.floor
		if required > e.floor { e.floor = required }
		e.holdWindows = e.config.ReleaseHoldSecs/e.config.ObservationIntervalSecs
		if !e.active { event = "intervention_started" } else if e.floor > oldFloor { event = "intervention_raised" }
		e.active = true
	} else if e.active {
		if protectionNeeded { e.holdWindows = e.config.ReleaseHoldSecs/e.config.ObservationIntervalSecs } else if e.holdWindows > 0 { e.holdWindows-- }
		if !protectionNeeded && e.holdWindows == 0 { e.active, e.floor, event = false, e.config.MinReplicas, "intervention_released" }
	}
	floor := e.config.MinReplicas; if e.active { floor = e.floor }
	final := predictiveReplicas; if floor > final { final = floor }
	decision := Decision{Sequence:e.sequence, ObservedDemandRPS:observation.ObservedDemandRPS, ReadyReplicas:readyReplicas,
		ReadyCapacityRPS:readyCapacity, Overload:overload, ProtectionNeeded:protectionNeeded,
		ConsecutiveOverloadWindows:e.overloadWindows, Triggered:triggered, Event:event, Active:e.active,
		ObservedRequiredReplicas:required, SafetyFloorReplicas:floor, PredictiveReplicas:predictiveReplicas,
		FinalCommandedReplicas:final, InterventionChangesCommand:final>predictiveReplicas,
		ReleaseHoldRemainingSeconds:e.holdWindows*e.config.ObservationIntervalSecs}
	e.sequence++
	return decision,nil
}
