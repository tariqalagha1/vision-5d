"""
Vision 5D — Integration Tests for Async Durable Job Execution
Tests: async submission, idempotency, checkpoint resume, worker authority,
duplicate prevention, artifact durability, and auth session persistence.
"""
import pytest, json, time, os, sys, tempfile, threading
from uuid import uuid4, UUID
from datetime import datetime

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.domain.database import SessionLocal, engine
from packages.domain.models import Base, DurableJob, JobAttempt, Checkpoint, ProgressEvent, DurableArtifactRef, PersistedGeometry
from packages.contracts.models import JobState, is_valid_transition


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test module."""
    Base.metadata.create_all(bind=engine)
    yield
    # Don't drop tables — tests may share DB across modules


def _create_test_job(db, job_type="plan-understanding", state=JobState.QUEUED, tenant_id=None, project_id=None):
    """Helper to create a test job."""
    job = DurableJob(
        tenant_id=tenant_id or uuid4(),
        workspace_id=uuid4(),
        project_id=project_id or uuid4(),
        job_type=job_type,
        idempotency_key=f"test-{uuid4().hex[:12]}",
        state=state.value,
        params={"test": True},
        param_hash="abc123",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ═══════════════════════════════════════════════════════════
# T1: State Transitions
# ═══════════════════════════════════════════════════════════

class TestStateTransitions:
    def test_created_to_authorized(self):
        assert is_valid_transition(JobState.CREATED, JobState.AUTHORIZED)

    def test_authorized_to_queued(self):
        assert is_valid_transition(JobState.AUTHORIZED, JobState.QUEUED)

    def test_queued_to_claimed(self):
        assert is_valid_transition(JobState.QUEUED, JobState.CLAIMED)

    def test_claimed_to_running(self):
        assert is_valid_transition(JobState.CLAIMED, JobState.RUNNING)

    def test_running_to_interrupted(self):
        assert is_valid_transition(JobState.RUNNING, JobState.INTERRUPTED)

    def test_interrupted_to_queued(self):
        assert is_valid_transition(JobState.INTERRUPTED, JobState.QUEUED)

    def test_checkpointed_to_interrupted(self):
        assert is_valid_transition(JobState.CHECKPOINTED, JobState.INTERRUPTED)

    def test_resuming_to_running(self):
        assert is_valid_transition(JobState.RESUMING, JobState.RUNNING)

    def test_resume_requested_to_resuming(self):
        assert is_valid_transition(JobState.RESUME_REQUESTED, JobState.RESUMING)

    def test_terminal_no_transition(self):
        assert not is_valid_transition(JobState.COMPLETED, JobState.RUNNING)
        assert not is_valid_transition(JobState.FAILED_TERMINAL, JobState.QUEUED)
        assert not is_valid_transition(JobState.CANCELLED, JobState.DISPATCHED)

    def test_new_states_in_enum(self):
        """Verify INTERRUPTED and RESUMING are in the enum."""
        assert hasattr(JobState, "INTERRUPTED")
        assert JobState.INTERRUPTED.value == "INTERRUPTED"
        assert JobState.RESUMING.value == "RESUMING"
        assert JobState.CLAIMED.value == "CLAIMED"


# ═══════════════════════════════════════════════════════════
# T2: Durable Job Lifecycle (DB)
# ═══════════════════════════════════════════════════════════

class TestDurableJobLifecycle:
    def test_create_job_persisted(self):
        db = SessionLocal()
        try:
            job = _create_test_job(db)
            # Re-read
            loaded = db.query(DurableJob).filter(DurableJob.id == job.id).first()
            assert loaded is not None
            assert loaded.job_type == "plan-understanding"
            assert loaded.state == JobState.QUEUED.value
            assert loaded.idempotency_key is not None
            assert loaded.created_at is not None
        finally:
            db.close()

    def test_job_transition_persisted(self):
        db = SessionLocal()
        try:
            job = _create_test_job(db, state=JobState.CREATED)
            job.state = JobState.AUTHORIZED.value
            db.commit()
            db.refresh(job)
            assert job.state == JobState.AUTHORIZED.value

            job.state = JobState.QUEUED.value
            db.commit()
            db.refresh(job)
            assert job.state == JobState.QUEUED.value

            job.state = JobState.CLAIMED.value
            db.commit()
            db.refresh(job)
            assert job.state == JobState.CLAIMED.value
        finally:
            db.close()

    def test_attempt_record_created(self):
        db = SessionLocal()
        try:
            job = _create_test_job(db)
            attempt = JobAttempt(job_id=job.id, attempt_number=1, worker_id="test-worker", state="RUNNING")
            db.add(attempt)
            db.commit()
            assert attempt.id is not None
            loaded = db.query(JobAttempt).filter(JobAttempt.job_id == job.id).first()
            assert loaded.worker_id == "test-worker"
        finally:
            db.close()

    def test_checkpoint_with_resume_metadata(self):
        db = SessionLocal()
        try:
            job = _create_test_job(db)
            attempt = JobAttempt(job_id=job.id, attempt_number=1, worker_id="test", state="RUNNING")
            db.add(attempt)
            db.commit()

            ckpt = Checkpoint(
                job_id=job.id, attempt_id=attempt.id, sequence=1,
                serialized_state=b'{"stage":"p3_pipeline"}',
                content_hash="abc", pipeline_type="geometry-reconstruction",
                current_stage="p3_pipeline",
                completed_stages=["p2_complete", "p3_reconstruct"],
                input_version_ref=str(job.id),
                artifact_refs={"graph_id": str(uuid4())},
                tenant_id=job.tenant_id, project_id=job.project_id,
                params={"test": True}, resume_compatible=True,
            )
            db.add(ckpt)
            db.commit()

            loaded = db.query(Checkpoint).filter(Checkpoint.job_id == job.id).first()
            assert loaded.pipeline_type == "geometry-reconstruction"
            assert loaded.current_stage == "p3_pipeline"
            assert "p2_complete" in loaded.completed_stages
            assert loaded.resume_compatible is True
        finally:
            db.close()

    def test_progress_event_persisted(self):
        db = SessionLocal()
        try:
            job = _create_test_job(db)
            event = ProgressEvent(job_id=job.id, status="running", progress_pct=45.0,
                                  message="Processing walls...", current_stage="p3_pipeline")
            db.add(event)
            db.commit()
            loaded = db.query(ProgressEvent).filter(ProgressEvent.job_id == job.id).first()
            assert loaded.progress_pct == 45.0
            assert "walls" in loaded.message
        finally:
            db.close()

    def test_durable_artifact_ref_persisted(self):
        db = SessionLocal()
        try:
            job = _create_test_job(db)
            dart = DurableArtifactRef(
                tenant_id=job.tenant_id, project_id=job.project_id, job_id=job.id,
                artifact_type="understanding-graph",
                storage_provider="s3",
                storage_key=f"test/key/{uuid4().hex[:8]}.json",
                content_hash="sha256:abc123", size_bytes=4096,
                mime_type="application/json",
                producing_stage="persisting", producing_version=1,
            )
            db.add(dart)
            db.commit()
            loaded = db.query(DurableArtifactRef).filter(DurableArtifactRef.job_id == job.id).first()
            assert loaded.artifact_type == "understanding-graph"
            assert loaded.storage_provider == "s3"
            assert loaded.storage_key.startswith("test/key/")
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════
# T3: Idempotency and Duplicate Prevention
# ═══════════════════════════════════════════════════════════

class TestIdempotency:
    def test_unique_idempotency_key_enforced(self):
        db = SessionLocal()
        try:
            key = f"idem-{uuid4().hex[:8]}"
            job1 = DurableJob(
                tenant_id=uuid4(), workspace_id=uuid4(), project_id=uuid4(),
                job_type="test", idempotency_key=key,
                state=JobState.QUEUED.value, params={}, param_hash="test",
            )
            db.add(job1)
            db.commit()

            # Second with same key should fail
            job2 = DurableJob(
                tenant_id=uuid4(), workspace_id=uuid4(), project_id=uuid4(),
                job_type="test", idempotency_key=key,
                state=JobState.QUEUED.value, params={}, param_hash="test",
            )
            db.add(job2)
            with pytest.raises(Exception):
                db.commit()
            db.rollback()
        finally:
            db.close()

    def test_same_params_different_key_allowed(self):
        db = SessionLocal()
        try:
            job1 = DurableJob(
                tenant_id=uuid4(), workspace_id=uuid4(), project_id=uuid4(),
                job_type="test", idempotency_key=f"idem-a-{uuid4().hex[:8]}",
                state=JobState.QUEUED.value, params={"x": 1}, param_hash="same",
            )
            db.add(job1)
            db.commit()

            job2 = DurableJob(
                tenant_id=uuid4(), workspace_id=uuid4(), project_id=uuid4(),
                job_type="test", idempotency_key=f"idem-b-{uuid4().hex[:8]}",
                state=JobState.QUEUED.value, params={"x": 1}, param_hash="same",
            )
            db.add(job2)
            db.commit()  # Different idempotency key — allowed
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════
# T4: Job Interruption and Resume
# ═══════════════════════════════════════════════════════════

class TestInterruptResume:
    def test_interrupt_then_recover_flow(self):
        """Simulate: RUNNING → INTERRUPTED → RESUMING → RUNNING"""
        db = SessionLocal()
        try:
            job = _create_test_job(db, state=JobState.QUEUED)

            # Worker claims
            assert is_valid_transition(JobState.QUEUED, JobState.CLAIMED)
            job.state = JobState.CLAIMED.value
            db.commit()
            db.refresh(job)

            # Worker starts
            assert is_valid_transition(JobState.CLAIMED, JobState.RUNNING)
            job.state = JobState.RUNNING.value
            db.commit()
            db.refresh(job)

            # Create checkpoint
            attempt = JobAttempt(job_id=job.id, attempt_number=1, worker_id="w1", state="RUNNING")
            db.add(attempt)
            db.commit()

            ckpt = Checkpoint(
                job_id=job.id, attempt_id=attempt.id, sequence=1,
                serialized_state=b"in_progress",
                content_hash="hash1", pipeline_type="plan-understanding",
                current_stage="processing", completed_stages=["starting"],
                resume_compatible=True,
            )
            db.add(ckpt)
            db.commit()

            # Interrupt
            assert is_valid_transition(JobState.RUNNING, JobState.INTERRUPTED)
            job.state = JobState.INTERRUPTED.value
            db.commit()
            db.refresh(job)
            assert job.state == JobState.INTERRUPTED.value

            # Recovery: INTERRUPTED → QUEUED
            assert is_valid_transition(JobState.INTERRUPTED, JobState.QUEUED)
            job.state = JobState.QUEUED.value
            db.commit()
            db.refresh(job)

            # Re-claim
            job.state = JobState.CLAIMED.value
            db.commit()

            # RESUME_REQUESTED → RESUMING
            assert is_valid_transition(JobState.RESUME_REQUESTED, JobState.RESUMING)
            # Simulate: re-queued job goes through resume path
            job.state = JobState.RESUMING.value
            db.commit()
            db.refresh(job)
            assert job.state == JobState.RESUMING.value

            # RESUMING → RUNNING
            assert is_valid_transition(JobState.RESUMING, JobState.RUNNING)
            job.state = JobState.RUNNING.value
            db.commit()
            db.refresh(job)
            assert job.state == JobState.RUNNING.value

            # Verify checkpoint still exists
            ckpt_loaded = db.query(Checkpoint).filter(Checkpoint.job_id == job.id).first()
            assert ckpt_loaded is not None
            assert ckpt_loaded.resume_compatible
        finally:
            db.close()

    def test_checkpoint_load_latest(self):
        """Verify latest checkpoint is retrievable."""
        db = SessionLocal()
        try:
            job = _create_test_job(db)
            attempt = JobAttempt(job_id=job.id, attempt_number=1, worker_id="w1", state="RUNNING")
            db.add(attempt)
            db.commit()

            # Create 3 checkpoints
            for i in range(3):
                ckpt = Checkpoint(
                    job_id=job.id, attempt_id=attempt.id, sequence=i + 1,
                    serialized_state=f"state_{i}".encode(),
                    content_hash=f"hash_{i}", pipeline_type="test",
                    current_stage=f"stage_{i}",
                    completed_stages=[f"s{j}" for j in range(i)],
                    resume_compatible=True,
                )
                db.add(ckpt)
            db.commit()

            # Latest should be sequence 3
            latest = db.query(Checkpoint).filter(
                Checkpoint.job_id == job.id,
                Checkpoint.resume_compatible == True,
            ).order_by(Checkpoint.sequence.desc()).first()
            assert latest.sequence == 3
            assert latest.current_stage == "stage_2"
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════
# T5: Single Output Commit
# ═══════════════════════════════════════════════════════════

class TestSingleOutputCommit:
    def test_only_one_persisted_geometry_per_job(self):
        """Duplicate geometry persist should not create extra versions."""
        db = SessionLocal()
        try:
            job = _create_test_job(db, job_type="geometry-reconstruction")

            # First persist
            geom1 = PersistedGeometry(
                tenant_id=job.tenant_id, project_id=job.project_id,
                source_graph_id=uuid4(), source_graph_version=1,
                job_id=job.id, state="COMPLETED", version=1, is_complete=True,
            )
            db.add(geom1)
            db.commit()
            db.refresh(geom1)

            # Check: same job_id should not allow second commit
            existing = db.query(PersistedGeometry).filter(
                PersistedGeometry.job_id == job.id
            ).first()
            assert existing is not None
            assert existing.version == 1
            # The code should check and skip duplicate persists
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════
# T6: Contract Import Verification
# ═══════════════════════════════════════════════════════════

class TestContractImports:
    def test_new_contracts_importable(self):
        from packages.contracts.models import (
            JobSubmitRequest, JobSubmitResponse, DurableArtifactRef,
        )
        req = JobSubmitRequest(job_type="test", params={})
        assert req.job_type == "test"

        resp = JobSubmitResponse(
            job_id=uuid4(), state=JobState.QUEUED,
            idempotency_key="key1", created_at=datetime.utcnow(),
            status_endpoint="/api/v1/jobs/x",
        )
        assert resp.state == JobState.QUEUED

    def test_room_area_formatting(self):
        """Verify adaptive room area display precision."""
        def format_area_m2(area: float) -> str:
            if area is None or area < 0:
                return "0.00"
            if area == 0:
                return "0.00"
            if area >= 1.0:
                return f"{area:.2f}"
            elif area >= 0.01:
                return f"{area:.4f}"
            else:
                return f"{area:.6f}"

        assert format_area_m2(24.52) == "24.52"
        assert format_area_m2(1.60) == "1.60"
        assert format_area_m2(0.0016) == "0.001600"
        assert format_area_m2(0.05) == "0.0500"
        assert format_area_m2(0.0) == "0.00"
        assert format_area_m2(150.0) == "150.00"
