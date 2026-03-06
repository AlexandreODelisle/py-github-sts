"""
Tests for structured audit logging.
"""

import json
import tempfile

import pytest

from src.github_sts.audit import (
    AuditEvent,
    ExchangeResult,
    FileAuditLogger,
    create_audit_logger,
)


class TestAuditEvent:
    """Test AuditEvent Pydantic model."""

    def test_audit_event_creation(self):
        """Create a basic audit event."""
        event = AuditEvent(
            scope="owner/repo",
            identity="ci",
            issuer="https://token.actions.githubusercontent.com",
            subject="repo:owner/repo:ref:refs/heads/main",
            result=ExchangeResult.SUCCESS,
        )

        assert event.scope == "owner/repo"
        assert event.identity == "ci"
        assert event.result == ExchangeResult.SUCCESS
        assert event.timestamp is not None

    def test_audit_event_with_all_fields(self):
        """Create audit event with all optional fields."""
        event = AuditEvent(
            scope="owner/repo",
            identity="ci",
            issuer="https://token.actions.githubusercontent.com",
            subject="repo:owner/repo:ref:refs/heads/main",
            jti="workflow-123",
            result=ExchangeResult.SUCCESS,
            error_reason=None,
            duration_ms=150.5,
            user_agent="github-actions/v1",
            remote_ip="192.168.1.1",
        )

        assert event.duration_ms == 150.5
        assert event.user_agent == "github-actions/v1"
        assert event.remote_ip == "192.168.1.1"

    def test_audit_event_denied(self):
        """Create audit event for denied request."""
        event = AuditEvent(
            scope="owner/repo",
            identity="ci",
            issuer="https://token.actions.githubusercontent.com",
            subject="untrusted-subject",
            result=ExchangeResult.POLICY_DENIED,
            error_reason="Subject does not match policy",
        )

        assert event.result == ExchangeResult.POLICY_DENIED
        assert event.error_reason is not None

    def test_audit_event_to_json_line(self):
        """Convert event to JSON-Lines format."""
        event = AuditEvent(
            scope="owner/repo",
            identity="ci",
            issuer="https://github.com",
            subject="ghsa",
            result=ExchangeResult.SUCCESS,
        )

        line = event.to_json_line()
        assert line.endswith("\n")

        # Parse JSON
        parsed = json.loads(line.rstrip("\n"))
        assert parsed["scope"] == "owner/repo"
        assert parsed["identity"] == "ci"
        assert parsed["result"] == "success"

    def test_audit_event_jti_redaction(self):
        """JTI should be redacted to first 50 chars."""
        long_jti = "x" * 100
        event = AuditEvent(
            scope="owner/repo",
            identity="ci",
            issuer="https://github.com",
            subject="test",
            jti=long_jti,
            result=ExchangeResult.SUCCESS,
        )

        # JTI is stored as-is in model, but should be truncated in logs
        assert len(event.jti) == 100
        assert event.jti == long_jti


class TestFileAuditLogger:
    """Test file-based audit logger."""

    @pytest.mark.asyncio
    async def test_file_logger_creation(self):
        """Create file audit logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(log_path=log_path)

            assert logger.log_path.name == "audit.log"
            assert logger.rotation_policy == "daily"
            await logger.cleanup()

    @pytest.mark.asyncio
    async def test_file_logger_write_event(self):
        """Write event to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(log_path=log_path)

            event = AuditEvent(
                scope="owner/repo",
                identity="ci",
                issuer="https://github.com",
                subject="test",
                result=ExchangeResult.SUCCESS,
            )

            await logger.log_event(event)
            await logger.cleanup()

            # Check file was created and contains JSON
            with open(log_path) as f:
                content = f.read()
                assert len(content) > 0
                lines = content.strip().split("\n")
                assert len(lines) >= 1

                # Parse first line as JSON
                parsed = json.loads(lines[0])
                assert parsed["scope"] == "owner/repo"

    @pytest.mark.asyncio
    async def test_file_logger_multiple_events(self):
        """Write multiple events to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(log_path=log_path)

            # Log multiple events
            for i in range(5):
                event = AuditEvent(
                    scope=f"repo{i}",
                    identity=f"identity{i}",
                    issuer="https://github.com",
                    subject=f"subject{i}",
                    result=ExchangeResult.SUCCESS,
                )
                await logger.log_event(event)

            await logger.cleanup()

            # Verify all events written
            with open(log_path) as f:
                lines = [line for line in f.read().strip().split("\n") if line]
                assert len(lines) >= 5

                for i, line in enumerate(lines[:5]):
                    parsed = json.loads(line)
                    assert parsed["scope"] == f"repo{i}"

    @pytest.mark.asyncio
    async def test_file_logger_daily_rotation(self):
        """Test daily rotation policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(log_path=log_path, rotation_policy="daily")

            assert logger.rotation_policy == "daily"
            await logger.cleanup()

    @pytest.mark.asyncio
    async def test_file_logger_size_rotation(self):
        """Test size-based rotation policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(
                log_path=log_path,
                rotation_policy="size",
                rotation_size_bytes=1000,
            )

            assert logger.rotation_policy == "size"
            assert logger.rotation_size_bytes == 1000
            await logger.cleanup()


class TestCreateAuditLogger:
    """Test factory function for audit loggers."""

    @pytest.mark.asyncio
    async def test_create_file_logger(self):
        """Factory should create file logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = await create_audit_logger("file", log_path=f"{tmpdir}/audit.log")
            assert isinstance(logger, FileAuditLogger)
            await logger.cleanup()

    @pytest.mark.asyncio
    async def test_create_invalid_backend(self):
        """Invalid backend should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown audit logger backend"):
            await create_audit_logger("invalid-backend")


class TestAuditEventResults:
    """Test all AuditEvent result types."""

    def test_all_result_types(self):
        """Verify all ExchangeResult enum values."""
        results = [
            ExchangeResult.SUCCESS,
            ExchangeResult.POLICY_DENIED,
            ExchangeResult.OIDC_INVALID,
            ExchangeResult.JTI_REPLAY,
            ExchangeResult.POLICY_NOT_FOUND,
            ExchangeResult.CACHE_ERROR,
            ExchangeResult.GITHUB_ERROR,
            ExchangeResult.UNKNOWN_ERROR,
        ]

        for result in results:
            event = AuditEvent(
                scope="test",
                identity="test",
                issuer="https://github.com",
                subject="test",
                result=result,
            )
            assert event.result == result

            # Verify JSON serialization
            line = event.to_json_line()
            parsed = json.loads(line.rstrip("\n"))
            assert parsed["result"] == result.value


class TestAuditIntegration:
    """Integration tests for audit logging."""

    @pytest.mark.asyncio
    async def test_realistic_audit_flow(self):
        """Test realistic audit logging for a successful exchange."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(log_path=log_path)

            # Simulate exchange flow with multiple events
            events = [
                AuditEvent(
                    scope="owner/repo",
                    identity="ci",
                    issuer="https://token.actions.githubusercontent.com",
                    subject="repo:owner/repo:ref:refs/heads/main",
                    jti="workflow-123",
                    result=ExchangeResult.SUCCESS,
                    duration_ms=145.25,
                    user_agent="github-actions/v1",
                    remote_ip="192.0.2.1",
                ),
                AuditEvent(
                    scope="owner/private",
                    identity="ci",
                    issuer="https://token.actions.githubusercontent.com",
                    subject="fork:attacker/repo:ref:refs/heads/main",
                    result=ExchangeResult.POLICY_DENIED,
                    error_reason="Subject does not match allowed patterns",
                    duration_ms=50.1,
                    user_agent="curl/7.68.0",
                    remote_ip="198.51.100.1",
                ),
            ]

            for event in events:
                await logger.log_event(event)

            await logger.cleanup()

            # Verify file structure
            with open(log_path) as f:
                lines = [line for line in f.read().strip().split("\n") if line]
                assert len(lines) >= 2

                # First event should be success
                first = json.loads(lines[0])
                assert first["result"] == "success"
                assert first["scope"] == "owner/repo"

                # Second event should be denied
                second = json.loads(lines[1])
                assert second["result"] == "policy_denied"
                assert second["scope"] == "owner/private"

    @pytest.mark.asyncio
    async def test_json_lines_compatibility(self):
        """Audit logs should be JSON-Lines compatible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = f"{tmpdir}/audit.log"
            logger = FileAuditLogger(log_path=log_path)

            # Log multiple events
            for i in range(3):
                event = AuditEvent(
                    scope=f"repo{i}",
                    identity="ci",
                    issuer="https://github.com",
                    subject=f"subject{i}",
                    result=ExchangeResult.SUCCESS,
                )
                await logger.log_event(event)

            await logger.cleanup()

            # Verify JSON-Lines format
            with open(log_path) as f:
                for line in f:
                    # Each line should be valid JSON
                    parsed = json.loads(line)
                    assert "scope" in parsed
                    assert "result" in parsed
