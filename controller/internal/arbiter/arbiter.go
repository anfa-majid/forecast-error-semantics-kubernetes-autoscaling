package arbiter

import (
	"errors"
	"sync"
)

type Source string
const (
	SourcePredictive Source = "predictive_tick"
	SourceSafety Source = "safety_observation"
)

type Decision struct {
	Source                    Source `json:"arbitration_source"`
	PriorFinalReplicas        int    `json:"prior_final_replicas"`
	PredictiveReplicas        int    `json:"predictive_replicas"`
	SafetyFloorReplicas       int    `json:"safety_floor_replicas"`
	FinalReplicas             int    `json:"final_commanded_replicas"`
	Action                    string `json:"final_action"`
	SafetyChangesCommand      bool   `json:"safety_changes_command"`
}

type Engine struct {
	mu sync.Mutex
	minimum int
	maximum int
	predictive int
	safetyFloor int
	final int
}

func New(minimum,maximum,initial int)(*Engine,error){
	if minimum<1||maximum<minimum||initial<minimum||initial>maximum{return nil,errors.New("invalid arbiter bounds")}
	return &Engine{minimum:minimum,maximum:maximum,predictive:initial,safetyFloor:minimum,final:initial},nil
}

func (e *Engine) UpdatePredictive(replicas int)(Decision,error){
	e.mu.Lock();defer e.mu.Unlock();return e.updateLocked(SourcePredictive,replicas,e.safetyFloor)
}
func (e *Engine) UpdateSafetyFloor(replicas int)(Decision,error){
	e.mu.Lock();defer e.mu.Unlock();return e.updateLocked(SourceSafety,e.predictive,replicas)
}

func (e *Engine) updateLocked(source Source,predictive,safetyFloor int)(Decision,error){
	if predictive<e.minimum||predictive>e.maximum||safetyFloor<e.minimum||safetyFloor>e.maximum{return Decision{},errors.New("arbiter input outside bounds")}
	prior:=e.final;final:=predictive;if safetyFloor>final{final=safetyFloor}
	action:="none";if final>prior{action="scale_up"}else if final<prior{action="scale_down"}
	e.predictive,e.safetyFloor,e.final=predictive,safetyFloor,final
	return Decision{Source:source,PriorFinalReplicas:prior,PredictiveReplicas:predictive,SafetyFloorReplicas:safetyFloor,
		FinalReplicas:final,Action:action,SafetyChangesCommand:safetyFloor>predictive},nil
}

func(e *Engine) Snapshot()(predictive,safetyFloor,final int){e.mu.Lock();defer e.mu.Unlock();return e.predictive,e.safetyFloor,e.final}
