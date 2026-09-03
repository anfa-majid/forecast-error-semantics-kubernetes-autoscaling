package policy

import (
	"encoding/csv"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

func testConfig() Config {
	return Config{PolicyID: "anfa-empirical-replica-policy-v1", PolicyVersion: "1.0.0", CapacityLookup: []CapacityPoint{{1, 30}, {2, 40}, {3, 55}, {4, 65}}, ForecastHorizonSeconds: 6, DecisionIntervalSeconds: 1, MinReplicas: 1, MaxReplicas: 4, InitialReplicas: 1, SafetyFactor: 1, ScaleDownStabilizationSecs: 30, MaxScaleDownStep: 1}
}

func TestBoundaries(t *testing.T) {
	engine, _ := NewEngine(testConfig())
	cases := []struct {
		workload float64
		replicas int
	}{{0, 1}, {30, 1}, {30.000001, 2}, {40, 2}, {40.000001, 3}, {55, 3}, {55.000001, 4}, {65, 4}}
	for _, item := range cases {
		actual, _, err := engine.RawReplicas(item.workload)
		if err != nil || actual != item.replicas {
			t.Fatalf("workload=%f replicas=%d err=%v", item.workload, actual, err)
		}
	}
}

func TestMalformedWorkload(t *testing.T) {
	engine, _ := NewEngine(testConfig())
	for _, value := range []float64{-1, math.NaN(), math.Inf(1), 65.000001} {
		if _, _, err := engine.RawReplicas(value); err == nil {
			t.Fatalf("expected error for %v", value)
		}
	}
}

func TestImmediateScaleUpAndStabilizedScaleDown(t *testing.T) {
	engine, _ := NewEngine(testConfig())
	up, err := engine.Decide(60)
	if err != nil || up.CommandedReplicas != 4 || up.Action != "scale_up" {
		t.Fatalf("unexpected scale-up: %+v %v", up, err)
	}
	for index := 1; index <= 29; index++ {
		decision, _ := engine.Decide(25)
		if decision.CommandedReplicas != 4 {
			t.Fatalf("scaled down early at low decision %d", index)
		}
	}
	for expected := 3; expected >= 1; expected-- {
		decision, _ := engine.Decide(25)
		if decision.CommandedReplicas != expected {
			t.Fatalf("expected %d, got %+v", expected, decision)
		}
	}
}

func TestRepeatedSameDecision(t *testing.T) {
	engine, _ := NewEngine(testConfig())
	for index := 0; index < 10; index++ {
		decision, err := engine.Decide(25)
		if err != nil || decision.CommandedReplicas != 1 || decision.Action != "none" {
			t.Fatalf("unexpected decision: %+v %v", decision, err)
		}
	}
}

func TestGoldenVectors(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "testdata", "golden-policy-vectors.json"))
	if err != nil {
		t.Fatal(err)
	}
	var vectors struct {
		Capacity []struct {
			Workload float64 `json:"workload_rps"`
			Replicas int     `json:"raw_replicas"`
		} `json:"capacity_vectors"`
	}
	if err := json.Unmarshal(data, &vectors); err != nil {
		t.Fatal(err)
	}
	engine, _ := NewEngine(testConfig())
	for _, vector := range vectors.Capacity {
		actual, _, err := engine.RawReplicas(vector.Workload)
		if err != nil || actual != vector.Replicas {
			t.Fatalf("golden mismatch %+v actual=%d err=%v", vector, actual, err)
		}
	}
}

func TestAllStep8OracleTimelines(t *testing.T) {
	paths, err := filepath.Glob(filepath.Join("..", "..", "testdata", "oracle", "*.csv"))
	if err != nil || len(paths) != 5 {
		t.Fatalf("expected five oracle files, got %d err=%v", len(paths), err)
	}
	for _, path := range paths {
		file, err := os.Open(path)
		if err != nil {
			t.Fatal(err)
		}
		reader := csv.NewReader(file)
		header, err := reader.Read()
		if err != nil {
			t.Fatal(err)
		}
		columns := map[string]int{}
		for index, name := range header {
			columns[name] = index
		}
		engine, _ := NewEngine(testConfig())
		count := 0
		for {
			record, readErr := reader.Read()
			if readErr != nil {
				break
			}
			future, _ := strconv.ParseFloat(record[columns["true_future_workload_rps"]], 64)
			decision, err := engine.Decide(future)
			if err != nil {
				t.Fatal(err)
			}
			checks := map[string]int{"raw_replicas": decision.RawReplicas, "bounded_replicas": decision.BoundedReplicas, "stabilized_replicas": decision.StabilizedReplicas, "prior_commanded_replicas": decision.PriorCommandedReplicas, "commanded_replicas": decision.CommandedReplicas}
			for field, expected := range checks {
				actual, _ := strconv.Atoi(record[columns[field]])
				if actual != expected {
					t.Fatalf("%s row %d %s expected=%d actual=%d", path, count, field, expected, actual)
				}
			}
			if record[columns["action"]] != decision.Action {
				t.Fatalf("%s row %d action mismatch", path, count)
			}
			count++
		}
		_ = file.Close()
		if count == 0 {
			t.Fatalf("no rows in %s", path)
		}
	}
}
