# Forge Test Suite

This directory contains the comprehensive test suite for Forge, covering unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual modules
│   ├── workflow/            # Workflow-related unit tests
│   │   ├── nodes/           # Node-specific tests
│   │   └── test_*.py        # Workflow state and utility tests
│   └── ...
├── integration/             # Integration tests
│   ├── orchestrator/        # Orchestrator integration tests
│   ├── workflow/            # Workflow integration tests
│   └── ...
├── e2e/                     # End-to-end tests
├── conftest.py              # Shared fixtures and test configuration
└── README.md                # This file
```

## Running Tests

### Run all tests
```bash
uv run pytest
```

### Run specific test directories
```bash
# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# Specific test file
uv run pytest tests/unit/workflow/test_ai_review_status.py -v
```

### Run with coverage
```bash
uv run pytest --cov=src/forge --cov-report=html
```

## Conditional Test Execution

Some tests in this suite are **conditionally executed** based on the availability of workflow features. This allows tests to be committed and maintained alongside feature development but only run when the feature is ready.

### AI Review Node Tests

Tests for the `ai_review` workflow node are conditional on the node's availability. These tests will be automatically **skipped** with a clear message if the `ai_review` node is not yet implemented or not available in the workflow configuration.

**Affected test files:**
- `tests/unit/workflow/test_ai_review_status.py`
- `tests/unit/workflow/nodes/test_ai_review_status_comment.py`
- `tests/integration/workflow/test_ai_review_status_integration.py`

**How it works:**

1. **Automatic detection**: The test framework checks if the `ai_review` node can be imported from `forge.workflow.nodes`
2. **Skip behavior**: If the node is not available, all affected tests are skipped with the message:
   ```
   SKIPPED: ai_review node not yet implemented - tests will run when node is available
   ```
3. **Normal execution**: Once the node is implemented and exported, tests run normally

### Force-Enable Tests During Development

You can force tests to run even if automatic detection fails by setting an environment variable:

```bash
# Force-enable ai_review tests
export FORGE_ENABLE_AI_REVIEW_TESTS=1
uv run pytest tests/unit/workflow/test_ai_review_status.py -v

# Or inline:
FORGE_ENABLE_AI_REVIEW_TESTS=1 uv run pytest tests/unit/workflow/test_ai_review_status.py -v
```

This is useful when:
- Developing the feature and want to run tests before full integration
- Debugging test failures
- The automatic detection mechanism fails for some reason

### Adding Conditional Tests for New Features

To add conditional execution for a new feature's tests:

1. **Add detection function in `conftest.py`:**
   ```python
   def feature_name_node_available() -> bool:
       """Check if feature_name node is available."""
       # Check force-enable flag
       if os.environ.get("FORGE_ENABLE_FEATURE_NAME_TESTS", "").lower() in ("1", "true", "yes"):
           return True
       
       try:
           from forge.workflow.nodes import feature_name
           return feature_name is not None
       except (ImportError, AttributeError):
           return False
   ```

2. **Create skip marker:**
   ```python
   skip_if_feature_name_unavailable = pytest.mark.skipif(
       not feature_name_node_available(),
       reason="feature_name node not yet implemented - tests will run when node is available",
   )
   ```

3. **Apply to test files:**
   ```python
   from tests.conftest import skip_if_feature_name_unavailable
   
   @skip_if_feature_name_unavailable
   class TestFeatureName:
       # Tests here will be skipped if feature not available
       pass
   ```

## CI/CD Integration

The test suite is designed to work seamlessly in CI/CD pipelines:

- **Skipped tests don't fail the build**: pytest treats skipped tests as passing
- **Clear reporting**: CI logs show which tests were skipped and why
- **No false positives**: Only implemented features are tested
- **Easy activation**: Set environment variables in CI to force-enable tests when ready

### Example CI Configuration

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: uv run pytest
  env:
    # Enable AI review tests once feature is ready
    # FORGE_ENABLE_AI_REVIEW_TESTS: "1"
```

## Test Output Examples

### When ai_review node is NOT available:
```
tests/unit/workflow/test_ai_review_status.py::TestAIReviewStatusCommentOnEntry SKIPPED
tests/unit/workflow/test_ai_review_status.py::TestAIReviewCommentIncludesPRNumber SKIPPED
...

======================== 17 skipped in 0.12s ========================
Reason: ai_review node not yet implemented - tests will run when node is available
```

### When ai_review node IS available:
```
tests/unit/workflow/test_ai_review_status.py::TestAIReviewStatusCommentOnEntry::test_ai_review_posts_status_comment_on_entry PASSED
tests/unit/workflow/test_ai_review_status.py::TestAIReviewCommentIncludesPRNumber::test_ai_review_comment_includes_pr_number PASSED
...

======================== 17 passed in 2.34s ========================
```

## Best Practices

1. **Write tests alongside features**: Even if the feature isn't ready, commit the tests
2. **Document conditional execution**: Add clear notes in test docstrings
3. **Use descriptive skip messages**: Help developers understand why tests are skipped
4. **Test the skip mechanism**: Verify tests are actually skipped when expected
5. **Keep detection simple**: Use straightforward import checks for availability

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Forge Development Guidelines](../CLAUDE.md)
