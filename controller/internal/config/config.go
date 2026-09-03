package config

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"

	"github.com/anfa-research/predictive-autoscaler/internal/policy"
	"github.com/anfa-research/predictive-autoscaler/internal/safety"
)

type Runtime struct {
	ExperimentID  string `json:"experiment_id"`
	RunID         string `json:"run_id"`
	ControllerID  string `json:"controller_id"`
	TraceID       string `json:"trace_id"`
	Condition     string `json:"condition"`
	Namespace     string `json:"namespace"`
	Deployment    string `json:"deployment"`
	ForecastPath  string `json:"forecast_path"`
	PolicyPath    string `json:"policy_path"`
	T0UTC         string `json:"t0_utc"`
	HealthAddress string `json:"health_address"`
	SafetyEnabled bool   `json:"safety_enabled"`
	SafetyPolicyPath string `json:"safety_policy_path"`
}

func LoadSafetyPolicy(path string)(safety.Config,string,error){
	data,err:=os.ReadFile(path);if err!=nil{return safety.Config{},"",fmt.Errorf("read safety policy: %w",err)}
	var result safety.Config;if err:=json.Unmarshal(data,&result);err!=nil{return safety.Config{},"",fmt.Errorf("parse safety policy: %w",err)}
	if err:=result.Validate();err!=nil{return safety.Config{},"",err}
	return result,fmt.Sprintf("%x",sha256.Sum256(data)),nil
}

func LoadPolicy(path string) (policy.Config, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return policy.Config{}, "", fmt.Errorf("read policy config: %w", err)
	}
	var result policy.Config
	if err := json.Unmarshal(data, &result); err != nil {
		return policy.Config{}, "", fmt.Errorf("parse policy config: %w", err)
	}
	if err := result.Validate(); err != nil {
		return policy.Config{}, "", err
	}
	return result, fmt.Sprintf("%x", sha256.Sum256(data)), nil
}

func LoadRuntime(path string) (Runtime, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Runtime{}, fmt.Errorf("read runtime config: %w", err)
	}
	var result Runtime
	if err := json.Unmarshal(data, &result); err != nil {
		return Runtime{}, fmt.Errorf("parse runtime config: %w", err)
	}
	if result.ExperimentID == "" || result.RunID == "" || result.ControllerID == "" || result.TraceID == "" || result.Condition == "" || result.Namespace == "" || result.Deployment == "" || result.ForecastPath == "" || result.PolicyPath == "" || result.T0UTC == "" || result.HealthAddress == "" {
		return Runtime{}, fmt.Errorf("runtime configuration is incomplete")
	}
	if result.SafetyEnabled&&result.SafetyPolicyPath==""{return Runtime{},fmt.Errorf("safety_policy_path is required when safety is enabled")}
	return result, nil
}
