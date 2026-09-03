package safety

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestObservationStoreStrictSequence(t *testing.T){
	store,_:=NewObservationStore("run-1",1)
	if err:=store.Submit(obs(0,25));err!=nil{t.Fatal(err)}
	if err:=store.Submit(obs(0,25));err==nil{t.Fatal("expected duplicate rejection")}
	if err:=store.Submit(obs(2,25));err==nil{t.Fatal("expected gap rejection")}
	if err:=store.Submit(obs(1,25));err!=nil{t.Fatal(err)}
	if store.LatestSequence()!=1{t.Fatalf("latest=%d",store.LatestSequence())}
}

func TestObservationStoreRejectsCrossRun(t *testing.T){
	store,_:=NewObservationStore("run-1",1);row:=obs(0,25);row.RunID="other"
	if err:=store.Submit(row);err==nil{t.Fatal("expected run mismatch")}
}

func TestObservationHTTP(t *testing.T){
	store,_:=NewObservationStore("run-1",1);server:=httptest.NewServer(store.Handler());defer server.Close()
	body:=[]byte(`{"run_id":"run-1","sequence":0,"window_start_ms":0,"window_end_ms":1000,"dispatch_count":25,"observed_demand_rps":25}`)
	response,err:=http.Post(server.URL+"/v1/safety/observations","application/json",bytes.NewReader(body));if err!=nil{t.Fatal(err)}
	defer response.Body.Close();if response.StatusCode!=http.StatusAccepted{t.Fatalf("status=%d",response.StatusCode)}
	if _,ok:=store.Get(0);!ok{t.Fatal("accepted observation missing")}
}

func TestObservationHTTPRejectsUnknownField(t *testing.T){
	store,_:=NewObservationStore("run-1",1);request:=httptest.NewRequest(http.MethodPost,"/v1/safety/observations",bytes.NewBufferString(`{"run_id":"run-1","sequence":0,"window_start_ms":0,"window_end_ms":1000,"dispatch_count":25,"observed_demand_rps":25,"extra":true}`));recorder:=httptest.NewRecorder()
	store.Handler().ServeHTTP(recorder,request);if recorder.Code!=http.StatusBadRequest{t.Fatalf("status=%d",recorder.Code)}
}

func TestObservationHTTPInvokesAcceptedCallback(t *testing.T){
	store,_:=NewObservationStore("run-1",1);called:=false;store.SetOnAccepted(func(row Observation)error{called=row.Sequence==0;return nil})
	request:=httptest.NewRequest(http.MethodPost,"/v1/safety/observations",bytes.NewBufferString(`{"run_id":"run-1","sequence":0,"window_start_ms":0,"window_end_ms":1000,"dispatch_count":25,"observed_demand_rps":25}`));recorder:=httptest.NewRecorder();store.Handler().ServeHTTP(recorder,request)
	if recorder.Code!=http.StatusAccepted||!called{t.Fatalf("status=%d called=%v",recorder.Code,called)}
}
