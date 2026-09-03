package controller

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/anfa-research/predictive-autoscaler/internal/arbiter"
	"github.com/anfa-research/predictive-autoscaler/internal/forecast"
	"github.com/anfa-research/predictive-autoscaler/internal/policy"
	"github.com/anfa-research/predictive-autoscaler/internal/safety"
)

type fakeScaler struct {
	current   int
	updates   []int
	updateErr error
}

func (f *fakeScaler) Current(context.Context) (ScaleResult, error) {
	return ScaleResult{Replicas: f.current, ResourceVersion: "1"}, nil
}
func (f *fakeScaler) Update(_ context.Context, replicas int) (ScaleResult, error) {
	if f.updateErr != nil {
		return ScaleResult{}, f.updateErr
	}
	f.current = replicas
	f.updates = append(f.updates, replicas)
	return ScaleResult{Replicas: replicas, ResourceVersion: "2"}, nil
}

type memoryLogger struct{ records []Record }

func (m *memoryLogger) Write(record Record) error { m.records = append(m.records, record); return nil }
type fakeReady struct{ replicas int }
func(f fakeReady)ReadyReplicas(context.Context)(int,error){return f.replicas,nil}
type transientReady struct{ replicas, failures, calls int }
func(f *transientReady)ReadyReplicas(context.Context)(int,error){
	f.calls++
	if f.calls<=f.failures{return 0,errors.New("transient readiness read")}
	return f.replicas,nil
}

func controllerFor(t *testing.T, values ...float64) (*Controller, *fakeScaler, *memoryLogger) {
	t.Helper()
	config := policy.Config{PolicyID: "anfa-empirical-replica-policy-v1", PolicyVersion: "1.0.0", CapacityLookup: []policy.CapacityPoint{{Replicas: 1, RPS: 30}, {Replicas: 2, RPS: 40}, {Replicas: 3, RPS: 55}, {Replicas: 4, RPS: 65}}, ForecastHorizonSeconds: 6, DecisionIntervalSeconds: 1, MinReplicas: 1, MaxReplicas: 4, InitialReplicas: 1, SafetyFactor: 1, ScaleDownStabilizationSecs: 30, MaxScaleDownStep: 1}
	engine, err := policy.NewEngine(config)
	if err != nil {
		t.Fatal(err)
	}
	trace := forecast.Trace{ByIssued: map[int64]forecast.Row{}, SHA256: "forecast-hash", TraceID: "trace", Condition: "condition"}
	for index, value := range values {
		row := forecast.Row{TraceID: "trace", Condition: "condition", IssuedOffsetMS: int64(index * 1000), TargetOffsetMS: int64(index*1000 + 6000), HorizonMS: 6000, PredictedRPS: value, MutationID: "mutation", PairManifestID: "pair"}
		trace.Rows = append(trace.Rows, row)
		trace.ByIssued[row.IssuedOffsetMS] = row
	}
	scaler, logger := &fakeScaler{current: 1}, &memoryLogger{}
	now := time.Date(2026, 8, 7, 0, 0, 0, 0, time.UTC)
	ctl := &Controller{Identity: RunIdentity{ExperimentID: "experiment", RunID: "run", ControllerID: "controller"}, Policy: engine, PolicyConfig: config, PolicyHash: "policy-hash", Forecast: trace, Scaler: scaler, Logger: logger, Now: func() time.Time { return now }}
	return ctl, scaler, logger
}

func TestNoAPIWriteForRepeatedDecision(t *testing.T) {
	ctl, scaler, logger := controllerFor(t, 25, 25)
	if err := ctl.Tick(context.Background(), 0); err != nil {
		t.Fatal(err)
	}
	if err := ctl.Tick(context.Background(), 1000); err != nil {
		t.Fatal(err)
	}
	if len(scaler.updates) != 0 || len(logger.records) != 2 || logger.records[1].APIResult != "not_required" {
		t.Fatalf("updates=%v records=%+v", scaler.updates, logger.records)
	}
}

func TestSafetyTickRetriesTransientReadyRead(t *testing.T) {
	ctl, _, logger := controllerFor(t, 25)
	arb, err := arbiter.New(1, 4, 1)
	if err != nil { t.Fatal(err) }
	safe, err := safety.NewEngine(safety.Config{PolicyID:"safety-v1",PolicyVersion:"1.0.0",ObservationIntervalSecs:1,TriggerPersistenceSecs:3,ReleaseHoldSecs:30,MinReplicas:1,MaxReplicas:4,CapacityLookup:[]safety.CapacityPoint{{Replicas:1,RPS:30},{Replicas:2,RPS:40},{Replicas:3,RPS:55},{Replicas:4,RPS:65}}})
	if err != nil { t.Fatal(err) }
	ready := &transientReady{replicas:1,failures:2}
	ctl.Arbiter, ctl.Safety, ctl.Ready, ctl.SafetyHash = arb, safe, ready, "safety-hash"
	observation := safety.Observation{RunID:"run",Sequence:0,WindowStartMS:0,WindowEndMS:1000,DispatchCount:25,ObservedDemandRPS:25}
	if err := ctl.SafetyTick(context.Background(), observation); err != nil { t.Fatal(err) }
	if ready.calls != 3 { t.Fatalf("ready calls=%d want=3", ready.calls) }
	if got := logger.records[len(logger.records)-1]; got.RecordType != "safety_decision" { t.Fatalf("record=%+v", got) }
}

func TestSafetyTickFailsAfterBoundedReadyRetries(t *testing.T) {
	ctl, _, _ := controllerFor(t, 25)
	arb, _ := arbiter.New(1, 4, 1)
	safe, _ := safety.NewEngine(safety.Config{PolicyID:"safety-v1",PolicyVersion:"1.0.0",ObservationIntervalSecs:1,TriggerPersistenceSecs:3,ReleaseHoldSecs:30,MinReplicas:1,MaxReplicas:4,CapacityLookup:[]safety.CapacityPoint{{Replicas:1,RPS:30},{Replicas:2,RPS:40},{Replicas:3,RPS:55},{Replicas:4,RPS:65}}})
	ready := &transientReady{replicas:1,failures:10}
	ctl.Arbiter, ctl.Safety, ctl.Ready, ctl.SafetyHash = arb, safe, ready, "safety-hash"
	observation := safety.Observation{RunID:"run",Sequence:0,WindowStartMS:0,WindowEndMS:1000,DispatchCount:25,ObservedDemandRPS:25}
	err := ctl.SafetyTick(context.Background(), observation)
	if err == nil || ready.calls != readyReadMaxAttempts { t.Fatalf("err=%v calls=%d", err, ready.calls) }
}

func TestScaleUpAndCompleteLog(t *testing.T) {
	ctl, scaler, logger := controllerFor(t, 60)
	if err := ctl.Tick(context.Background(), 0); err != nil {
		t.Fatal(err)
	}
	if len(scaler.updates) != 1 || scaler.updates[0] != 4 {
		t.Fatalf("updates=%v", scaler.updates)
	}
	record := logger.records[0]
	if record.CommandedReplicas != 4 || record.Action != "scale_up" || record.APIResult != "success" || record.TraceID == "" || record.PolicyConfigSHA256 == "" || record.ForecastSHA256 == "" {
		t.Fatalf("incomplete record: %+v", record)
	}
}

func TestMissingForecastIsFatalAndLogged(t *testing.T) {
	ctl, scaler, logger := controllerFor(t, 25)
	if err := ctl.Tick(context.Background(), 1000); err == nil {
		t.Fatal("expected error")
	}
	if len(scaler.updates) != 0 || len(logger.records) != 1 || logger.records[0].ErrorClass != "missing_forecast" {
		t.Fatalf("updates=%v records=%+v", scaler.updates, logger.records)
	}
}

func TestAPIErrorIsFatalAndLogged(t *testing.T) {
	ctl, scaler, logger := controllerFor(t, 60)
	scaler.updateErr = errors.New("conflict")
	if err := ctl.Tick(context.Background(), 0); err == nil {
		t.Fatal("expected error")
	}
	if len(logger.records) != 1 || logger.records[0].ErrorClass != "kubernetes_scale_error" {
		t.Fatalf("records=%+v", logger.records)
	}
}

func TestPreflightRejectsWrongInitialReplicaCount(t *testing.T) {
	ctl, scaler, _ := controllerFor(t, 25)
	scaler.current = 2
	if err := ctl.Preflight(context.Background()); err == nil {
		t.Fatal("expected preflight error")
	}
}

func TestSafetyArbitrationRaisesFinalCommandWithoutChangingPredictiveCommand(t *testing.T){
	ctl,scaler,logger:=controllerFor(t,25)
	arb,_:=arbiter.New(1,4,1)
	safe,_:=safety.NewEngine(safety.Config{PolicyID:"safety-v1",PolicyVersion:"1.0.0",ObservationIntervalSecs:1,TriggerPersistenceSecs:2,ReleaseHoldSecs:30,MinReplicas:1,MaxReplicas:4,CapacityLookup:[]safety.CapacityPoint{{Replicas:1,RPS:30},{Replicas:2,RPS:40},{Replicas:3,RPS:55},{Replicas:4,RPS:65}}})
	ctl.Arbiter,ctl.Safety,ctl.Ready,ctl.SafetyHash=arb,safe,fakeReady{replicas:1},"safety-hash"
	if err:=ctl.Tick(context.Background(),0);err!=nil{t.Fatal(err)}
	first:=safety.Observation{RunID:"run",Sequence:0,WindowStartMS:0,WindowEndMS:1000,DispatchCount:60,ObservedDemandRPS:60}
	second:=safety.Observation{RunID:"run",Sequence:1,WindowStartMS:1000,WindowEndMS:2000,DispatchCount:60,ObservedDemandRPS:60}
	if err:=ctl.SafetyTick(context.Background(),first);err!=nil{t.Fatal(err)}
	if err:=ctl.SafetyTick(context.Background(),second);err!=nil{t.Fatal(err)}
	if len(scaler.updates)!=1||scaler.updates[0]!=4{t.Fatalf("updates=%v",scaler.updates)}
	record:=logger.records[len(logger.records)-1]
	if record.RecordType!="safety_decision"||record.PredictiveCommandedReplicas!=1||record.FinalCommandedReplicas!=4||!record.InterventionChangesCommand{t.Fatalf("%+v",record)}
}
