"""
Automated Pytest Test Suite for Dialogue Intent Stack Manager.
Domain: Long-Horizon Agent Context & State Architecture
Standard: Autonomous Agent State Machine & Token Economy RFC
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, AuditTrail, SecurityException
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_phi_guard_ssn_detection():
    """Test that SSN patterns are detected and blocked."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient SSN: 123-45-6789")


def test_phi_guard_phone_detection():
    """Test that phone number patterns are detected and blocked."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Contact patient at 555-123-4567")


def test_phi_guard_email_detection():
    """Test that email patterns are detected and blocked."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Send results to patient@hospital.com")


def test_phi_guard_redaction():
    """Test that PHI patterns are properly redacted."""
    redacted = PHIGuard.redact_phi("Patient MRN-12345 has SSN 123-45-6789")
    assert "MRN" not in redacted or "12345" not in redacted
    assert "123-45-6789" not in redacted


def test_phi_guard_empty_input():
    """Test that empty/None input is handled gracefully."""
    PHIGuard.assert_no_phi("")
    PHIGuard.assert_no_phi(None)


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_audit_trail_signature_verification():
    """Test that audit trail HMAC signatures are properly verified."""
    trail = AuditTrail(secret_key="test-secret-key-for-verification")
    trail.log("test_actor", "test_tier", "TEST_EVENT", {"data": "value1"})
    trail.log("test_actor", "test_tier", "TEST_EVENT", {"data": "value2"})

    # Integrity should pass for untampered trail
    assert trail.verify_integrity() is True

    # Tampering with an entry should fail verification
    if trail.logs:
        trail.logs[0]["current_hash"] = "tampered_hash"
        assert trail.verify_integrity() is False


def test_audit_trail_chain_linkage():
    """Test that audit trail chain linkage is maintained."""
    trail = AuditTrail(secret_key="test-chain-key")
    trail.log("actor1", "tier1", "EVENT_A", {"x": 1})
    trail.log("actor2", "tier2", "EVENT_B", {"y": 2})
    trail.log("actor3", "tier3", "EVENT_C", {"z": 3})

    # Verify chain linkage
    assert len(trail.logs) == 3
    assert trail.logs[0]["prev_hash"] == "GENESIS_BLOCK_0000000000000000"
    assert trail.logs[1]["prev_hash"] == trail.logs[0]["current_hash"]
    assert trail.logs[2]["prev_hash"] == trail.logs[1]["current_hash"]


def test_audit_trail_empty():
    """Test that empty audit trail passes integrity check."""
    trail = AuditTrail(secret_key="test-empty-key")
    assert trail.verify_integrity() is True
    assert len(trail.get_trail()) == 0


def test_cli_batch_missing_file():
    """Test that batch command handles missing input file gracefully."""
    result = main(["batch", "-i", "nonexistent_file.csv"])
    assert result == 1


def test_supervisor_phi_blocking():
    """Test that supervisor blocks PHI-containing payloads."""
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-01",
        target_identifier="Patient MRN-12345",  # PHI violation
        primary_metric=10.0,
        secondary_metric=5.0,
        status_descriptor="NOMINAL"
    )
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)
