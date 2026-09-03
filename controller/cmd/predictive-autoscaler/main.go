package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/anfa-research/predictive-autoscaler/internal/arbiter"
	"github.com/anfa-research/predictive-autoscaler/internal/config"
	"github.com/anfa-research/predictive-autoscaler/internal/controller"
	"github.com/anfa-research/predictive-autoscaler/internal/forecast"
	"github.com/anfa-research/predictive-autoscaler/internal/kube"
	"github.com/anfa-research/predictive-autoscaler/internal/policy"
	"github.com/anfa-research/predictive-autoscaler/internal/safety"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

var version = "dev"
var commit = "unknown"

func main() {
	os.Exit(run())
}

func run() int {
	runtimePath := flag.String("runtime-config", "/etc/anfa/runtime/runtime-config.json", "runtime configuration file")
	kubeconfig := flag.String("kubeconfig", "", "optional kubeconfig for development only")
	flag.Parse()

	runtimeConfig, err := config.LoadRuntime(*runtimePath)
	if err != nil {
		return fatal("runtime_config", err)
	}
	policyConfig, policyHash, err := config.LoadPolicy(runtimeConfig.PolicyPath)
	if err != nil {
		return fatal("policy_config", err)
	}
	trace, err := forecast.LoadFile(runtimeConfig.ForecastPath, forecast.Requirements{
		DecisionIntervalMS: int64(policyConfig.DecisionIntervalSeconds * 1000), HorizonMS: int64(policyConfig.ForecastHorizonSeconds * 1000),
		MaximumRPS:      policyConfig.CapacityLookup[len(policyConfig.CapacityLookup)-1].RPS,
		ExpectedTraceID: runtimeConfig.TraceID, ExpectedCondition: runtimeConfig.Condition,
	})
	if err != nil {
		return fatal("forecast_validation", err)
	}
	engine, err := policy.NewEngine(policyConfig)
	if err != nil {
		return fatal("policy_engine", err)
	}
	t0, err := time.Parse(time.RFC3339Nano, runtimeConfig.T0UTC)
	if err != nil {
		return fatal("t0", err)
	}
	if !t0.After(time.Now()) {
		return fatal("t0", fmt.Errorf("t0 must be in the future"))
	}

	restConfig, err := kubernetesConfig(*kubeconfig)
	if err != nil {
		return fatal("kubernetes_config", err)
	}
	client, err := kubernetes.NewForConfig(restConfig)
	if err != nil {
		return fatal("kubernetes_client", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	logger := controller.NewJSONLogger(os.Stdout)
	scaler:=kube.DeploymentScaler{Client: client, Namespace: runtimeConfig.Namespace, DeploymentName: runtimeConfig.Deployment}
	ctl := &controller.Controller{
		Identity: controller.RunIdentity{ExperimentID: runtimeConfig.ExperimentID, RunID: runtimeConfig.RunID, ControllerID: runtimeConfig.ControllerID},
		Policy:   engine, PolicyConfig: policyConfig, PolicyHash: policyHash, Forecast: trace,
		Scaler: scaler,
		Logger: logger, Now: time.Now,
	}
	var observationHandler http.Handler
	var safetyPolicyHash string
	if runtimeConfig.SafetyEnabled {
		safetyConfig,loadedHash,loadErr:=config.LoadSafetyPolicy(runtimeConfig.SafetyPolicyPath);if loadErr!=nil{return fatal("safety_policy_config",loadErr)}
		safetyPolicyHash=loadedHash
		safetyEngine,safetyErr:=safety.NewEngine(safetyConfig);if safetyErr!=nil{return fatal("safety_engine",safetyErr)}
		arbiterEngine,arbiterErr:=arbiter.New(policyConfig.MinReplicas,policyConfig.MaxReplicas,policyConfig.InitialReplicas);if arbiterErr!=nil{return fatal("arbiter_engine",arbiterErr)}
		observationStore,storeErr:=safety.NewObservationStore(runtimeConfig.RunID,safetyConfig.ObservationIntervalSecs);if storeErr!=nil{return fatal("observation_store",storeErr)}
		ctl.Arbiter,ctl.Safety,ctl.Ready,ctl.SafetyHash=arbiterEngine,safetyEngine,scaler,loadedHash
		observationStore.SetOnAccepted(func(observation safety.Observation)error{return ctl.SafetyTick(ctx,observation)})
		observationHandler=observationStore.Handler()
	}
	if err := ctl.Validate(); err != nil {
		return fatal("controller_validation", err)
	}
	if err := ctl.Preflight(ctx); err != nil {
		return fatal("controller_preflight", err)
	}

	var ready atomic.Bool
	server := healthServer(runtimeConfig.HealthAddress, &ready,observationHandler)
	go func() {
		if serveErr := server.ListenAndServe(); serveErr != nil && serveErr != http.ErrServerClosed {
			fmt.Fprintf(os.Stderr, "health server: %v\n", serveErr)
			stop()
		}
	}()
	ready.Store(true)
	fmt.Fprintf(os.Stderr, "predictive-autoscaler version=%s commit=%s policy=%s trace=%s condition=%s safety_enabled=%t safety_policy_sha256=%s\n", version, commit, policyConfig.PolicyID, trace.TraceID, trace.Condition,runtimeConfig.SafetyEnabled,safetyPolicyHash)
	err = ctl.RunAfterPreflight(ctx, t0)
	ready.Store(false)
	if err == nil {
		fmt.Fprintln(os.Stderr, "controller_run_complete=true; waiting for termination signal")
		<-ctx.Done()
	}
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	_ = server.Shutdown(shutdownCtx)
	if err != nil && !errors.Is(err, context.Canceled) {
		return fatal("controller_run", err)
	}
	return 0
}

func kubernetesConfig(kubeconfig string) (*rest.Config, error) {
	if kubeconfig != "" {
		return clientcmd.BuildConfigFromFlags("", kubeconfig)
	}
	return rest.InClusterConfig()
}

func healthServer(address string, ready *atomic.Bool,observationHandler http.Handler) *http.Server {
	mux := http.NewServeMux()
	mux.HandleFunc("/livez", func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusOK)
		_, _ = writer.Write([]byte("ok\n"))
	})
	mux.HandleFunc("/readyz", func(writer http.ResponseWriter, _ *http.Request) {
		if !ready.Load() {
			http.Error(writer, "not ready", http.StatusServiceUnavailable)
			return
		}
		writer.WriteHeader(http.StatusOK)
		_, _ = writer.Write([]byte("ready\n"))
	})
	if observationHandler!=nil{mux.Handle("/v1/safety/observations",observationHandler)}
	return &http.Server{Addr: address, Handler: mux, ReadHeaderTimeout: 2 * time.Second, ReadTimeout: 3 * time.Second, WriteTimeout: 3 * time.Second, IdleTimeout: 10 * time.Second}
}

func fatal(class string, err error) int {
	fmt.Fprintf(os.Stderr, "fatal class=%s error=%q\n", class, err.Error())
	return 1
}
