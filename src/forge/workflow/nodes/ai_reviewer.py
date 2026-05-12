"""AI code review node for automated PR analysis."""

import logging

from forge.integrations.jira.client import JiraClient
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.utils import update_state_timestamp
from forge.workflow.utils.jira_status import post_status_comment

logger = logging.getLogger(__name__)


async def ai_review(state: WorkflowState) -> WorkflowState:
    """Perform AI code review on PR after CI passes.

    This node:
    1. Posts status comment to Jira feature ticket
    2. Performs AI analysis of PR changes (TODO: implement review logic)
    3. Routes to human review

    Args:
        state: Current workflow state.

    Returns:
        Updated state after AI review.
    """
    ticket_key = state["ticket_key"]
    pr_number = state.get("current_pr_number")

    logger.info(f"Starting AI code review for {ticket_key}")

    # Post status comment to feature ticket when AI review begins
    # This provides visibility to users that AI review is in progress after CI passes
    jira = JiraClient()
    try:
        # Format message with PR number if available
        if pr_number is not None:
            message = f"🤖 CI checks passed. Running AI code review on PR #{pr_number}."
        else:
            # Fallback message when PR number unavailable (should not normally happen)
            message = "🤖 CI checks passed. Running AI code review."

        await post_status_comment(jira, ticket_key, message)
    finally:
        await jira.close()

    # TODO: Implement actual AI code review logic here
    # For now, this node posts the status comment and routes to human review
    # Future implementation will:
    # - Fetch PR diff and files changed
    # - Run AI analysis on code quality, security, spec alignment
    # - Post review comments or approval on GitHub PR
    # - Store review results in state (ai_review_status, ai_review_results)

    return update_state_timestamp(
        {
            **state,
            "current_node": "human_review_gate",
            "ai_review_status": "completed",  # Placeholder until actual review is implemented
        }
    )
