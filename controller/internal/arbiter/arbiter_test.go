package arbiter
import "testing"

func TestSafetyFloorWinsWithoutChangingPredictiveState(t *testing.T){
	e,_:=New(1,4,1);d,_:=e.UpdateSafetyFloor(4)
	if d.FinalReplicas!=4||!d.SafetyChangesCommand||d.Action!="scale_up"{t.Fatalf("%+v",d)}
	p,s,f:=e.Snapshot();if p!=1||s!=4||f!=4{t.Fatalf("snapshot=%d,%d,%d",p,s,f)}
}
func TestPredictiveTickCannotScaleBelowActiveSafetyFloor(t *testing.T){
	e,_:=New(1,4,1);e.UpdateSafetyFloor(4);d,_:=e.UpdatePredictive(1)
	if d.FinalReplicas!=4||d.Action!="none"{t.Fatalf("%+v",d)}
}
func TestPredictiveScaleUpAboveFloor(t *testing.T){
	e,_:=New(1,4,1);e.UpdateSafetyFloor(3);d,_:=e.UpdatePredictive(4)
	if d.FinalReplicas!=4||d.SafetyChangesCommand||d.Action!="scale_up"{t.Fatalf("%+v",d)}
}
func TestReleaseDelegatesToPredictiveCommand(t *testing.T){
	e,_:=New(1,4,1);e.UpdateSafetyFloor(4);d,_:=e.UpdateSafetyFloor(1)
	if d.FinalReplicas!=1||d.Action!="scale_down"{t.Fatalf("%+v",d)}
}
