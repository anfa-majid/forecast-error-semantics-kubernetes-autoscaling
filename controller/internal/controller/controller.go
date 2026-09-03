package controller

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sync"
	"time"

	"github.com/anfa-research/predictive-autoscaler/internal/arbiter"
	"github.com/anfa-research/predictive-autoscaler/internal/forecast"
	"github.com/anfa-research/predictive-autoscaler/internal/policy"
	"github.com/anfa-research/predictive-autoscaler/internal/safety"
)

type ScaleResult struct {
	Replicas        int
	ResourceVersion string
}

type ScaleClient interface {
	Current(ctx context.Context) (ScaleResult, error)
	Update(ctx context.Context, replicas int) (ScaleResult, error)
}

type ReadyClient interface { ReadyReplicas(ctx context.Context) (int,error) }

const (
	readyReadMaxAttempts = 3
	readyReadRetryDelay = 50 * time.Millisecond
)

type RunIdentity struct {
	ExperimentID string
	RunID        string
	ControllerID string
}

type Record struct {
	RecordType                string  `json:"record_type"`
	ExperimentID              string  `json:"experiment_id"`
	RunID                     string  `json:"run_id"`
	ControllerID              string  `json:"controller_id"`
	DecisionSequence          int     `json:"decision_seq"`
	TickOffsetMS              int64   `json:"tick_offset_ms"`
	TimestampUTC              string  `json:"timestamp_utc"`
	MonotonicElapsedNS        int64   `json:"monotonic_elapsed_ns"`
	TraceID                   string  `json:"trace_id"`
	Condition                 string  `json:"condition"`
	MutationID                string  `json:"mutation_id"`
	PairManifestID            string  `json:"pair_manifest_id"`
	ForecastIssuedOffsetMS    int64   `json:"forecast_issued_offset_ms"`
	ForecastTargetOffsetMS    int64   `json:"forecast_target_offset_ms"`
	HorizonMS                 int64   `json:"horizon_ms"`
	PredictedRPS              float64 `json:"predicted_rps"`
	SafetyAdjustedRPS         float64 `json:"safety_adjusted_rps"`
	RawReplicas               int     `json:"raw_replicas"`
	BoundedReplicas           int     `json:"bounded_replicas"`
	StabilizedReplicas        int     `json:"stabilized_replicas"`
	PriorCommandedReplicas    int     `json:"prior_commanded_replicas"`
	CommandedReplicas         int     `json:"commanded_replicas"`
	Action                    string  `json:"action"`
	ScaleDownHeld             bool    `json:"scale_down_held"`
	PolicyID                  string  `json:"policy_id"`
	PolicyConfigSHA256        string  `json:"policy_config_sha256"`
	ForecastSHA256            string  `json:"forecast_sha256"`
	APIRequestStartUTC        string  `json:"api_request_start_utc,omitempty"`
	APIResponseUTC            string  `json:"api_response_utc,omitempty"`
	APILatencyMS              float64 `json:"api_latency_ms,omitempty"`
	APIResult                 string  `json:"api_result"`
	DeploymentResourceVersion string  `json:"deployment_resource_version,omitempty"`
	ErrorClass                string  `json:"error_class,omitempty"`
	ErrorMessage              string  `json:"error_message,omitempty"`
	ArbitrationSource         string  `json:"arbitration_source,omitempty"`
	PredictiveCommandedReplicas int   `json:"predictive_commanded_replicas,omitempty"`
	SafetyFloorReplicas       int     `json:"safety_floor_replicas"`
	FinalCommandedReplicas    int     `json:"final_commanded_replicas"`
	FinalAction               string  `json:"final_action"`
	PriorFinalReplicas        int     `json:"prior_final_replicas"`
	SafetyPolicyID            string  `json:"safety_policy_id"`
	SafetyPolicySHA256        string  `json:"safety_policy_sha256"`
	SafetySequence            *int    `json:"safety_sequence,omitempty"`
	ObservationSequence       *int    `json:"observation_sequence,omitempty"`
	ObservationWindowStartMS  int64   `json:"observation_window_start_ms"`
	ObservationWindowEndMS    int64   `json:"observation_window_end_ms"`
	ObservedDemandRPS         float64 `json:"observed_demand_rps"`
	ReadyReplicas             int     `json:"ready_replicas"`
	ReadyCapacityRPS          float64 `json:"ready_capacity_rps"`
	SafetyOverload            bool    `json:"safety_overload"`
	ProtectionNeeded          bool    `json:"protection_needed"`
	ConsecutiveOverloadWindows int    `json:"consecutive_overload_windows"`
	SafetyTriggered           bool    `json:"safety_triggered"`
	SafetyEvent               string  `json:"safety_event"`
	SafetyActive              bool    `json:"safety_active"`
	InterventionChangesCommand bool   `json:"intervention_changes_command"`
	ReleaseHoldRemainingSeconds int   `json:"release_hold_remaining_seconds"`
}

type JSONLogger struct {
	mu      sync.Mutex
	encoder *json.Encoder
}

func NewJSONLogger(writer io.Writer) *JSONLogger {
	return &JSONLogger{encoder: json.NewEncoder(writer)}
}
func (l *JSONLogger) Write(record Record) error {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.encoder.Encode(record)
}

type Logger interface{ Write(Record) error }

type Controller struct {
	Identity     RunIdentity
	Policy       *policy.Engine
	PolicyConfig policy.Config
	PolicyHash   string
	Forecast     forecast.Trace
	Scaler       ScaleClient
	Logger       Logger
	StartTime    time.Time
	Now          func() time.Time
	Arbiter      *arbiter.Engine
	Safety       *safety.Engine
	SafetyHash   string
	Ready        ReadyClient
	scaleMu      sync.Mutex
	decisionMu   sync.Mutex
}

func (c *Controller) Validate() error {
	if c.Identity.ExperimentID == "" || c.Identity.RunID == "" || c.Identity.ControllerID == "" {
		return errors.New("run identity is incomplete")
	}
	if c.Policy == nil || c.Scaler == nil || c.Logger == nil || c.Now == nil {
		return errors.New("controller dependencies are incomplete")
	}
	if len(c.Forecast.Rows) == 0 || c.PolicyHash == "" || c.Forecast.SHA256 == "" {
		return errors.New("validated forecast and hashes are required")
	}
	if (c.Arbiter!=nil||c.Safety!=nil||c.Ready!=nil||c.SafetyHash!="") && (c.Arbiter==nil||c.Safety==nil||c.Ready==nil||c.SafetyHash=="") { return errors.New("all safety dependencies and safety hash must be configured together") }
	return nil
}

func (c *Controller) Preflight(ctx context.Context) error {
	current, err := c.Scaler.Current(ctx)
	if err != nil {
		return fmt.Errorf("read initial scale: %w", err)
	}
	if current.Replicas != c.PolicyConfig.InitialReplicas {
		return fmt.Errorf("initial Deployment replicas=%d, expected=%d", current.Replicas, c.PolicyConfig.InitialReplicas)
	}
	return nil
}

func (c *Controller) Tick(ctx context.Context, issuedOffsetMS int64) error {
	row, ok := c.Forecast.ByIssued[issuedOffsetMS]
	if !ok {
		record := c.baseRecord(issuedOffsetMS, forecast.Row{})
		record.APIResult, record.ErrorClass, record.ErrorMessage = "not_attempted", "missing_forecast", "required forecast row is missing"
		_ = c.Logger.Write(record)
		return errors.New("required forecast row is missing")
	}
	decision, err := c.Policy.Decide(row.PredictedRPS)
	if err != nil {
		record := c.baseRecord(issuedOffsetMS, row)
		record.APIResult, record.ErrorClass, record.ErrorMessage = "not_attempted", "policy_error", err.Error()
		_ = c.Logger.Write(record)
		return err
	}
	record := c.baseRecord(issuedOffsetMS, row)
	record.DecisionSequence = decision.DecisionSequence
	record.PredictedRPS = decision.InputWorkloadRPS
	record.SafetyAdjustedRPS = decision.SafetyAdjustedWorkloadRPS
	record.RawReplicas, record.BoundedReplicas, record.StabilizedReplicas = decision.RawReplicas, decision.BoundedReplicas, decision.StabilizedReplicas
	record.PriorCommandedReplicas, record.CommandedReplicas = decision.PriorCommandedReplicas, decision.CommandedReplicas
	record.Action, record.ScaleDownHeld = decision.Action, decision.ScaleDownHeld
	if c.Arbiter != nil {
		c.decisionMu.Lock();defer c.decisionMu.Unlock()
		arbitrated, arbitrationErr := c.Arbiter.UpdatePredictive(decision.CommandedReplicas)
		if arbitrationErr != nil { return arbitrationErr }
		record.ArbitrationSource=string(arbitrated.Source)
		record.PredictiveCommandedReplicas=decision.CommandedReplicas
		record.SafetyFloorReplicas=arbitrated.SafetyFloorReplicas
		record.PriorFinalReplicas=arbitrated.PriorFinalReplicas
		record.FinalCommandedReplicas=arbitrated.FinalReplicas
		record.FinalAction=arbitrated.Action
		return c.applyFinalDecision(ctx,record,arbitrated.Action,arbitrated.FinalReplicas)
	}
	if decision.Action == "none" {
		record.APIResult = "not_required"
		return c.Logger.Write(record)
	}
	requestStart := c.Now()
	record.APIRequestStartUTC = requestStart.UTC().Format(time.RFC3339Nano)
	result, updateErr := c.Scaler.Update(ctx, decision.CommandedReplicas)
	responseTime := c.Now()
	record.APIResponseUTC = responseTime.UTC().Format(time.RFC3339Nano)
	record.APILatencyMS = float64(responseTime.Sub(requestStart).Nanoseconds()) / 1e6
	if updateErr != nil {
		record.APIResult, record.ErrorClass, record.ErrorMessage = "error", "kubernetes_scale_error", updateErr.Error()
		_ = c.Logger.Write(record)
		return fmt.Errorf("update Deployment scale: %w", updateErr)
	}
	record.APIResult, record.DeploymentResourceVersion = "success", result.ResourceVersion
	if result.Replicas != decision.CommandedReplicas {
		record.APIResult, record.ErrorClass, record.ErrorMessage = "error", "scale_ack_mismatch", fmt.Sprintf("API returned replicas=%d", result.Replicas)
		_ = c.Logger.Write(record)
		return errors.New(record.ErrorMessage)
	}
	return c.Logger.Write(record)
}

func (c *Controller) applyFinalDecision(ctx context.Context,record Record,action string,replicas int) error {
	if action=="none"{record.APIResult="not_required";return c.Logger.Write(record)}
	c.scaleMu.Lock();defer c.scaleMu.Unlock()
	requestStart:=c.Now();record.APIRequestStartUTC=requestStart.UTC().Format(time.RFC3339Nano)
	result,updateErr:=c.Scaler.Update(ctx,replicas);responseTime:=c.Now()
	record.APIResponseUTC=responseTime.UTC().Format(time.RFC3339Nano);record.APILatencyMS=float64(responseTime.Sub(requestStart).Nanoseconds())/1e6
	if updateErr!=nil{record.APIResult,record.ErrorClass,record.ErrorMessage="error","kubernetes_scale_error",updateErr.Error();_ = c.Logger.Write(record);return fmt.Errorf("update Deployment scale: %w",updateErr)}
	record.APIResult,record.DeploymentResourceVersion="success",result.ResourceVersion
	if result.Replicas!=replicas{record.APIResult,record.ErrorClass,record.ErrorMessage="error","scale_ack_mismatch",fmt.Sprintf("API returned replicas=%d",result.Replicas);_ = c.Logger.Write(record);return errors.New(record.ErrorMessage)}
	return c.Logger.Write(record)
}

func (c *Controller) SafetyTick(ctx context.Context,observation safety.Observation) error {
	if c.Arbiter==nil||c.Safety==nil||c.Ready==nil{return errors.New("safety dependencies are incomplete")}
	c.decisionMu.Lock();defer c.decisionMu.Unlock()
	readyReplicas,err:=c.readReadyReplicas(ctx);if err!=nil{return err}
	predictive,_,_:=c.Arbiter.Snapshot()
	safetyDecision,err:=c.Safety.Evaluate(observation,readyReplicas,predictive);if err!=nil{return err}
	arbitrated,err:=c.Arbiter.UpdateSafetyFloor(safetyDecision.SafetyFloorReplicas);if err!=nil{return err}
	record:=c.baseRecord(observation.WindowEndMS,forecast.Row{})
	record.RecordType="safety_decision";record.ArbitrationSource=string(arbitrated.Source)
	record.SafetyPolicyID=c.Safety.PolicyID();record.SafetyPolicySHA256=c.SafetyHash;record.SafetySequence=&safetyDecision.Sequence
	record.ObservationSequence=&observation.Sequence;record.ObservationWindowStartMS=observation.WindowStartMS;record.ObservationWindowEndMS=observation.WindowEndMS
	record.ObservedDemandRPS=safetyDecision.ObservedDemandRPS;record.ReadyReplicas=safetyDecision.ReadyReplicas;record.ReadyCapacityRPS=safetyDecision.ReadyCapacityRPS
	record.SafetyOverload=safetyDecision.Overload;record.ProtectionNeeded=safetyDecision.ProtectionNeeded;record.ConsecutiveOverloadWindows=safetyDecision.ConsecutiveOverloadWindows
	record.SafetyTriggered=safetyDecision.Triggered;record.SafetyEvent=safetyDecision.Event;record.SafetyActive=safetyDecision.Active
	record.PredictiveCommandedReplicas=arbitrated.PredictiveReplicas;record.SafetyFloorReplicas=arbitrated.SafetyFloorReplicas
	record.PriorFinalReplicas=arbitrated.PriorFinalReplicas;record.FinalCommandedReplicas=arbitrated.FinalReplicas
	record.FinalAction=arbitrated.Action
	record.InterventionChangesCommand=arbitrated.SafetyChangesCommand;record.ReleaseHoldRemainingSeconds=safetyDecision.ReleaseHoldRemainingSeconds
	return c.applyFinalDecision(ctx,record,arbitrated.Action,arbitrated.FinalReplicas)
}

func (c *Controller) readReadyReplicas(ctx context.Context) (int, error) {
	var lastErr error
	for attempt := 1; attempt <= readyReadMaxAttempts; attempt++ {
		readyReplicas, err := c.Ready.ReadyReplicas(ctx)
		if err == nil {
			return readyReplicas, nil
		}
		lastErr = err
		if attempt == readyReadMaxAttempts {
			break
		}
		timer := time.NewTimer(readyReadRetryDelay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return 0, fmt.Errorf("read Ready replicas: %w", ctx.Err())
		case <-timer.C:
		}
	}
	return 0, fmt.Errorf("read Ready replicas after %d attempts: %w", readyReadMaxAttempts, lastErr)
}

func (c *Controller) Run(ctx context.Context, t0 time.Time) error {
	if err := c.Validate(); err != nil {
		return err
	}
	if err := c.Preflight(ctx); err != nil {
		return err
	}
	return c.RunAfterPreflight(ctx, t0)
}

func (c *Controller) RunAfterPreflight(ctx context.Context, t0 time.Time) error {
	c.StartTime = c.Now()
	for _, row := range c.Forecast.Rows {
		scheduled := t0.Add(time.Duration(row.IssuedOffsetMS) * time.Millisecond)
		if wait := time.Until(scheduled); wait > 0 {
			timer := time.NewTimer(wait)
			select {
			case <-ctx.Done():
				timer.Stop()
				return ctx.Err()
			case <-timer.C:
			}
		}
		if err := c.Tick(ctx, row.IssuedOffsetMS); err != nil {
			return err
		}
	}
	return nil
}

func (c *Controller) baseRecord(offset int64, row forecast.Row) Record {
	now := c.Now()
	elapsed := int64(0)
	if !c.StartTime.IsZero() {
		elapsed = now.Sub(c.StartTime).Nanoseconds()
	}
	return Record{
		RecordType: "decision", ExperimentID: c.Identity.ExperimentID, RunID: c.Identity.RunID, ControllerID: c.Identity.ControllerID,
		TickOffsetMS: offset, TimestampUTC: now.UTC().Format(time.RFC3339Nano), MonotonicElapsedNS: elapsed,
		TraceID: row.TraceID, Condition: row.Condition, MutationID: row.MutationID, PairManifestID: row.PairManifestID,
		ForecastIssuedOffsetMS: row.IssuedOffsetMS, ForecastTargetOffsetMS: row.TargetOffsetMS, HorizonMS: row.HorizonMS,
		PolicyID: c.PolicyConfig.PolicyID, PolicyConfigSHA256: c.PolicyHash, ForecastSHA256: c.Forecast.SHA256,
	}
}
