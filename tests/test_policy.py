"""
Tests for trust policy evaluation.
Run with: pytest tests/
"""
import pytest

from github_sts.policy import TrustPolicy


class TestTrustPolicyExactMatch:
    def _policy(self, **kwargs):
        base = {
            "issuer": "https://token.actions.githubusercontent.com",
            "subject": "repo:org/repo:ref:refs/heads/main",
            "permissions": {"contents": "read"},
        }
        base.update(kwargs)
        return TrustPolicy(**base)

    def test_exact_match_passes(self):
        policy = self._policy()
        claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "sub": "repo:org/repo:ref:refs/heads/main",
        }
        assert policy.evaluate(claims) is True

    def test_wrong_issuer_denied(self):
        policy = self._policy()
        claims = {
            "iss": "https://evil.example.com",
            "sub": "repo:org/repo:ref:refs/heads/main",
        }
        assert policy.evaluate(claims) is False

    def test_wrong_subject_denied(self):
        policy = self._policy()
        claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "sub": "repo:org/repo:ref:refs/heads/develop",
        }
        assert policy.evaluate(claims) is False


class TestTrustPolicyPatterns:
    def test_subject_pattern_matches(self):
        policy = TrustPolicy(
            issuer="https://accounts.google.com",
            subject_pattern=r"[0-9]+",
            permissions={"contents": "read"},
        )
        assert policy.evaluate({"iss": "https://accounts.google.com", "sub": "1234567890"})
        assert not policy.evaluate({"iss": "https://accounts.google.com", "sub": "not-a-number"})

    def test_claim_pattern_matches(self):
        policy = TrustPolicy(
            issuer="https://accounts.google.com",
            subject_pattern=r"[0-9]+",
            claim_pattern={"email": r".*@example\.com"},
            permissions={"contents": "read"},
        )
        good = {"iss": "https://accounts.google.com", "sub": "123", "email": "dev@example.com"}
        bad  = {"iss": "https://accounts.google.com", "sub": "123", "email": "dev@evil.com"}
        assert policy.evaluate(good)
        assert not policy.evaluate(bad)

    def test_exact_subject_takes_priority_over_pattern(self):
        policy = TrustPolicy(
            issuer="https://token.actions.githubusercontent.com",
            subject="repo:org/repo:ref:refs/heads/main",
            subject_pattern=r".*",   # would match anything, but subject wins
            permissions={"issues": "write"},
        )
        claims = {"iss": "https://token.actions.githubusercontent.com",
                  "sub": "repo:org/repo:ref:refs/heads/develop"}
        assert not policy.evaluate(claims)

    def test_workflow_ref_claim_pattern(self):
        """Restrict to a specific workflow file (GitHub-specific claim)."""
        policy = TrustPolicy(
            issuer="https://token.actions.githubusercontent.com",
            subject_pattern=r"repo:org/repo:.*",
            claim_pattern={
                "job_workflow_ref": r"org/repo/.github/workflows/deploy\.yml@.*"
            },
            permissions={"deployments": "write"},
        )
        good = {
            "iss": "https://token.actions.githubusercontent.com",
            "sub": "repo:org/repo:ref:refs/heads/main",
            "job_workflow_ref": "org/repo/.github/workflows/deploy.yml@refs/heads/main",
        }
        bad = {
            "iss": "https://token.actions.githubusercontent.com",
            "sub": "repo:org/repo:ref:refs/heads/main",
            "job_workflow_ref": "org/repo/.github/workflows/untrusted.yml@refs/heads/main",
        }
        assert policy.evaluate(good)
        assert not policy.evaluate(bad)


class TestPolicyValidation:
    def test_invalid_permission_name_rejected(self):
        with pytest.raises((ValueError, Exception)):
            TrustPolicy(
                issuer="https://example.com",
                permissions={"nonexistent_permission": "read"},
            )

    def test_invalid_permission_level_rejected(self):
        with pytest.raises((ValueError, Exception)):
            TrustPolicy(
                issuer="https://example.com",
                permissions={"contents": "superadmin"},
            )

    def test_multiple_permissions_accepted(self):
        policy = TrustPolicy(
            issuer="https://token.actions.githubusercontent.com",
            subject="repo:org/repo:ref:refs/heads/main",
            permissions={
                "contents": "read",
                "issues": "write",
                "pull_requests": "write",
            },
        )
        assert len(policy.permissions) == 3
