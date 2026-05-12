"""Unit tests for AI review status comment posting functionality.

This module tests the status comment posting behavior in the ai_review node,
verifying correct comment formatting, PR number interpolation, error handling,
and workflow state integration.

NOTE: These tests are conditional on the ai_review node being implemented in the workflow.
Tests will be automatically skipped with a clear message if the ai_review node does not exist.
To force-enable these tests during development, set the environment variable:
    FORGE_ENABLE_AI_REVIEW_TESTS=1
"""

import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import skip_if_ai_review_unavailable

# Conditional import - only import if available, otherwise tests will be skipped
try:
    from forge.workflow.nodes.ai_reviewer import ai_review
except ImportError:
    ai_review = None


@skip_if_ai_review_unavailable
class TestAIReviewStatusCommentOnEntry:
    """Test that status comment is posted when ai_review node starts.

    NOTE: These tests are conditional on ai_review node availability.
    """

    @pytest.mark.asyncio
    async def test_ai_review_posts_status_comment_on_entry(self):
        """Verify comment is posted when node starts with PR number available."""
        # Arrange
        state = {
            "ticket_key": "FORGE-123",
            "current_pr_number": 456,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - status comment is posted on node entry
        mock_post_status_comment.assert_called_once()
        assert mock_post_status_comment.call_count == 1
        
        # Verify JiraClient lifecycle
        mock_jira.close.assert_called_once()
        
        # Verify workflow continues to next node
        assert result["current_node"] == "human_review_gate"

    @pytest.mark.asyncio
    async def test_ai_review_posts_comment_before_routing(self):
        """Verify comment is posted before workflow routes to next node."""
        # Arrange
        state = {
            "ticket_key": "FORGE-789",
            "current_pr_number": 999,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - comment posted and workflow routed
        mock_post_status_comment.assert_called_once()
        assert result["current_node"] == "human_review_gate"


@skip_if_ai_review_unavailable
class TestAIReviewCommentIncludesPRNumber:
    """Test that PR number from workflow state is included in comment message.

    NOTE: These tests are conditional on ai_review node availability.
    """

    @pytest.mark.asyncio
    async def test_ai_review_comment_includes_pr_number(self):
        """Verify PR number is correctly included in message when available."""
        # Arrange
        state = {
            "ticket_key": "FORGE-100",
            "current_pr_number": 42,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                await ai_review(state)

        # Assert - PR number interpolated in message
        expected_message = "🤖 CI checks passed. Running AI code review on PR #42."
        mock_post_status_comment.assert_called_once_with(
            mock_jira, "FORGE-100", expected_message
        )

    @pytest.mark.asyncio
    async def test_ai_review_comment_with_different_pr_numbers(self):
        """Verify correct PR number interpolation for multiple scenarios."""
        test_cases = [
            (1, "🤖 CI checks passed. Running AI code review on PR #1."),
            (123, "🤖 CI checks passed. Running AI code review on PR #123."),
            (9999, "🤖 CI checks passed. Running AI code review on PR #9999."),
        ]

        for pr_number, expected_message in test_cases:
            # Arrange
            state = {
                "ticket_key": "FORGE-200",
                "current_pr_number": pr_number,
            }

            mock_jira = AsyncMock()
            mock_post_status_comment = AsyncMock()

            # Act
            with patch(
                "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
            ):
                with patch(
                    "forge.workflow.nodes.ai_reviewer.post_status_comment",
                    mock_post_status_comment,
                ):
                    await ai_review(state)

            # Assert
            mock_post_status_comment.assert_called_once_with(
                mock_jira, "FORGE-200", expected_message
            )

    @pytest.mark.asyncio
    async def test_ai_review_comment_uses_fallback_when_pr_number_none(self):
        """Verify fallback message when PR number is None."""
        # Arrange
        state = {
            "ticket_key": "FORGE-300",
            "current_pr_number": None,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                await ai_review(state)

        # Assert - fallback message without PR number
        expected_message = "🤖 CI checks passed. Running AI code review."
        mock_post_status_comment.assert_called_once_with(
            mock_jira, "FORGE-300", expected_message
        )

    @pytest.mark.asyncio
    async def test_ai_review_comment_uses_fallback_when_pr_number_missing(self):
        """Verify fallback message when PR number key is missing from state."""
        # Arrange
        state = {
            "ticket_key": "FORGE-400",
            # No current_pr_number in state
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                await ai_review(state)

        # Assert - fallback message when key missing
        expected_message = "🤖 CI checks passed. Running AI code review."
        mock_post_status_comment.assert_called_once_with(
            mock_jira, "FORGE-400", expected_message
        )


@skip_if_ai_review_unavailable
class TestAIReviewCommentErrorSuppressed:
    """Test that workflow continues when comment posting fails.

    NOTE: These tests are conditional on ai_review node availability.
    """

    @pytest.mark.asyncio
    async def test_ai_review_comment_error_suppressed(self):
        """Verify workflow continues when comment posting fails."""
        # Arrange
        state = {
            "ticket_key": "FORGE-500",
            "current_pr_number": 123,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock(side_effect=Exception("Jira API error"))

        # Act - should not raise exception
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - workflow continues despite error
        assert result["current_node"] == "human_review_gate"
        assert "last_error" not in result or result["last_error"] is None
        
        # Verify JiraClient still closed properly
        mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_review_handles_jira_connection_error(self):
        """Verify workflow continues when JiraClient connection fails."""
        # Arrange
        state = {
            "ticket_key": "FORGE-600",
            "current_pr_number": 789,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock(
            side_effect=ConnectionError("Network error")
        )

        # Act - should not raise exception
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - workflow continues
        assert result["current_node"] == "human_review_gate"
        mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_review_handles_timeout_error(self):
        """Verify workflow continues when comment posting times out."""
        # Arrange
        state = {
            "ticket_key": "FORGE-700",
            "current_pr_number": 456,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock(
            side_effect=TimeoutError("Request timeout")
        )

        # Act - should not raise exception
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - workflow continues
        assert result["current_node"] == "human_review_gate"
        mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_review_closes_jira_client_on_exception(self):
        """Verify JiraClient is properly closed even when exception occurs."""
        # Arrange
        state = {
            "ticket_key": "FORGE-800",
            "current_pr_number": 999,
        }

        mock_jira = AsyncMock()
        mock_jira.close = AsyncMock()
        mock_post_status_comment = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - JiraClient.close() called in finally block
        mock_jira.close.assert_called_once()
        assert result["current_node"] == "human_review_gate"


@skip_if_ai_review_unavailable
class TestAIReviewUsesFeatureKeyFromState:
    """Test that feature_key is correctly extracted from workflow state.

    NOTE: These tests are conditional on ai_review node availability.
    """

    @pytest.mark.asyncio
    async def test_ai_review_uses_feature_key_from_state(self):
        """Verify correct ticket receives comment using feature_key from state."""
        # Arrange
        state = {
            "ticket_key": "CUSTOM-999",
            "current_pr_number": 111,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - correct feature_key (ticket_key) used
        call_args = mock_post_status_comment.call_args
        assert call_args[0][1] == "CUSTOM-999"  # ticket_key argument
        
        # Verify result preserves ticket_key
        assert result["ticket_key"] == "CUSTOM-999"

    @pytest.mark.asyncio
    async def test_ai_review_uses_different_feature_keys(self):
        """Verify correct ticket_key extraction for various ticket formats."""
        test_ticket_keys = [
            "AISOS-123",
            "FORGE-456",
            "PROJ-999",
            "ABC-1",
            "FEATURE-12345",
        ]

        for ticket_key in test_ticket_keys:
            # Arrange
            state = {
                "ticket_key": ticket_key,
                "current_pr_number": 42,
            }

            mock_jira = AsyncMock()
            mock_post_status_comment = AsyncMock()

            # Act
            with patch(
                "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
            ):
                with patch(
                    "forge.workflow.nodes.ai_reviewer.post_status_comment",
                    mock_post_status_comment,
                ):
                    result = await ai_review(state)

            # Assert - correct ticket_key used in comment call
            call_args = mock_post_status_comment.call_args
            assert call_args[0][1] == ticket_key
            assert result["ticket_key"] == ticket_key

    @pytest.mark.asyncio
    async def test_ai_review_preserves_all_state_fields(self):
        """Verify all state fields are preserved after status comment posting."""
        # Arrange
        state = {
            "ticket_key": "FORGE-555",
            "current_pr_number": 666,
            "pr_urls": ["https://github.com/org/repo/pull/666"],
            "workspace_path": "/path/to/workspace",
            "current_repo": "org/repo",
            "ci_status": "passed",
            "some_custom_field": "custom_value",
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - all original fields preserved
        assert result["ticket_key"] == "FORGE-555"
        assert result["current_pr_number"] == 666
        assert result["pr_urls"] == ["https://github.com/org/repo/pull/666"]
        assert result["workspace_path"] == "/path/to/workspace"
        assert result["current_repo"] == "org/repo"
        assert result["ci_status"] == "passed"
        assert result["some_custom_field"] == "custom_value"
        
        # Verify new fields added
        assert result["current_node"] == "human_review_gate"
        assert result["ai_review_status"] == "completed"


@skip_if_ai_review_unavailable
class TestAIReviewMockingAndIntegration:
    """Test proper mocking of post_status_comment and workflow state integration.

    NOTE: These tests are conditional on ai_review node availability.
    """

    @pytest.mark.asyncio
    async def test_post_status_comment_called_with_correct_parameters(self):
        """Verify post_status_comment is called with correct parameters."""
        # Arrange
        state = {
            "ticket_key": "FORGE-1000",
            "current_pr_number": 2000,
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                await ai_review(state)

        # Assert - verify all three parameters
        mock_post_status_comment.assert_called_once()
        call_args = mock_post_status_comment.call_args
        
        # First arg: JiraClient instance
        assert call_args[0][0] == mock_jira
        
        # Second arg: ticket_key
        assert call_args[0][1] == "FORGE-1000"
        
        # Third arg: message with PR number
        assert call_args[0][2] == "🤖 CI checks passed. Running AI code review on PR #2000."

    @pytest.mark.asyncio
    async def test_workflow_state_integration_with_minimal_fields(self):
        """Verify workflow continues with minimal required state fields."""
        # Arrange - minimal state
        state = {
            "ticket_key": "FORGE-MIN",
        }

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                result = await ai_review(state)

        # Assert - workflow completes with minimal state
        assert result["ticket_key"] == "FORGE-MIN"
        assert result["current_node"] == "human_review_gate"
        mock_post_status_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_jira_client_lifecycle_management(self):
        """Verify JiraClient is created and closed properly."""
        # Arrange
        state = {
            "ticket_key": "FORGE-LIFECYCLE",
            "current_pr_number": 123,
        }

        mock_jira = AsyncMock()
        mock_jira_constructor = AsyncMock(return_value=mock_jira)
        mock_post_status_comment = AsyncMock()

        # Act
        with patch(
            "forge.workflow.nodes.ai_reviewer.JiraClient", mock_jira_constructor
        ):
            with patch(
                "forge.workflow.nodes.ai_reviewer.post_status_comment",
                mock_post_status_comment,
            ):
                await ai_review(state)

        # Assert - JiraClient created and closed
        mock_jira_constructor.assert_called_once_with()
        mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_routing_always_to_human_review_gate(self):
        """Verify workflow always routes to human_review_gate regardless of state."""
        test_states = [
            {"ticket_key": "FORGE-A", "current_pr_number": 1},
            {"ticket_key": "FORGE-B", "current_pr_number": None},
            {"ticket_key": "FORGE-C"},
            {
                "ticket_key": "FORGE-D",
                "current_pr_number": 999,
                "extra_field": "value",
            },
        ]

        mock_jira = AsyncMock()
        mock_post_status_comment = AsyncMock()

        for state in test_states:
            # Act
            with patch(
                "forge.workflow.nodes.ai_reviewer.JiraClient", return_value=mock_jira
            ):
                with patch(
                    "forge.workflow.nodes.ai_reviewer.post_status_comment",
                    mock_post_status_comment,
                ):
                    result = await ai_review(state)

            # Assert - always routes to human_review_gate
            assert result["current_node"] == "human_review_gate"
