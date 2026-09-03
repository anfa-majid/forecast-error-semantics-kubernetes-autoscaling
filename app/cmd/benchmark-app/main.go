package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

var version = "dev"
var commit = "unknown"

type config struct {
	Addr             string
	Iterations       int
	Seed             string
	ReadyDelay       time.Duration
	DrainDelay       time.Duration
	ShutdownTimeout  time.Duration
	RequestLogSample uint64
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
func loadConfig() (config, error) {
	c := config{Addr: env("LISTEN_ADDR", ":8080"), Seed: env("WORK_SEED", "anfa-benchmark-v1")}
	var err error
	if c.Iterations, err = strconv.Atoi(env("WORK_ITERATIONS", "50000")); err != nil || c.Iterations < 1 {
		return c, fmt.Errorf("WORK_ITERATIONS must be a positive integer")
	}
	if c.ReadyDelay, err = time.ParseDuration(env("READY_DELAY", "0s")); err != nil || c.ReadyDelay < 0 {
		return c, fmt.Errorf("READY_DELAY must be a non-negative duration")
	}
	if c.DrainDelay, err = time.ParseDuration(env("DRAIN_DELAY", "2s")); err != nil || c.DrainDelay < 0 {
		return c, fmt.Errorf("DRAIN_DELAY must be a non-negative duration")
	}
	if c.ShutdownTimeout, err = time.ParseDuration(env("SHUTDOWN_TIMEOUT", "20s")); err != nil || c.ShutdownTimeout <= 0 {
		return c, fmt.Errorf("SHUTDOWN_TIMEOUT must be a positive duration")
	}
	if c.RequestLogSample, err = strconv.ParseUint(env("REQUEST_LOG_SAMPLE_EVERY", "0"), 10, 64); err != nil {
		return c, fmt.Errorf("REQUEST_LOG_SAMPLE_EVERY must be a non-negative integer")
	}
	if strings.TrimSpace(c.Seed) == "" {
		return c, fmt.Errorf("WORK_SEED must not be empty")
	}
	return c, nil
}

type metrics struct {
	mu              sync.Mutex
	completed       map[string]uint64
	durationBuckets []float64
	durationCounts  []uint64
	durationSum     float64
	httpCounts      map[string][]uint64
	httpSums        map[string]float64
	httpTotals      map[string]uint64
	workStarted     atomic.Uint64
	active          atomic.Int64
	ready           atomic.Bool
	accepting       atomic.Bool
	started         float64
}

func newMetrics() *metrics {
	buckets := []float64{.001, .0025, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10}
	return &metrics{completed: map[string]uint64{}, durationBuckets: buckets, durationCounts: make([]uint64, len(buckets)), httpCounts: map[string][]uint64{}, httpSums: map[string]float64{}, httpTotals: map[string]uint64{}, started: float64(time.Now().UnixNano()) / 1e9}
}
func (m *metrics) completeWork(status int) {
	s := strconv.Itoa(status)
	m.mu.Lock()
	defer m.mu.Unlock()
	m.completed[s]++
}
func (m *metrics) observeWorkDuration(d time.Duration) {
	seconds := d.Seconds()
	m.mu.Lock()
	defer m.mu.Unlock()
	m.durationSum += seconds
	for i, b := range m.durationBuckets {
		if seconds <= b {
			m.durationCounts[i]++
		}
	}
}
func metricRoute(path string) string {
	switch path {
	case "/work", "/livez", "/readyz", "/metrics":
		return path
	default:
		return "other"
	}
}
func (m *metrics) observeHTTP(route string, status int, d time.Duration) {
	key := route + "|" + strconv.Itoa(status)
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.httpCounts[key]; !ok {
		m.httpCounts[key] = make([]uint64, len(m.durationBuckets))
	}
	seconds := d.Seconds()
	for i, b := range m.durationBuckets {
		if seconds <= b {
			m.httpCounts[key][i]++
		}
	}
	m.httpSums[key] += seconds
	m.httpTotals[key]++
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(status int) {
	w.status = status
	w.ResponseWriter.WriteHeader(status)
}
func (m *metrics) instrument(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(sw, r)
		m.observeHTTP(metricRoute(r.URL.Path), sw.status, time.Since(start))
	})
}
func (m *metrics) serve(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
	m.mu.Lock()
	defer m.mu.Unlock()
	fmt.Fprintln(w, "# HELP benchmark_work_requests_total Work requests received.")
	fmt.Fprintln(w, "# TYPE benchmark_work_requests_total counter")
	fmt.Fprintf(w, "benchmark_work_requests_total %d\n", m.workStarted.Load())
	fmt.Fprintln(w, "# HELP benchmark_work_completed_total Completed work requests by response status code.")
	fmt.Fprintln(w, "# TYPE benchmark_work_completed_total counter")
	for status, n := range m.completed {
		fmt.Fprintf(w, "benchmark_work_completed_total{code=%q} %d\n", status, n)
	}
	fmt.Fprintln(w, "# HELP benchmark_work_active_requests Current in-flight work requests.")
	fmt.Fprintln(w, "# TYPE benchmark_work_active_requests gauge")
	fmt.Fprintf(w, "benchmark_work_active_requests %d\n", m.active.Load())
	fmt.Fprintln(w, "# HELP benchmark_work_duration_seconds CPU-work request duration.")
	fmt.Fprintln(w, "# TYPE benchmark_work_duration_seconds histogram")
	for i, b := range m.durationBuckets {
		fmt.Fprintf(w, "benchmark_work_duration_seconds_bucket{le=%q} %d\n", strconv.FormatFloat(b, 'g', -1, 64), m.durationCounts[i])
	}
	fmt.Fprintf(w, "benchmark_work_duration_seconds_bucket{le=\"+Inf\"} %d\nbenchmark_work_duration_seconds_sum %g\nbenchmark_work_duration_seconds_count %d\n", m.completed["200"], m.durationSum, m.completed["200"])
	fmt.Fprintln(w, "# HELP benchmark_http_request_duration_seconds End-to-end HTTP handler duration by bounded route and status code.")
	fmt.Fprintln(w, "# TYPE benchmark_http_request_duration_seconds histogram")
	for key, counts := range m.httpCounts {
		parts := strings.SplitN(key, "|", 2)
		for i, b := range m.durationBuckets {
			fmt.Fprintf(w, "benchmark_http_request_duration_seconds_bucket{route=%q,code=%q,le=%q} %d\n", parts[0], parts[1], strconv.FormatFloat(b, 'g', -1, 64), counts[i])
		}
		fmt.Fprintf(w, "benchmark_http_request_duration_seconds_bucket{route=%q,code=%q,le=\"+Inf\"} %d\nbenchmark_http_request_duration_seconds_sum{route=%q,code=%q} %g\nbenchmark_http_request_duration_seconds_count{route=%q,code=%q} %d\n", parts[0], parts[1], m.httpTotals[key], parts[0], parts[1], m.httpSums[key], parts[0], parts[1], m.httpTotals[key])
	}
	r := 0
	if m.ready.Load() {
		r = 1
	}
	fmt.Fprintf(w, "# HELP benchmark_ready Whether the application accepts measured traffic.\n# TYPE benchmark_ready gauge\nbenchmark_ready %d\n", r)
	fmt.Fprintf(w, "# HELP benchmark_start_time_seconds Process start time.\n# TYPE benchmark_start_time_seconds gauge\nbenchmark_start_time_seconds %g\n", m.started)
	fmt.Fprintf(w, "# HELP benchmark_build_info Build identity.\n# TYPE benchmark_build_info gauge\nbenchmark_build_info{version=%q,commit=%q} 1\n", version, commit)
}

type app struct {
	cfg             config
	metrics         *metrics
	logger          *slog.Logger
	podName, podUID string
	readyAt         time.Time
	seq             atomic.Uint64
}

func newApp(c config, logger *slog.Logger) *app {
	return &app{cfg: c, metrics: newMetrics(), logger: logger, podName: env("POD_NAME", env("HOSTNAME", "local")), podUID: env("POD_UID", "local")}
}
func (a *app) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /livez", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(200); _, _ = w.Write([]byte("ok\n")) })
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		if !a.metrics.ready.Load() {
			http.Error(w, "not ready", 503)
			return
		}
		w.WriteHeader(200)
		_, _ = w.Write([]byte("ready\n"))
	})
	mux.HandleFunc("GET /work", a.work)
	mux.HandleFunc("GET /metrics", a.metrics.serve)
	return a.metrics.instrument(mux)
}
func hashWork(seed string, iterations int) [32]byte {
	sum := sha256.Sum256([]byte(seed))
	for i := 1; i < iterations; i++ {
		sum = sha256.Sum256(sum[:])
	}
	return sum
}
func (a *app) work(w http.ResponseWriter, r *http.Request) {
	a.metrics.workStarted.Add(1)
	if !a.metrics.accepting.Load() {
		http.Error(w, "not ready", 503)
		a.metrics.completeWork(503)
		return
	}
	a.metrics.active.Add(1)
	defer a.metrics.active.Add(-1)
	start := time.Now()
	sum := hashWork(a.cfg.Seed, a.cfg.Iterations)
	d := time.Since(start)
	a.metrics.observeWorkDuration(d)
	a.metrics.completeWork(200)
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Benchmark-Pod", a.podName)
	w.Header().Set("X-Benchmark-Pod-UID", a.podUID)
	w.Header().Set("X-Benchmark-Version", version)
	w.Header().Set("X-Benchmark-Ready-At", a.readyAt.UTC().Format(time.RFC3339Nano))
	_ = json.NewEncoder(w).Encode(map[string]any{"digest": hex.EncodeToString(sum[:]), "iterations": a.cfg.Iterations, "pod": a.podName, "duration_ns": d.Nanoseconds()})
	if n := a.cfg.RequestLogSample; n > 0 && a.seq.Add(1)%n == 0 {
		a.logger.Info("request_completed", "path", r.URL.Path, "status", 200, "duration_ns", d.Nanoseconds(), "sample_every", n)
	}
}

func run(ctx context.Context, c config, logger *slog.Logger) error {
	a := newApp(c, logger)
	server := &http.Server{Addr: c.Addr, Handler: a.routes(), ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 60 * time.Second}
	listener, err := net.Listen("tcp", c.Addr)
	if err != nil {
		return err
	}
	errCh := make(chan error, 1)
	go func() {
		logger.Info("server_starting", "addr", listener.Addr().String(), "version", version, "commit", commit, "iterations", c.Iterations)
		errCh <- server.Serve(listener)
	}()
	timer := time.NewTimer(c.ReadyDelay)
	defer timer.Stop()
	select {
	case <-timer.C:
		a.readyAt = time.Now()
		a.metrics.ready.Store(true)
		a.metrics.accepting.Store(true)
		logger.Info("readiness_changed", "ready", true, "ready_at", a.readyAt.UTC())
	case err := <-errCh:
		return err
	case <-ctx.Done():
	}
	select {
	case err := <-errCh:
		return err
	case <-ctx.Done():
	}
	a.metrics.ready.Store(false)
	logger.Info("readiness_changed", "ready", false)
	if c.DrainDelay > 0 {
		logger.Info("drain_delay_started", "duration", c.DrainDelay)
		time.Sleep(c.DrainDelay)
	}
	a.metrics.accepting.Store(false)
	shutdownCtx, cancel := context.WithTimeout(context.Background(), c.ShutdownTimeout)
	defer cancel()
	err = server.Shutdown(shutdownCtx)
	if err != nil {
		_ = server.Close()
		return err
	}
	logger.Info("shutdown_complete")
	return nil
}
func main() {
	flag.Parse()
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	c, err := loadConfig()
	if err != nil {
		logger.Error("invalid_configuration", "error", err)
		os.Exit(2)
	}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	if err = run(ctx, c, logger); err != nil && !errors.Is(err, http.ErrServerClosed) {
		logger.Error("server_failed", "error", err)
		os.Exit(1)
	}
}
