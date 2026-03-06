"""
Tests for JTI (JWT ID) replay prevention cache.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from src.github_sts.jti_cache import (
    InMemoryJTICache,
    RedisJTICache,
    create_jti_cache,
)


class TestInMemoryJTICache:
    """Test in-memory JTI cache implementation."""

    @pytest.mark.asyncio
    async def test_new_jti_returns_true(self):
        """New JTI should return True (non-replay)."""
        cache = InMemoryJTICache(ttl_seconds=3600)
        exp = int(time.time()) + 3600
        result = await cache.check_and_store("jti-123", exp)
        assert result is True
        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_duplicate_jti_returns_false(self):
        """Duplicate JTI should return False (replay detected)."""
        cache = InMemoryJTICache(ttl_seconds=3600)
        exp = int(time.time()) + 3600
        jti = "jti-replay-test"

        # First attempt
        result1 = await cache.check_and_store(jti, exp)
        assert result1 is True

        # Second attempt (replay)
        result2 = await cache.check_and_store(jti, exp)
        assert result2 is False

        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_different_jtis_both_allowed(self):
        """Different JTIs should both be allowed."""
        cache = InMemoryJTICache(ttl_seconds=3600)
        exp = int(time.time()) + 3600

        result1 = await cache.check_and_store("jti-1", exp)
        result2 = await cache.check_and_store("jti-2", exp)

        assert result1 is True
        assert result2 is True

        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_expired_jti_can_be_reused(self):
        """Expired JTI entries should be removed and can be reused."""
        cache = InMemoryJTICache(ttl_seconds=1)  # 1 second TTL
        jti = "jti-expiring"
        now = int(time.time())

        # Store JTI with immediate expiry
        result1 = await cache.check_and_store(jti, now)
        assert result1 is True

        # Wait for expiry
        await asyncio.sleep(1.1)

        # Same JTI should be allowed again after expiry
        result2 = await cache.check_and_store(jti, now + 10)
        assert result2 is True

        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Cache should handle concurrent access safely."""
        cache = InMemoryJTICache(ttl_seconds=3600)
        exp = int(time.time()) + 3600
        jti = "jti-concurrent"

        # Simulate concurrent access
        tasks = [
            cache.check_and_store(jti, exp),
            cache.check_and_store(jti, exp),
            cache.check_and_store(jti, exp),
        ]

        results = await asyncio.gather(*tasks)

        # Only one should succeed (the race winner)
        assert results.count(True) == 1
        assert results.count(False) == 2

        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Cleanup should complete without error."""
        cache = InMemoryJTICache()
        await cache.cleanup()
        # Should not raise


class TestRedisJTICache:
    """Test Redis JTI cache implementation."""

    @pytest.mark.asyncio
    async def test_redis_initialization(self):
        """Redis cache should initialize correctly (skipped without redis package)."""
        pytest.skip("Redis tests require redis package to be installed")

    @pytest.mark.asyncio
    async def test_redis_new_jti(self):
        """New JTI in Redis should return True (skipped without redis package)."""
        pytest.skip("Redis tests require redis package to be installed")

    @pytest.mark.asyncio
    async def test_redis_duplicate_jti(self):
        """Duplicate JTI in Redis should return False (skipped without redis package)."""
        pytest.skip("Redis tests require redis package to be installed")

    @pytest.mark.asyncio
    async def test_redis_connection_error(self):
        """Redis connection errors should raise JTICacheError (skipped without redis package)."""
        pytest.skip("Redis tests require redis package to be installed")

    def test_redis_missing_import(self):
        """Missing redis package should raise ImportError."""
        with patch.dict("sys.modules", {"redis": None}):
            with pytest.raises(ImportError, match="redis package required"):
                with patch(
                    "builtins.__import__",
                    side_effect=ImportError("No module named 'redis'"),
                ):
                    RedisJTICache(redis_url="redis://localhost:6379/0")


class TestCreateJTICache:
    """Test factory function for creating JTI caches."""

    @pytest.mark.asyncio
    async def test_create_memory_cache(self):
        """Factory should create in-memory cache."""
        cache = await create_jti_cache("memory")
        assert isinstance(cache, InMemoryJTICache)
        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_create_redis_cache(self):
        """Factory should create Redis cache (skipped without redis)."""
        pytest.skip("Redis tests require redis package to be installed")

    @pytest.mark.asyncio
    async def test_create_redis_without_url(self):
        """Creating Redis cache without URL should raise ValueError."""
        with pytest.raises(ValueError, match="redis_url required"):
            await create_jti_cache("redis")

    @pytest.mark.asyncio
    async def test_create_invalid_backend(self):
        """Invalid backend should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown JTI cache backend"):
            await create_jti_cache("invalid-backend")

    @pytest.mark.asyncio
    async def test_create_with_custom_ttl(self):
        """Factory should pass custom TTL to cache."""
        cache = await create_jti_cache("memory", ttl_seconds=1800)
        assert cache.ttl_seconds == 1800
        await cache.cleanup()


class TestJTICacheIntegration:
    """Integration tests with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_realistic_token_flow(self):
        """Test realistic token exchange flow with JTI checks."""
        cache = InMemoryJTICache(ttl_seconds=3600)
        now = int(time.time())

        # Simulate token exchange for GitHub Actions workload
        token_claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "sub": "repo:owner/repo:ref:refs/heads/main",
            "jti": "workflow-run-123",
            "exp": now + 300,  # 5 minute token
        }

        jti = token_claims["jti"]
        exp = token_claims["exp"]

        # First exchange succeeds
        assert await cache.check_and_store(jti, exp) is True

        # Immediate retry with same token should fail (replay)
        assert await cache.check_and_store(jti, exp) is False

        # Different JTI (different workflow run) should succeed
        token_claims["jti"] = "workflow-run-456"
        assert await cache.check_and_store(token_claims["jti"], exp) is True

        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_jti_expiry_cleanup(self):
        """Test that expired JTIs are cleaned up properly."""
        cache = InMemoryJTICache(ttl_seconds=1)
        now = int(time.time())

        # Store multiple JTIs
        for i in range(5):
            jti = f"jti-{i}"
            await cache.check_and_store(jti, now + 1)

        initial_count = len(cache._seen_jtis)
        assert initial_count == 5

        # Wait for expiry
        await asyncio.sleep(1.1)

        # Access cache to trigger cleanup
        await cache.check_and_store("new-jti", now + 3600)

        # Expired entries should be removed
        final_count = len(cache._seen_jtis)
        assert final_count < initial_count

        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_jti_with_missing_exp(self):
        """JTI without exp claim should still be cached."""
        cache = InMemoryJTICache(ttl_seconds=3600)

        # No exp provided
        result = await cache.check_and_store("jti-no-exp", 0)
        assert result is True

        # Should still prevent replay
        result = await cache.check_and_store("jti-no-exp", 0)
        assert result is False

        await cache.cleanup()
