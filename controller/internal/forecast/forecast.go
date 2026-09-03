package forecast

import (
	"bytes"
	"crypto/sha256"
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
)

var requiredColumns = []string{"trace_id", "condition", "issued_offset_ms", "target_offset_ms", "horizon_ms", "predicted_rps", "mutation_id", "pair_manifest_id"}

type Row struct {
	TraceID        string
	Condition      string
	IssuedOffsetMS int64
	TargetOffsetMS int64
	HorizonMS      int64
	PredictedRPS   float64
	MutationID     string
	PairManifestID string
}

type Trace struct {
	Rows      []Row
	ByIssued  map[int64]Row
	SHA256    string
	TraceID   string
	Condition string
}

type Requirements struct {
	DecisionIntervalMS int64
	HorizonMS          int64
	MaximumRPS         float64
	ExpectedTraceID    string
	ExpectedCondition  string
}

func LoadFile(path string, requirements Requirements) (Trace, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Trace{}, fmt.Errorf("read forecast: %w", err)
	}
	trace, err := Parse(data, requirements)
	if err != nil {
		return Trace{}, err
	}
	trace.SHA256 = fmt.Sprintf("%x", sha256.Sum256(data))
	return trace, nil
}

func Parse(data []byte, requirements Requirements) (Trace, error) {
	if requirements.DecisionIntervalMS <= 0 || requirements.HorizonMS <= 0 || requirements.MaximumRPS <= 0 {
		return Trace{}, errors.New("invalid forecast requirements")
	}
	reader := csv.NewReader(bytes.NewReader(data))
	header, err := reader.Read()
	if err != nil {
		return Trace{}, fmt.Errorf("read header: %w", err)
	}
	indices := map[string]int{}
	for index, name := range header {
		if _, duplicate := indices[name]; duplicate {
			return Trace{}, fmt.Errorf("duplicate column %q", name)
		}
		indices[name] = index
	}
	for _, required := range requiredColumns {
		if _, ok := indices[required]; !ok {
			return Trace{}, fmt.Errorf("missing required column %q", required)
		}
	}
	result := Trace{ByIssued: map[int64]Row{}}
	rowNumber := 1
	for {
		record, readErr := reader.Read()
		if readErr == io.EOF {
			break
		}
		rowNumber++
		if readErr != nil {
			return Trace{}, fmt.Errorf("row %d: %w", rowNumber, readErr)
		}
		get := func(name string) string { return record[indices[name]] }
		issued, parseErr := strconv.ParseInt(get("issued_offset_ms"), 10, 64)
		if parseErr != nil {
			return Trace{}, fmt.Errorf("row %d: malformed issued_offset_ms", rowNumber)
		}
		target, parseErr := strconv.ParseInt(get("target_offset_ms"), 10, 64)
		if parseErr != nil {
			return Trace{}, fmt.Errorf("row %d: malformed target_offset_ms", rowNumber)
		}
		horizon, parseErr := strconv.ParseInt(get("horizon_ms"), 10, 64)
		if parseErr != nil {
			return Trace{}, fmt.Errorf("row %d: malformed horizon_ms", rowNumber)
		}
		predicted, parseErr := strconv.ParseFloat(get("predicted_rps"), 64)
		if parseErr != nil || predicted < 0 || math.IsNaN(predicted) || math.IsInf(predicted, 0) {
			return Trace{}, fmt.Errorf("row %d: predicted_rps must be finite and nonnegative", rowNumber)
		}
		row := Row{TraceID: get("trace_id"), Condition: get("condition"), IssuedOffsetMS: issued, TargetOffsetMS: target, HorizonMS: horizon, PredictedRPS: predicted, MutationID: get("mutation_id"), PairManifestID: get("pair_manifest_id")}
		if row.TraceID == "" || row.Condition == "" || row.MutationID == "" || row.PairManifestID == "" {
			return Trace{}, fmt.Errorf("row %d: identity fields cannot be empty", rowNumber)
		}
		if row.TraceID != requirements.ExpectedTraceID || row.Condition != requirements.ExpectedCondition {
			return Trace{}, fmt.Errorf("row %d: unexpected trace or condition", rowNumber)
		}
		if issued < 0 || issued%requirements.DecisionIntervalMS != 0 || horizon != requirements.HorizonMS || target != issued+horizon {
			return Trace{}, fmt.Errorf("row %d: invalid forecast time contract", rowNumber)
		}
		if predicted > requirements.MaximumRPS+1e-9 {
			return Trace{}, fmt.Errorf("row %d: forecast exceeds validated capacity", rowNumber)
		}
		if _, duplicate := result.ByIssued[issued]; duplicate {
			return Trace{}, fmt.Errorf("row %d: duplicate issued_offset_ms", rowNumber)
		}
		expectedIssued := int64(len(result.Rows)) * requirements.DecisionIntervalMS
		if issued != expectedIssued {
			return Trace{}, fmt.Errorf("row %d: missing or unordered decision offset; expected %d", rowNumber, expectedIssued)
		}
		result.Rows = append(result.Rows, row)
		result.ByIssued[issued] = row
	}
	if len(result.Rows) == 0 {
		return Trace{}, errors.New("forecast contains no rows")
	}
	result.TraceID, result.Condition = result.Rows[0].TraceID, result.Rows[0].Condition
	return result, nil
}
