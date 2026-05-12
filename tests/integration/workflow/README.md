# Workflow Integration Tests

This directory contains end-to-end integration tests for workflow status updates across PR creation and CI fix attempt scenarios.

## Test Files

### test_pr_ci_status_updates.py

Integration tests for PR creation and CI fix attempt status updates.

**Purpose**: Verify that Jira status comments and label transitions work correctly end-to-end for PR creation and CI fix attempts.

**Test Scenarios**:

1. **TS-006: PR creation posts comment with PR number and updates labels**
   - `test_pr_creation_posts_comment_with_pr_number`: Verifies "🚀 Pull request #123 created and submitted. Waiting for CI checks to complete." is posted
   - `test_pr_creation_removes_implementing_label`: Verifies forge:implementing label removed from feature ticket
   - `test_pr_creation_adds_ci_pending_label`: Verifies forge:ci-pending label added to feature ticket
   - `test_pr_creation_jira_client_properly_closed`: Verifies JiraClient properly closed after operations

2. **TS-007: CI fix attempts post comments with correct attempt counts**
   - `test_first_attempt_posts_comment_with_1_of_3`: Verifies first attempt posts "🔧 CI checks failed. Analyzing failure and attempting fix (1/3)."
   - `test_second_attempt_posts_comment_with_2_of_3`: Verifies second attempt posts "2/3" format
   - `test_third_attempt_posts_comment_with_3_of_3`: Verifies third/final attempt posts "3/3" format

3. **TS-014: Comment uses fallback text when PR number unavailable**
   - `test_pr_creation_posts_fallback_comment_without_pr_number`: Verifies "🚀 Pull request created and submitted. Waiting for CI checks to complete." is posted when PR number is None
   - `test_pr_creation_without_pr_number_still_updates_labels`: Verifies label transitions still occur when PR number unavailable

4. **Error Handling**
   - `test_workflow_continues_when_pr_comment_posting_fails`: Verifies workflow continues when PR creation comment posting fails
   - `test_workflow_continues_when_label_removal_fails`: Verifies workflow continues when label removal fails
   - `test_workflow_continues_when_ci_attempt_comment_posting_fails`: Verifies workflow continues when CI attempt comment posting fails

**Running the tests**:
```bash
uv run pytest tests/integration/workflow/test_pr_ci_status_updates.py -v
```

**Mock Strategy**:
- JiraClient is mocked to avoid external API calls
- ContainerRunner is mocked to simulate CI fix execution
- GitHubClient is mocked to avoid external GitHub API calls
- prepare_workspace and other workflow utilities are mocked to isolate status update logic
- Tests verify exact comment text matches specification
- Tests verify label transitions with correct ForgeLabel enums
- Tests verify workflow continues despite Jira failures (error suppression)

**Test Fixtures**:
- Uses fixtures from Epic AISOS-633 for Jira mocking patterns
- Mock helpers: `create_mock_jira_client()`, `create_mock_container_runner()`, `create_mock_github_client()`
- State creation via `create_initial_feature_state()` from `forge.workflow.feature.state`

### test_ai_review_status_integration.py

Integration tests for AI review status comment posting.

**Purpose**: Verify that Jira status comments are posted correctly when the ai_review node is entered after CI passes.

**Test Scenarios**:

1. **TS-012: AI review start posts comment to feature ticket**
   - `test_ai_review_posts_comment_with_pr_number`: Verifies "🤖 CI checks passed. Running AI code review on PR #456." is posted
   - `test_ai_review_posts_comment_with_different_pr_numbers`: Verifies PR number matches workflow state (tests PR #1, #9999)
   - `test_ai_review_posts_to_feature_ticket`: Verifies comment posts to feature ticket (ticket_key)
   - `test_ai_review_jira_client_properly_closed`: Verifies JiraClient properly closed after operations

2. **Fallback comment when PR number unavailable**
   - `test_ai_review_posts_fallback_comment_without_pr_number`: Verifies "🤖 CI checks passed. Running AI code review." when PR number is None
   - `test_ai_review_posts_fallback_when_pr_number_missing_from_state`: Verifies fallback when key missing from state

3. **Error Handling**
   - `test_workflow_continues_when_comment_posting_fails`: Verifies workflow continues when comment posting fails
   - `test_workflow_continues_when_jira_client_creation_fails`: Verifies behavior when JiraClient creation fails
   - `test_jira_client_closed_even_on_comment_failure`: Verifies JiraClient cleanup even on errors

4. **Conditional Execution**
   - `test_comment_posts_when_ai_review_node_entered`: Verifies comment posts when node is entered after CI passes
   - `test_no_duplicate_comments_on_node_re_entry`: Verifies behavior on hypothetical node re-entry

5. **State Preservation**
   - `test_ai_review_preserves_state_fields`: Verifies all state fields preserved except those updated by the node
   - `test_ai_review_sets_ai_review_status`: Verifies ai_review_status set to 'completed'

**Running the tests**:
```bash
uv run pytest tests/integration/workflow/test_ai_review_status_integration.py -v
```

**Mock Strategy**:
- JiraClient is mocked to avoid external API calls
- Tests verify exact comment text matches specification
- Tests verify workflow continues despite Jira failures (error suppression)
- Tests verify state preservation and updates

**Test Fixtures**:
- Mock helper: `create_mock_jira_client()`
- State creation via `create_initial_feature_state()` from `forge.workflow.feature.state`

## Related Tests

These integration tests complement:
- `/tests/integration/orchestrator/test_pr_creation_status_comments.py` - Original PR creation tests
- `/tests/integration/orchestrator/test_ci_fix_attempt_status_comments.py` - Original CI attempt tests
- `/tests/unit/workflow/test_pr_status_comments.py` - Unit tests for PR status comment logic
- `/tests/unit/workflow/nodes/test_ci_attempt_tracking.py` - Unit tests for CI attempt tracking
- `/tests/unit/workflow/test_ai_review_status.py` - Unit tests for AI review status comment logic
- `/tests/unit/workflow/nodes/test_ai_review_status_comment.py` - Unit tests for AI review status instrumentation
