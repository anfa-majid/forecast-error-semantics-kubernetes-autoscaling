package safety

import "testing"

func testConfig() Config { return Config{PolicyID:"safety-v1",PolicyVersion:"1.0.0",ObservationIntervalSecs:1,TriggerPersistenceSecs:2,ReleaseHoldSecs:30,MinReplicas:1,MaxReplicas:4,CapacityLookup:[]CapacityPoint{{1,30},{2,40},{3,55},{4,65}}} }
func obs(seq, demand int) Observation { return Observation{RunID:"run-1",Sequence:seq,WindowStartMS:int64(seq*1000),WindowEndMS:int64((seq+1)*1000),DispatchCount:demand,ObservedDemandRPS:float64(demand)} }

func TestTriggerAndArbitration(t *testing.T){
	e,_:=NewEngine(testConfig()); first,_:=e.Evaluate(obs(0,60),1,1); second,_:=e.Evaluate(obs(1,60),1,1)
	if first.Active || second.Event!="intervention_started" || second.FinalCommandedReplicas!=4 { t.Fatalf("first=%+v second=%+v",first,second) }
}
func TestProtectionPreventsPrematureRelease(t *testing.T){
	e,_:=NewEngine(testConfig()); e.Evaluate(obs(0,60),1,1); e.Evaluate(obs(1,60),1,1)
	for i:=2;i<80;i++ { d,_:=e.Evaluate(obs(i,60),4,1); if !d.Active { t.Fatalf("released during protection at %d",i) } }
}
func TestReleaseAfterProtectionClears(t *testing.T){
	e,_:=NewEngine(testConfig()); e.Evaluate(obs(0,60),1,1); e.Evaluate(obs(1,60),1,1)
	for i:=2;i<31;i++ { d,_:=e.Evaluate(obs(i,25),4,1); if !d.Active { t.Fatalf("early release %d",i) } }
	d,_:=e.Evaluate(obs(31,25),4,1); if d.Event!="intervention_released" || d.FinalCommandedReplicas!=1 { t.Fatalf("%+v",d) }
}
func TestObservationCountMustMatchRate(t *testing.T){
	e,_:=NewEngine(testConfig()); bad:=obs(0,25);bad.ObservedDemandRPS=24
	if _,err:=e.Evaluate(bad,1,1);err==nil { t.Fatal("expected validation error") }
}
