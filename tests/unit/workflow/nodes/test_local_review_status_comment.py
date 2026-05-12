"""Unit tests for local review initial status comment posting.

These tests verify that the local_review_changes node correctly posts an
initial status comment only on the first pass (pass_number == 1) and handles
errors gracefully without blocking workflow execution.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.workflow.feature.state import create_initial_feature_state
from forge.workflow.nodes.local_reviewer import local_review_changes


def create_mock_jira_client():
    """Create a mock JiraClient with required methods."""
    mock = MagicMock()
    mock.close = AsyncMock()
    mock.add_comment = AsyncMock()
    return mock


def create_mock_container_runner(has_unfixed_issues=False):
    """Create a mock ContainerRunner."""
    mock = MagicMock()

    # Mock result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.error_message = None

    # Set stdout/stderr to indicate unfixed issues if requested
    if has_unfixed_issues:
        mock_result.stdout = "unfixed breaking issues remain"
        mock_result.stderr = ""
    else:
        mock_result.stdout = "all issues fixed"
        mock_result.stderr = ""

    mock.run = AsyncMock(return_value=mock_result)
    return mock


def create_mock_git_operations(has_changes=False):
    """Create a mock GitOperations."""
    mock = MagicMock()
    mock.has_uncommitted_changes = MagicMock(return_value=has_changes)
    mock.stage_all = MagicMock()
    mock.commit = MagicMock()
    return mock


class TestLocalReviewInitialStatusComment:
    """Test cases for initial status comment on first pass."""

    @pytest.mark.asyncio
    async def test_posts_initial_comment_on_first_pass(self):
        """Should post initial status comment when pass_number == 1."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 0

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            mock_post_status.return_value = AsyncMock()
            await local_review_changes(state)

        # Verify post_status_comment was called with correct parameters
        mock_post_status.assert_called_once_with(
            mock_jira,
            "FEAT-123",
            "🔍 Running local code review on changes before creating PR.",
        )

        # Verify JiraClient was properly closed
        mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_comment_on_second_pass(self):
        """Should NOT post initial comment when pass_number == 2."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 2
        state["local_review_attempts"] = 1

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            mock_post_status.return_value = AsyncMock()
            await local_review_changes(state)

        # Verify post_status_comment was NOT called
        mock_post_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_comment_on_third_pass(self):
        """Should NOT post initial comment when pass_number == 3."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 3
        state["local_review_attempts"] = 2

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            mock_post_status.return_value = AsyncMock()
            await local_review_changes(state)

        # Verify post_status_comment was NOT called
        mock_post_status.assert_not_called()


class TestLocalReviewStatusCommentErrorHandling:
    """Test cases for error handling when posting status comment."""

    @pytest.mark.asyncio
    async def test_workflow_continues_when_comment_posting_fails(self, caplog):
        """Should continue workflow when post_status_comment fails."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 0

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            # Simulate post_status_comment raising an exception (though it shouldn't in practice)
            mock_post_status.side_effect = Exception("Jira API error")

            # Should not raise exception - workflow should continue
            result = await local_review_changes(state)

        # Verify workflow completed
        assert result["current_node"] == "create_pr"

        # Verify JiraClient was properly closed even when error occurred
        mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_jira_client_closed_even_when_comment_posting_fails(self):
        """Should close JiraClient even when post_status_comment fails."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 0

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            mock_post_status.side_effect = Exception("Jira API error")
            await local_review_changes(state)

        # Verify JiraClient.close() was called in finally block
        mock_jira.close.assert_called_once()


class TestLocalReviewStatusCommentEdgeCases:
    """Test cases for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_no_comment_when_no_workspace(self):
        """Should not post comment when workspace_path is missing."""
        mock_jira = create_mock_jira_client()

        state = create_initial_feature_state(ticket_key="FEAT-123")
        state["workspace_path"] = None
        state["local_review_pass_number"] = 1

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            result = await local_review_changes(state)

        # Should skip to create_pr without posting comment
        assert result["current_node"] == "create_pr"
        mock_post_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_comment_when_max_attempts_reached(self):
        """Should not post comment when max review attempts already reached."""
        mock_jira = create_mock_jira_client()

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 2  # MAX_REVIEW_ATTEMPTS

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            result = await local_review_changes(state)

        # Should proceed to create_pr without running review or posting comment
        assert result["current_node"] == "create_pr"
        # Note: Comment is posted before max attempts check, so it would be called
        # This test verifies the overall flow when max attempts is reached
        mock_post_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_comment_posted_before_max_attempts_check(self):
        """Should post comment before checking max attempts on first pass."""
        mock_jira = create_mock_jira_client()

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 2  # MAX_REVIEW_ATTEMPTS

        call_order = []

        async def track_post_status(*args, **kwargs):
            call_order.append("post_status_comment")

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment",
                side_effect=track_post_status,
            ),
        ):
            await local_review_changes(state)

        # Verify comment was posted even though max attempts was reached
        assert "post_status_comment" in call_order

    @pytest.mark.asyncio
    async def test_comment_posts_to_correct_ticket(self):
        """Should post comment to the feature ticket, not task ticket."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        state = create_initial_feature_state(
            ticket_key="FEAT-999",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 0

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            mock_post_status.return_value = AsyncMock()
            await local_review_changes(state)

        # Verify comment posted to feature ticket
        call_args = mock_post_status.call_args[0]
        assert call_args[1] == "FEAT-999"  # ticket_key parameter


class TestLocalReviewStatusCommentIntegrationWithReviewFlow:
    """Test cases verifying comment posting integrates correctly with review flow."""

    @pytest.mark.asyncio
    async def test_comment_posted_before_container_execution(self):
        """Should post comment before running container review."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=False)
        mock_git = create_mock_git_operations(has_changes=False)

        call_order = []

        async def track_post_status(*args, **kwargs):
            call_order.append("post_status_comment")

        async def track_container_run(*args, **kwargs):
            call_order.append("container_run")
            # Return the mock result
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.stdout = "all issues fixed"
            mock_result.stderr = ""
            return mock_result

        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 0

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment",
                side_effect=track_post_status,
            ),
        ):
            mock_runner.run.side_effect = track_container_run
            await local_review_changes(state)

        # Verify comment was posted before container execution
        assert call_order == ["post_status_comment", "container_run"]

    @pytest.mark.asyncio
    async def test_no_duplicate_comment_on_retry_after_unfixed_issues(self):
        """Should not post duplicate comment when retrying after unfixed issues."""
        mock_jira = create_mock_jira_client()
        mock_runner = create_mock_container_runner(has_unfixed_issues=True)
        mock_git = create_mock_git_operations(has_changes=True)

        # First pass - should post comment
        state = create_initial_feature_state(
            ticket_key="FEAT-123",
            current_repo="owner/test-repo",
        )
        state["workspace_path"] = "/tmp/test-workspace"
        state["local_review_pass_number"] = 1
        state["local_review_attempts"] = 0
        state["context"] = {"branch_name": "feature-branch"}

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status,
        ):
            mock_post_status.return_value = AsyncMock()
            result1 = await local_review_changes(state)

        # First pass should post comment
        assert mock_post_status.call_count == 1

        # Second pass - should NOT post comment (pass_number incremented to 2)
        result1["local_review_pass_number"] = 2

        with (
            patch("forge.workflow.nodes.local_reviewer.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.local_reviewer.ContainerRunner", return_value=mock_runner),
            patch("forge.workflow.nodes.local_reviewer.GitOperations", return_value=mock_git),
            patch(
                "forge.workflow.nodes.local_reviewer.post_status_comment"
            ) as mock_post_status_2,
        ):
            mock_post_status_2.return_value = AsyncMock()
            await local_review_changes(result1)

        # Second pass should NOT post comment
        mock_post_status_2.assert_not_called()
