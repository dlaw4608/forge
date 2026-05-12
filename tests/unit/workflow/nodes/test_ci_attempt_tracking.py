"""Unit tests for CI attempt tracking (AISOS-654)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forge.workflow.nodes.ci_evaluator import evaluate_ci_status
from forge.workflow.feature.state import FeatureState


# ── Helpers ───────────────────────────────────────────────────────────────────


def create_mock_github_client():
    """Create a mock GitHub client with common methods."""
    client = MagicMock()
    client.get_pull_request = AsyncMock()
    client.get_check_runs = AsyncMock()
    client.close = AsyncMock()
    return client


def create_base_state(**kwargs) -> FeatureState:
    """Create a base workflow state with CI fields."""
    defaults = {
        "ticket_key": "TEST-123",
        "pr_urls": ["https://github.com/org/repo/pull/42"],
        "ci_fix_attempts": 0,
        "current_attempt": 0,
        "max_attempts": 3,
        "ci_status": None,
        "ci_failed_checks": [],
        "ci_skipped_checks": [],
        "current_repo": "org/repo",
    }
    defaults.update(kwargs)
    return FeatureState(**defaults)


# ── State Initialization Tests ────────────────────────────────────────────────


class TestCIAttemptTrackingStateFields:
    """Test that current_attempt and max_attempts fields exist in state."""

    def test_current_attempt_in_ci_integration_state(self):
        """current_attempt must be a field in CIIntegrationState."""
        from forge.workflow.base import CIIntegrationState
        assert "current_attempt" in CIIntegrationState.__annotations__

    def test_max_attempts_in_ci_integration_state(self):
        """max_attempts must be a field in CIIntegrationState."""
        from forge.workflow.base import CIIntegrationState
        assert "max_attempts" in CIIntegrationState.__annotations__

    def test_feature_state_initializes_current_attempt_to_zero(self):
        """Feature state should initialize current_attempt to 0."""
        from forge.workflow.feature.state import create_initial_feature_state
        state = create_initial_feature_state(ticket_key="TEST-1")
        assert state.get("current_attempt") == 0

    def test_feature_state_initializes_max_attempts_from_config(self):
        """Feature state should initialize max_attempts from config."""
        from forge.workflow.feature.state import create_initial_feature_state
        state = create_initial_feature_state(ticket_key="TEST-1")
        # Default config value is 5
        assert state.get("max_attempts") is not None
        assert isinstance(state.get("max_attempts"), int)

    def test_bug_state_initializes_current_attempt_to_zero(self):
        """Bug state should initialize current_attempt to 0."""
        from forge.workflow.bug.state import create_initial_bug_state
        state = create_initial_bug_state(ticket_key="TEST-2")
        assert state.get("current_attempt") == 0

    def test_bug_state_initializes_max_attempts_from_config(self):
        """Bug state should initialize max_attempts from config."""
        from forge.workflow.bug.state import create_initial_bug_state
        state = create_initial_bug_state(ticket_key="TEST-2")
        # Default config value is 5
        assert state.get("max_attempts") is not None
        assert isinstance(state.get("max_attempts"), int)


# ── Attempt Increment Tests ───────────────────────────────────────────────────


class TestCIAttemptIncrement:
    """Test that current_attempt increments before each fix attempt."""

    @pytest.mark.asyncio
    async def test_first_ci_failure_increments_attempt_to_one(self):
        """First CI failure should increment current_attempt from 0 to 1."""
        state = create_base_state(current_attempt=0, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        assert result["current_attempt"] == 1
        assert result["current_node"] == "attempt_ci_fix"

    @pytest.mark.asyncio
    async def test_second_ci_failure_increments_attempt_to_two(self):
        """Second CI failure should increment current_attempt from 1 to 2."""
        state = create_base_state(current_attempt=1, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        assert result["current_attempt"] == 2
        assert result["current_node"] == "attempt_ci_fix"

    @pytest.mark.asyncio
    async def test_third_ci_failure_increments_attempt_to_three(self):
        """Third CI failure should increment current_attempt from 2 to 3."""
        state = create_base_state(current_attempt=2, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        assert result["current_attempt"] == 3
        assert result["current_node"] == "attempt_ci_fix"


# ── Attempt Limit Validation Tests ────────────────────────────────────────────


class TestCIAttemptLimitValidation:
    """Test that current_attempt is validated against max_attempts."""

    @pytest.mark.asyncio
    async def test_attempt_at_max_limit_blocks_further_attempts(self):
        """When current_attempt equals max_attempts, no more attempts should be made."""
        state = create_base_state(current_attempt=3, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                with patch("forge.workflow.nodes.ci_evaluator.record_ci_fix_attempt") as mock_record:
                    result = await evaluate_ci_status(state)

        # Should not increment or route to attempt_ci_fix
        assert result["current_attempt"] == 3  # Unchanged
        assert result["current_node"] == "ci_evaluator"
        assert result["ci_status"] == "failed"
        assert "limit reached" in result["last_error"]

    @pytest.mark.asyncio
    async def test_attempt_exceeding_max_limit_blocks_further_attempts(self):
        """When current_attempt exceeds max_attempts, no more attempts should be made."""
        state = create_base_state(current_attempt=4, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                with patch("forge.workflow.nodes.ci_evaluator.record_ci_fix_attempt") as mock_record:
                    result = await evaluate_ci_status(state)

        # Should not increment or route to attempt_ci_fix
        assert result["current_attempt"] == 4  # Unchanged
        assert result["current_node"] == "ci_evaluator"
        assert result["ci_status"] == "failed"
        assert "limit reached" in result["last_error"]

    @pytest.mark.asyncio
    async def test_attempt_one_below_max_allows_final_attempt(self):
        """When current_attempt is one below max, one more attempt should be allowed."""
        state = create_base_state(current_attempt=2, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        # Should increment and route to attempt_ci_fix
        assert result["current_attempt"] == 3
        assert result["current_node"] == "attempt_ci_fix"
        assert result["ci_status"] == "fixing"


# ── Attempt Reset Tests ───────────────────────────────────────────────────────


class TestCIAttemptReset:
    """Test that current_attempt resets when workflow completes or succeeds."""

    @pytest.mark.asyncio
    async def test_current_attempt_resets_on_ci_success(self):
        """When CI passes, current_attempt should reset to 0."""
        state = create_base_state(current_attempt=2, max_attempts=3)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "success",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        assert result["current_attempt"] == 0
        assert result["current_node"] == "human_review_gate"
        assert result["ci_status"] == "passed"

    @pytest.mark.asyncio
    async def test_current_attempt_resets_on_workflow_completion(self):
        """When workflow completes (tasks complete), current_attempt should reset to 0."""
        from forge.workflow.nodes.human_review import complete_tasks
        
        state = create_base_state(
            current_attempt=2,
            implemented_tasks=["TASK-1", "TASK-2"],
        )

        with patch("forge.workflow.nodes.human_review.JiraClient") as mock_jira_class:
            mock_jira = MagicMock()
            mock_jira.transition_issue = AsyncMock()
            mock_jira.set_workflow_label = AsyncMock()
            mock_jira.close = AsyncMock()
            mock_jira_class.return_value = mock_jira

            result = await complete_tasks(state)

        assert result["current_attempt"] == 0
        assert result["tasks_completed"] is True


# ── Edge Case Tests ───────────────────────────────────────────────────────────


class TestCIAttemptEdgeCases:
    """Test edge cases for CI attempt tracking."""

    @pytest.mark.asyncio
    async def test_missing_current_attempt_defaults_to_zero(self):
        """If current_attempt is missing from state, it should default to 0."""
        state = create_base_state()
        # Remove current_attempt from state
        del state["current_attempt"]
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        # Should default to 0 and increment to 1
        assert result["current_attempt"] == 1

    @pytest.mark.asyncio
    async def test_missing_max_attempts_defaults_to_config_value(self):
        """If max_attempts is missing from state, it should default to 5."""
        state = create_base_state(current_attempt=0)
        # Remove max_attempts from state
        del state["max_attempts"]
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        # Should allow attempt since default is 5
        assert result["current_attempt"] == 1
        assert result["current_node"] == "attempt_ci_fix"

    @pytest.mark.asyncio
    async def test_max_attempts_one_allows_single_attempt(self):
        """When max_attempts is 1, only one attempt should be allowed."""
        state = create_base_state(current_attempt=0, max_attempts=1)
        
        github = create_mock_github_client()
        github.get_pull_request.return_value = {"head": {"sha": "abc123"}}
        github.get_check_runs.return_value = [
            {
                "name": "test",
                "status": "completed",
                "conclusion": "failure",
                "output": {},
                "html_url": "https://github.com/org/repo/runs/1",
            }
        ]

        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                result = await evaluate_ci_status(state)

        # Should allow first attempt
        assert result["current_attempt"] == 1
        assert result["current_node"] == "attempt_ci_fix"

        # Second failure should block
        state2 = create_base_state(current_attempt=1, max_attempts=1)
        with patch("forge.workflow.nodes.ci_evaluator.GitHubClient", return_value=github):
            with patch("forge.workflow.nodes.ci_evaluator.get_settings") as mock_settings:
                mock_settings.return_value.ci_fix_max_retries = 5
                mock_settings.return_value.ignored_ci_checks = ["tide"]
                with patch("forge.workflow.nodes.ci_evaluator.record_ci_fix_attempt"):
                    result2 = await evaluate_ci_status(state2)

        assert result2["current_attempt"] == 1  # Unchanged
        assert result2["current_node"] == "ci_evaluator"
        assert result2["ci_status"] == "failed"


# ── CI Fix Attempt Status Comment Tests ───────────────────────────────────────


class TestCIFixAttemptCommentFormatting:
    """Test CI fix attempt comment formatting with various attempt counts."""

    @pytest.mark.asyncio
    async def test_first_attempt_comment_shows_1_of_max(self):
        """First attempt should show '1/{max_attempts}' in status comment."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=1,
            max_attempts=3,
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify comment posted with correct format
        assert mock_jira.add_comment.call_count == 1
        call_args = mock_jira.add_comment.call_args
        assert call_args[0][0] == "TEST-123"  # ticket_key
        assert call_args[0][1] == "🔧 CI checks failed. Analyzing failure and attempting fix (1/3)."

    @pytest.mark.asyncio
    async def test_second_attempt_comment_shows_2_of_max(self):
        """Second attempt should show '2/{max_attempts}' in status comment."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=2,
            max_attempts=3,
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify comment posted with correct format
        assert mock_jira.add_comment.call_count == 1
        call_args = mock_jira.add_comment.call_args
        assert call_args[0][0] == "TEST-123"  # ticket_key
        assert call_args[0][1] == "🔧 CI checks failed. Analyzing failure and attempting fix (2/3)."

    @pytest.mark.asyncio
    async def test_third_attempt_comment_shows_3_of_max(self):
        """Third attempt should show '3/{max_attempts}' in status comment."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=3,
            max_attempts=3,
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify comment posted with correct format
        assert mock_jira.add_comment.call_count == 1
        call_args = mock_jira.add_comment.call_args
        assert call_args[0][0] == "TEST-123"  # ticket_key
        assert call_args[0][1] == "🔧 CI checks failed. Analyzing failure and attempting fix (3/3)."


class TestCIFixAttemptCommentEdgeCases:
    """Test edge cases for CI fix attempt comment formatting."""

    @pytest.mark.asyncio
    async def test_final_attempt_edge_case_shows_max_of_max(self):
        """Final attempt edge case (when current_attempt == max_attempts) should show '{max}/{max}'."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=5,
            max_attempts=5,
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify comment shows '5/5' for final attempt
        assert mock_jira.add_comment.call_count == 1
        call_args = mock_jira.add_comment.call_args
        assert call_args[0][1] == "🔧 CI checks failed. Analyzing failure and attempting fix (5/5)."

    @pytest.mark.asyncio
    async def test_first_attempt_with_different_max_shows_1_of_custom_max(self):
        """First attempt with custom max_attempts (e.g., 5) should show '1/5'."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=1,
            max_attempts=5,  # Custom max_attempts
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify comment shows '1/5' with custom max
        assert mock_jira.add_comment.call_count == 1
        call_args = mock_jira.add_comment.call_args
        assert call_args[0][1] == "🔧 CI checks failed. Analyzing failure and attempting fix (1/5)."


class TestCIFixAttemptCommentErrorHandling:
    """Test error handling for CI fix attempt comment posting."""

    @pytest.mark.asyncio
    async def test_missing_current_attempt_logs_error_and_skips_comment(self, caplog):
        """When current_attempt is None, should log error and skip comment posting."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=None,  # Missing
            max_attempts=3,
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify no comment posted
        assert mock_jira.add_comment.call_count == 0
        
        # Verify JiraClient still closed (even though comment wasn't posted)
        assert mock_jira.close.call_count == 1
        
        # Verify error logged with diagnostic info
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        assert any("CI fix attempt values unavailable" in r.message for r in error_logs)
        assert any("current_attempt=None" in r.message for r in error_logs)

    @pytest.mark.asyncio
    async def test_missing_max_attempts_logs_error_and_skips_comment(self, caplog):
        """When max_attempts is None, should log error and skip comment posting."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=1,
            max_attempts=None,  # Missing
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify no comment posted
        assert mock_jira.add_comment.call_count == 0
        
        # Verify JiraClient still closed
        assert mock_jira.close.call_count == 1
        
        # Verify error logged with diagnostic info
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        assert any("CI fix attempt values unavailable" in r.message for r in error_logs)
        assert any("max_attempts=None" in r.message for r in error_logs)

    @pytest.mark.asyncio
    async def test_both_attempt_values_missing_logs_error_and_skips_comment(self, caplog):
        """When both current_attempt and max_attempts are None, should log error and skip comment."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=None,  # Missing
            max_attempts=None,  # Missing
        )

        mock_jira = MagicMock()
        mock_jira.add_comment = AsyncMock()
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                await attempt_ci_fix(state)

        # Verify no comment posted
        assert mock_jira.add_comment.call_count == 0
        
        # Verify error logged for both values
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        assert any("current_attempt=None" in r.message and "max_attempts=None" in r.message for r in error_logs)


class TestCIFixAttemptWorkflowContinuation:
    """Test that workflow continues after comment posting failures."""

    @pytest.mark.asyncio
    async def test_workflow_continues_after_comment_posting_failure(self):
        """Workflow should continue when comment posting fails (error suppressed by utility)."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=1,
            max_attempts=3,
        )

        mock_jira = MagicMock()
        # Simulate comment posting failure
        mock_jira.add_comment = AsyncMock(side_effect=Exception("Jira API error"))
        mock_jira.close = AsyncMock()

        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", return_value=mock_jira):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                # Should not raise exception - workflow continues
                                                result = await attempt_ci_fix(state)

        # Verify workflow continued (returned a result)
        assert result is not None
        
        # Verify JiraClient was still closed properly
        assert mock_jira.close.call_count == 1

    @pytest.mark.asyncio
    async def test_workflow_continues_after_jira_client_creation_failure(self):
        """Workflow should continue even if JiraClient creation fails."""
        from forge.workflow.nodes.ci_evaluator import attempt_ci_fix

        state = create_base_state(
            ci_failed_checks=[{"pr_url": "https://github.com/org/repo/pull/1", "name": "test", "conclusion": "failure"}],
            workspace_path="/tmp/workspace",
            current_attempt=1,
            max_attempts=3,
        )

        # Simulate JiraClient creation failure
        with patch("forge.workflow.nodes.ci_evaluator.JiraClient", side_effect=Exception("Cannot create Jira client")):
            with patch("forge.workflow.nodes.ci_evaluator.prepare_workspace", return_value=("/tmp/workspace", None)):
                with patch("forge.workflow.nodes.ci_evaluator._fetch_ci_logs_and_artifacts", AsyncMock()):
                    with patch("forge.workflow.nodes.ci_evaluator._collect_error_info", return_value="errors"):
                        with patch("forge.workflow.nodes.ci_evaluator.load_prompt", return_value="prompt"):
                            with patch("forge.workflow.nodes.ci_evaluator.ContainerRunner") as mock_runner:
                                mock_runner.return_value.run = AsyncMock()
                                with patch("forge.workflow.nodes.ci_evaluator.GitHubClient") as mock_gh:
                                    mock_gh.return_value.close = AsyncMock()
                                    with patch("pathlib.Path.mkdir"):
                                        with patch("pathlib.Path.write_text"):
                                            with patch("pathlib.Path.exists", return_value=False):
                                                # Should not raise exception - workflow continues
                                                result = await attempt_ci_fix(state)

        # Verify workflow continued (returned a result)
        assert result is not None
