"""Unit tests for AI review status comment posting."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forge.workflow.nodes.ai_reviewer import ai_review


@pytest.mark.asyncio
async def test_ai_review_posts_status_comment_with_pr_number():
    """Test that ai_review posts status comment with PR number when available."""
    # Arrange
    state = {
        "ticket_key": "AISOS-123",
        "current_pr_number": 456,
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock()

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert
    mock_post_status_comment.assert_called_once_with(
        mock_jira,
        "AISOS-123",
        "🤖 CI checks passed. Running AI code review on PR #456.",
    )
    mock_jira.close.assert_called_once()
    assert result["current_node"] == "human_review_gate"
    assert result["ticket_key"] == "AISOS-123"


@pytest.mark.asyncio
async def test_ai_review_posts_fallback_comment_without_pr_number():
    """Test that ai_review posts fallback comment when PR number is unavailable."""
    # Arrange
    state = {
        "ticket_key": "AISOS-789",
        "current_pr_number": None,
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock()

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert
    mock_post_status_comment.assert_called_once_with(
        mock_jira,
        "AISOS-789",
        "🤖 CI checks passed. Running AI code review.",
    )
    mock_jira.close.assert_called_once()
    assert result["current_node"] == "human_review_gate"


@pytest.mark.asyncio
async def test_ai_review_posts_fallback_comment_when_pr_number_missing_from_state():
    """Test that ai_review posts fallback comment when PR number key is missing."""
    # Arrange
    state = {
        "ticket_key": "AISOS-999",
        # No current_pr_number key at all
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock()

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert
    mock_post_status_comment.assert_called_once_with(
        mock_jira,
        "AISOS-999",
        "🤖 CI checks passed. Running AI code review.",
    )
    mock_jira.close.assert_called_once()


@pytest.mark.asyncio
async def test_ai_review_continues_on_comment_posting_failure():
    """Test that ai_review continues workflow when comment posting fails."""
    # Arrange
    state = {
        "ticket_key": "AISOS-456",
        "current_pr_number": 789,
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock(side_effect=Exception("Jira API error"))

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert - workflow should continue despite failure
    mock_post_status_comment.assert_called_once()
    mock_jira.close.assert_called_once()
    assert result["current_node"] == "human_review_gate"
    assert "last_error" not in result or result["last_error"] is None


@pytest.mark.asyncio
async def test_ai_review_closes_jira_client_on_exception():
    """Test that JiraClient is properly closed even when exception occurs."""
    # Arrange
    state = {
        "ticket_key": "AISOS-111",
        "current_pr_number": 222,
    }

    mock_jira = AsyncMock()
    mock_jira.close = AsyncMock()
    mock_post_status_comment = AsyncMock(side_effect=Exception("Some error"))

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert - JiraClient.close() should be called in finally block
    mock_jira.close.assert_called_once()
    assert result["current_node"] == "human_review_gate"


@pytest.mark.asyncio
async def test_ai_review_uses_ticket_key_from_state():
    """Test that ai_review uses the correct ticket_key from state."""
    # Arrange
    state = {
        "ticket_key": "CUSTOM-999",
        "current_pr_number": 123,
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock()

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert
    call_args = mock_post_status_comment.call_args
    assert call_args[0][1] == "CUSTOM-999"  # ticket_key argument
    assert result["ticket_key"] == "CUSTOM-999"


@pytest.mark.asyncio
async def test_ai_review_routes_to_human_review_gate():
    """Test that ai_review always routes to human_review_gate."""
    # Arrange
    state = {
        "ticket_key": "AISOS-333",
        "current_pr_number": 444,
        "some_other_field": "value",
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock()

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert
    assert result["current_node"] == "human_review_gate"
    assert result.get("some_other_field") == "value"  # Other state preserved


@pytest.mark.asyncio
async def test_ai_review_preserves_all_state_fields():
    """Test that ai_review preserves all existing state fields."""
    # Arrange
    state = {
        "ticket_key": "AISOS-555",
        "current_pr_number": 666,
        "pr_urls": ["https://github.com/org/repo/pull/666"],
        "workspace_path": "/path/to/workspace",
        "current_repo": "org/repo",
        "ci_status": "passed",
    }

    mock_jira = AsyncMock()
    mock_post_status_comment = AsyncMock()

    # Act
    with patch("forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira):
        with patch(
            "forge.workflow.nodes.ai_reviewer.post_status_comment",
            mock_post_status_comment,
        ):
            result = await ai_review(state)

    # Assert - all original fields preserved
    assert result["ticket_key"] == "AISOS-555"
    assert result["current_pr_number"] == 666
    assert result["pr_urls"] == ["https://github.com/org/repo/pull/666"]
    assert result["workspace_path"] == "/path/to/workspace"
    assert result["current_repo"] == "org/repo"
    assert result["ci_status"] == "passed"
    assert result["current_node"] == "human_review_gate"
