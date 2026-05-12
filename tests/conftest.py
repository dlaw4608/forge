"""Shared test fixtures for Forge test suite."""

import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from forge.config import Settings
from forge.main import app


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token="test-token",
        jira_user_email="test@example.com",
        jira_webhook_secret="test-webhook-secret",
        github_token="test-github-token",
        github_webhook_secret="test-github-webhook-secret",
        anthropic_api_key="test-anthropic-key",
    )


@pytest.fixture
def mock_redis() -> Generator[MagicMock, None, None]:
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.ping = AsyncMock(return_value=True)
    mock.xlen = AsyncMock(return_value=0)
    mock.xadd = AsyncMock(return_value="1234567890-0")
    mock.xreadgroup = AsyncMock(return_value=[])
    mock.xack = AsyncMock(return_value=1)
    mock.xgroup_create = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    yield mock


@pytest.fixture
def mock_jira_client() -> Generator[MagicMock, None, None]:
    """Create a mock Jira client."""
    from forge.integrations.jira.models import JiraIssue

    mock = MagicMock()
    mock.get_issue = AsyncMock(
        return_value=JiraIssue(
            key="TEST-123",
            id="10001",
            summary="Test Issue",
            description="Test description",
            status="Open",
            issue_type="Feature",
        )
    )
    mock.update_description = AsyncMock()
    mock.transition_issue = AsyncMock()
    mock.create_epic = AsyncMock(return_value="TEST-124")
    mock.create_task = AsyncMock(return_value="TEST-125")
    mock.delete_issue = AsyncMock()
    mock.add_comment = AsyncMock()
    mock.close = AsyncMock()
    yield mock


@pytest.fixture
def mock_github_client() -> Generator[MagicMock, None, None]:
    """Create a mock GitHub client."""
    mock = MagicMock()
    mock.create_pull_request = AsyncMock(
        return_value={
            "number": 42,
            "html_url": "https://github.com/org/repo/pull/42",
        }
    )
    mock.get_pull_request = AsyncMock(
        return_value={
            "number": 42,
            "state": "open",
            "title": "Test PR",
        }
    )
    mock.create_issue_comment = AsyncMock()
    mock.get_check_runs = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    yield mock


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_jira_webhook_payload() -> dict:
    """Sample Jira webhook payload for testing."""
    return {
        "timestamp": 1711814400000,
        "webhookEvent": "jira:issue_updated",
        "issue_event_type_name": "issue_generic",
        "user": {
            "accountId": "user-123",
            "displayName": "Test User",
        },
        "issue": {
            "id": "10001",
            "key": "TEST-123",
            "fields": {
                "issuetype": {"name": "Feature"},
                "status": {"name": "Drafting PRD"},
                "summary": "Test Feature",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Raw requirements"}],
                        }
                    ],
                },
            },
        },
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "Open",
                    "toString": "Drafting PRD",
                }
            ]
        },
    }


@pytest.fixture
def sample_github_webhook_payload() -> dict:
    """Sample GitHub webhook payload for testing."""
    return {
        "action": "synchronize",
        "number": 42,
        "pull_request": {
            "id": 12345,
            "number": 42,
            "state": "open",
            "title": "TEST-456: Implement feature",
            "head": {
                "ref": "feature/TEST-456",
                "sha": "abc123def456",
            },
            "base": {"ref": "main"},
            "html_url": "https://github.com/org/repo/pull/42",
        },
        "repository": {"full_name": "org/repo"},
    }


def ai_review_node_available() -> bool:
    """Check if ai_review node is available in the workflow.

    This function checks:
    1. If the ai_review module can be imported
    2. If ai_review is exported from forge.workflow.nodes
    3. If FORGE_ENABLE_AI_REVIEW_TESTS env var is set (for force-enable during development)

    Returns:
        bool: True if ai_review node is available, False otherwise.
    """
    # Check force-enable flag first
    if os.environ.get("FORGE_ENABLE_AI_REVIEW_TESTS", "").lower() in ("1", "true", "yes"):
        return True

    try:
        # Check if ai_review can be imported from workflow nodes
        from forge.workflow.nodes import ai_review

        # If import succeeds, the node is available
        return ai_review is not None
    except (ImportError, AttributeError):
        # Node not yet implemented or not exported
        return False


# Pytest skip marker for ai_review tests
# Use this to conditionally skip tests when ai_review node is not available
skip_if_ai_review_unavailable = pytest.mark.skipif(
    not ai_review_node_available(),
    reason="ai_review node not yet implemented - tests will run when node is available",
)
