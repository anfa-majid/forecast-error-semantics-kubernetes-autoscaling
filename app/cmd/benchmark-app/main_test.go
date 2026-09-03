package main

import (
	"bytes"
	"context"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func testApp() *app {
	a := newApp(config{Iterations: 10, Seed: "fixed"}, slog.New(slog.NewTextHandler(&bytes.Buffer{}, nil)))
	a.readyAt = time.Unix(1, 0)
	return a
}
func TestHashWorkDeterministic(t *testing.T) {
	if hashWork("x", 10) != hashWork("x", 10) {
		t.Fatal("work is not deterministic")
	}
	if hashWork("x", 10) == hashWork("x", 11) {
		t.Fatal("iterations do not affect result")
	}
}
func TestReadinessAndWork(t *testing.T) {
	a := testApp()
	h := a.routes()
	r := httptest.NewRequest("GET", "/readyz", nil)
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != 503 {
		t.Fatalf("got %d", w.Code)
	}
	a.metrics.ready.Store(true)
	a.metrics.accepting.Store(true)
	w = httptest.NewRecorder()
	h.ServeHTTP(w, httptest.NewRequest("GET", "/work", nil))
	if w.Code != 200 {
		t.Fatalf("got %d", w.Code)
	}
	if w.Header().Get("X-Benchmark-Pod") == "" {
		t.Fatal("missing pod header")
	}
}
func TestLivenessIndependentOfReadiness(t *testing.T) {
	a := testApp()
	w := httptest.NewRecorder()
	a.routes().ServeHTTP(w, httptest.NewRequest("GET", "/livez", nil))
	if w.Code != 200 {
		t.Fatalf("got %d", w.Code)
	}
}
func TestMetrics(t *testing.T) {
	a := testApp()
	a.metrics.ready.Store(true)
	a.metrics.accepting.Store(true)
	a.routes().ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("GET", "/work", nil))
	w := httptest.NewRecorder()
	a.metrics.serve(w, httptest.NewRequest("GET", "/metrics", nil))
	for _, want := range []string{"benchmark_work_requests_total 1", "benchmark_work_completed_total{code=\"200\"} 1", "benchmark_work_duration_seconds_count 1", "benchmark_http_request_duration_seconds_count{route=\"/work\",code=\"200\"} 1", "benchmark_ready 1"} {
		if !strings.Contains(w.Body.String(), want) {
			t.Errorf("missing %q", want)
		}
	}
}
func TestConfigValidation(t *testing.T) {
	tests := []struct{ name, key, value string }{
		{"iterations", "WORK_ITERATIONS", "0"}, {"iterations text", "WORK_ITERATIONS", "many"},
		{"ready delay", "READY_DELAY", "-1s"}, {"drain delay", "DRAIN_DELAY", "-1s"}, {"shutdown", "SHUTDOWN_TIMEOUT", "0s"},
		{"sample", "REQUEST_LOG_SAMPLE_EVERY", "invalid"}, {"seed", "WORK_SEED", " "},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv(tc.key, tc.value)
			if _, err := loadConfig(); err == nil {
				t.Fatalf("expected %s=%q to fail", tc.key, tc.value)
			}
		})
	}
}
func TestConfigDefaults(t *testing.T) {
	for _, key := range []string{"LISTEN_ADDR", "WORK_ITERATIONS", "WORK_SEED", "READY_DELAY", "DRAIN_DELAY", "SHUTDOWN_TIMEOUT", "REQUEST_LOG_SAMPLE_EVERY"} {
		t.Setenv(key, "")
	}
	c, err := loadConfig()
	if err != nil {
		t.Fatal(err)
	}
	if c.Iterations != 50000 || c.Seed != "anfa-benchmark-v1" || c.Addr != ":8080" || c.DrainDelay != 2*time.Second {
		t.Fatalf("unexpected defaults: %+v", c)
	}
}
func TestRunGracefulShutdown(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	c := config{Addr: "127.0.0.1:0", Iterations: 1, Seed: "x", ShutdownTimeout: time.Second}
	done := make(chan error, 1)
	go func() { done <- run(ctx, c, slog.New(slog.NewTextHandler(&bytes.Buffer{}, nil))) }()
	time.Sleep(20 * time.Millisecond)
	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("shutdown timed out")
	}
}

var _ http.Handler = (*http.ServeMux)(nil)
