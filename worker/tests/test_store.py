from worker.app.store import WorkerJobStore


def test_running_job_is_failed_after_restart(tmp_path, job_payload):
    store = WorkerJobStore(tmp_path / "worker.db")
    store.initialize()
    job, _ = store.put("job-001", "a" * 64, job_payload)
    assert job.status == "queued"
    store.update("job-001", status="running")

    restarted_store = WorkerJobStore(tmp_path / "worker.db")
    restarted_store.initialize()
    restarted_store.mark_interrupted_jobs()
    recovered = restarted_store.get("job-001")
    assert recovered is not None
    assert recovered.status == "failed"
    assert recovered.error_code == "worker_restarted"
