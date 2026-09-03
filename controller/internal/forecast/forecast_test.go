package forecast

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestAllVersionedForecastFiles(t *testing.T) {
	paths, err := filepath.Glob(filepath.Join("..", "..", "testdata", "forecasts", "*.csv"))
	if err != nil || len(paths) != 5 {
		t.Fatalf("expected five forecast files, got %d (err=%v)", len(paths), err)
	}
	for _, path := range paths {
		name := filepath.Base(path)
		traceID := strings.TrimSuffix(name, ".oracle-forecast.csv")
		t.Run(traceID, func(t *testing.T) {
			trace, loadErr := LoadFile(path, Requirements{DecisionIntervalMS: 1000, HorizonMS: 6000, MaximumRPS: 65, ExpectedTraceID: traceID, ExpectedCondition: "oracle"})
			if loadErr != nil {
				t.Fatal(loadErr)
			}
			if len(trace.Rows) == 0 || trace.SHA256 == "" {
				t.Fatal("validated trace must contain rows and a digest")
			}
		})
	}
}

const header = "trace_id,condition,issued_offset_ms,target_offset_ms,horizon_ms,predicted_rps,mutation_id,pair_manifest_id\n"
const row0 = "trace,oracle,0,6000,6000,25,mutation,pair\n"
const row1 = "trace,oracle,1000,7000,6000,35,mutation,pair\n"

func requirements() Requirements {
	return Requirements{DecisionIntervalMS: 1000, HorizonMS: 6000, MaximumRPS: 65, ExpectedTraceID: "trace", ExpectedCondition: "oracle"}
}

func TestValidForecast(t *testing.T) {
	trace, err := Parse([]byte(header+row0+row1), requirements())
	if err != nil || len(trace.Rows) != 2 || trace.ByIssued[1000].PredictedRPS != 35 {
		t.Fatalf("trace=%+v err=%v", trace, err)
	}
}

func TestInvalidForecasts(t *testing.T) {
	cases := map[string]string{
		"missing column":  strings.Replace(header, "mutation_id,", "", 1) + row0,
		"duplicate row":   header + row0 + row0,
		"missing offset":  header + row1,
		"bad horizon":     header + strings.Replace(row0, ",6000,6000,", ",6001,6001,", 1),
		"bad target":      header + strings.Replace(row0, ",6000,6000,", ",7000,6000,", 1),
		"malformed":       header + strings.Replace(row0, ",25,", ",abc,", 1),
		"negative":        header + strings.Replace(row0, ",25,", ",-1,", 1),
		"nan":             header + strings.Replace(row0, ",25,", ",NaN,", 1),
		"above max":       header + strings.Replace(row0, ",25,", ",66,", 1),
		"wrong condition": header + strings.Replace(row0, ",oracle,", ",late,", 1),
		"empty identity":  header + strings.Replace(row0, ",mutation,", ",,", 1),
	}
	for name, data := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := Parse([]byte(data), requirements()); err == nil {
				t.Fatal("expected error")
			}
		})
	}
}
