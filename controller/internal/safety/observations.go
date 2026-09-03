package safety

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"sync"
)

type ObservationStore struct {
	mu              sync.RWMutex
	runID           string
	intervalSeconds int
	rows            map[int]Observation
	latestSequence  int
	onAccepted      func(Observation) error
}

func(s *ObservationStore)SetOnAccepted(callback func(Observation)error){s.mu.Lock();defer s.mu.Unlock();s.onAccepted=callback}

func NewObservationStore(runID string, intervalSeconds int) (*ObservationStore, error) {
	if runID == "" || intervalSeconds <= 0 { return nil, errors.New("run identity and positive interval are required") }
	return &ObservationStore{runID:runID, intervalSeconds:intervalSeconds, rows:map[int]Observation{}, latestSequence:-1},nil
}

func (s *ObservationStore) Submit(observation Observation) error {
	if err:=observation.Validate(s.intervalSeconds);err!=nil{return err}
	if observation.RunID!=s.runID{return errors.New("observation run_id mismatch")}
	s.mu.Lock();defer s.mu.Unlock()
	expected:=s.latestSequence+1
	if observation.Sequence!=expected{return fmt.Errorf("observation sequence=%d expected=%d",observation.Sequence,expected)}
	expectedStart:=int64(observation.Sequence*s.intervalSeconds*1000)
	if observation.WindowStartMS!=expectedStart{return fmt.Errorf("observation window starts at %d expected %d",observation.WindowStartMS,expectedStart)}
	s.rows[observation.Sequence]=observation;s.latestSequence=observation.Sequence
	return nil
}

func (s *ObservationStore) Get(sequence int)(Observation,bool){
	s.mu.RLock();defer s.mu.RUnlock();row,ok:=s.rows[sequence];return row,ok
}

func (s *ObservationStore) LatestSequence()int{s.mu.RLock();defer s.mu.RUnlock();return s.latestSequence}

func (s *ObservationStore) Handler() http.Handler {
	mux:=http.NewServeMux()
	mux.HandleFunc("/v1/safety/observations",func(w http.ResponseWriter,r *http.Request){
		if r.Method!=http.MethodPost{http.Error(w,"method not allowed",http.StatusMethodNotAllowed);return}
		r.Body=http.MaxBytesReader(w,r.Body,16*1024)
		decoder:=json.NewDecoder(r.Body);decoder.DisallowUnknownFields()
		var observation Observation
		if err:=decoder.Decode(&observation);err!=nil{http.Error(w,"invalid observation: "+err.Error(),http.StatusBadRequest);return}
		if decoder.Decode(&struct{}{})==nil{http.Error(w,"multiple JSON values",http.StatusBadRequest);return}
		if err:=s.Submit(observation);err!=nil{http.Error(w,err.Error(),http.StatusConflict);return}
		s.mu.RLock();callback:=s.onAccepted;s.mu.RUnlock()
		if callback!=nil{if err:=callback(observation);err!=nil{http.Error(w,"safety evaluation failed: "+err.Error(),http.StatusInternalServerError);return}}
		w.Header().Set("Content-Type","application/json");w.WriteHeader(http.StatusAccepted)
		_ = json.NewEncoder(w).Encode(map[string]any{"accepted":true,"sequence":observation.Sequence})
	})
	return mux
}
