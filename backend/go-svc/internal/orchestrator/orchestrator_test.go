package orchestrator_test

import (
	"testing"
	"time"

	"ceron-go/internal/orchestrator"
	"ceron-go/internal/queue"
	"ceron-go/internal/store"
)

func TestRunPersistsAndLists(t *testing.T) {
	st := store.NewMemory()
	orc := orchestrator.New(nil, st) // Py 为 nil 也安全，因为使用 PipelineFn 桩
	orc.PipelineFn = func(vertical, text string) (map[string]interface{}, error) {
		return map[string]interface{}{"vertical": vertical, "ok": true}, nil
	}

	job, err := orc.Run("j1", "insurance_hk", "保单文本")
	if err != nil {
		t.Fatal(err)
	}
	if job.Status != "completed" {
		t.Fatalf("status=%s", job.Status)
	}
	if job.Result["ok"] != true {
		t.Fatalf("result missing: %v", job.Result)
	}

	jobs, err := orc.List()
	if err != nil || len(jobs) != 1 {
		t.Fatalf("list=%v err=%v", jobs, err)
	}

	got, err := orc.Get("j1")
	if err != nil || got.Status != "completed" {
		t.Fatalf("get=%v err=%v", got, err)
	}
}

func TestAsyncPoolCompletes(t *testing.T) {
	st := store.NewMemory()
	orc := orchestrator.New(nil, st)
	orc.PipelineFn = func(vertical, text string) (map[string]interface{}, error) {
		return map[string]interface{}{"x": 1}, nil
	}
	pool := queue.NewPool(2, 8, orc.Process)
	orc.Queue = pool

	job := orc.Submit("a1", "family_office", "客户文本")
	if job.Status != "queued" {
		t.Fatalf("should be queued, got %s", job.Status)
	}

	deadline := time.Now().Add(2 * time.Second)
	for {
		got, _ := orc.Get("a1")
		if got != nil && got.Status == "completed" {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("async job did not complete, status=%s", got.Status)
		}
		time.Sleep(50 * time.Millisecond)
	}
	pool.Close()
}
