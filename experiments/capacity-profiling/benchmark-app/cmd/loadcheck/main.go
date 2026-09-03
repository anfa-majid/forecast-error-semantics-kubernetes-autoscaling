package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"sort"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

func envInt(name string, fallback int) int {
	v, err := strconv.Atoi(os.Getenv(name))
	if err != nil || v < 1 {
		return fallback
	}
	return v
}
func optionalEnvInt(name string) int {
	v, _ := strconv.Atoi(os.Getenv(name))
	if v < 1 {
		return 0
	}
	return v
}

func main() {
	url := os.Getenv("TARGET_URL")
	if url == "" {
		url = "http://benchmark-app:8080/work"
	}
	requests, concurrency := envInt("REQUESTS", 2000), envInt("CONCURRENCY", 64)
	targetRPS, durationSeconds := optionalEnvInt("TARGET_RPS"), envInt("DURATION_SECONDS", 30)
	mode := "closed_loop"
	if targetRPS > 0 {
		mode = "open_loop"
		requests = targetRPS * durationSeconds
	}
	client := &http.Client{Timeout: 10 * time.Second, Transport: &http.Transport{MaxIdleConns: concurrency, MaxIdleConnsPerHost: concurrency, MaxConnsPerHost: concurrency}}
	jobs := make(chan struct{}, concurrency)
	latencies := make([]time.Duration, 0, requests)
	pods := map[string]int{}
	var mu sync.Mutex
	var errors atomic.Int64
	start := time.Now()
	var wg sync.WaitGroup
	request := func(bounded bool) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if bounded {
				defer func() { <-jobs }()
			}
			requestStart := time.Now()
			response, err := client.Get(url)
			latency := time.Since(requestStart)
			if err != nil {
				errors.Add(1)
				return
			}
			_ = response.Body.Close()
			if response.StatusCode != http.StatusOK {
				errors.Add(1)
				return
			}
			mu.Lock()
			latencies = append(latencies, latency)
			pods[response.Header.Get("X-Benchmark-Pod")]++
			mu.Unlock()
		}()
	}
	if targetRPS > 0 {
		ticker := time.NewTicker(time.Second / time.Duration(targetRPS))
		defer ticker.Stop()
		for range requests {
			<-ticker.C
			request(false)
		}
	} else {
		for range requests {
			jobs <- struct{}{}
			request(true)
		}
	}
	wg.Wait()
	elapsed := time.Since(start)
	sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
	percentile := func(p float64) float64 {
		if len(latencies) == 0 {
			return 0
		}
		index := int(float64(len(latencies)-1) * p)
		return float64(latencies[index].Microseconds()) / 1000
	}
	averageMilliseconds := 0.0
	maximumMilliseconds := 0.0
	if len(latencies) > 0 {
		var total time.Duration
		for _, latency := range latencies {
			total += latency
		}
		averageMilliseconds = float64(total.Microseconds()) / 1000 / float64(len(latencies))
		maximumMilliseconds = float64(latencies[len(latencies)-1].Microseconds()) / 1000
	}
	completionRatio := float64(len(latencies)) / float64(requests)
	failureRate := float64(errors.Load()) / float64(requests)
	measurementThroughput := float64(len(latencies)) / elapsed.Seconds()
	if targetRPS > 0 {
		measurementThroughput = float64(len(latencies)) / float64(durationSeconds)
	}
	result := map[string]any{
		"mode": mode, "target_rps": targetRPS, "duration_seconds": durationSeconds,
		"scheduled": requests, "sent": requests, "requests": requests, "concurrency": concurrency,
		"completed": len(latencies), "errors": errors.Load(), "completion_ratio": completionRatio,
		"failure_rate": failureRate, "elapsed_seconds": elapsed.Seconds(),
		"throughput_rps":             float64(len(latencies)) / elapsed.Seconds(),
		"measurement_throughput_rps": measurementThroughput,
		"average_ms":                 averageMilliseconds, "p50_ms": percentile(.50), "p95_ms": percentile(.95),
		"p99_ms": percentile(.99), "max_ms": maximumMilliseconds, "serving_pods": pods,
	}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		panic(err)
	}
	if errors.Load() != 0 {
		fmt.Fprintln(os.Stderr, "load check completed with errors")
		os.Exit(1)
	}
}
