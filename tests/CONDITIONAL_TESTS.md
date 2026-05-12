# Conditional Test Execution for AI Review Node

## Overview

This document describes the conditional test execution implementation for the `ai_review` workflow node. Tests for this node are automatically skipped when the node is not available, allowing tests to be committed before the full feature implementation.

## Implementation Details

### Detection Mechanism

The conditional execution is implemented in `/workspace/tests/conftest.py`:

```python
def ai_review_node_available() -> bool:
    """Check if ai_review node is available in the workflow."""
    # 1. Check force-enable environment variable
    if os.environ.get("FORGE_ENABLE_AI_REVIEW_TESTS", "").lower() in ("1", "true", "yes"):
        return True
    
    # 2. Try to import ai_review from workflow nodes
    try:
        from forge.workflow.nodes import ai_review
        return ai_review is not None
    except (ImportError, AttributeError):
        return False
```

### Skip Marker

A pytest skip marker is defined for easy application to test classes and functions:

```python
skip_if_ai_review_unavailable = pytest.mark.skipif(
    not ai_review_node_available(),
    reason="ai_review node not yet implemented - tests will run when node is available",
)
```

### Affected Test Files

Three test files have been updated with conditional execution:

1. **`tests/unit/workflow/test_ai_review_status.py`**
   - 5 test classes with 17 total tests
   - All test classes decorated with `@skip_if_ai_review_unavailable`

2. **`tests/unit/workflow/nodes/test_ai_review_status_comment.py`**
   - 8 individual test functions
   - All functions decorated with `@skip_if_ai_review_unavailable`

3. **`tests/integration/workflow/test_ai_review_status_integration.py`**
   - 5 test classes with 13 total tests
   - All test classes decorated with `@skip_if_ai_review_unavailable`

## Usage

### Normal Test Execution

When the `ai_review` node is available (imported from `forge.workflow.nodes`):
```bash
pytest tests/unit/workflow/test_ai_review_status.py -v
# Tests run normally
```

When the `ai_review` node is NOT available:
```bash
pytest tests/unit/workflow/test_ai_review_status.py -v
# All tests are skipped with clear message
# SKIPPED: ai_review node not yet implemented - tests will run when node is available
```

### Force-Enable Tests

To force tests to run even if automatic detection indicates the node is unavailable:

```bash
# Environment variable approach
export FORGE_ENABLE_AI_REVIEW_TESTS=1
pytest tests/unit/workflow/test_ai_review_status.py -v

# Inline approach
FORGE_ENABLE_AI_REVIEW_TESTS=1 pytest tests/unit/workflow/test_ai_review_status.py -v
```

Valid values for the environment variable: `1`, `true`, `yes` (case-insensitive)

## CI/CD Integration

### Behavior in CI

- **Skipped tests don't fail builds**: pytest treats skipped tests as passing
- **Clear reporting**: CI logs show skip reason for each skipped test
- **Gradual activation**: Set `FORGE_ENABLE_AI_REVIEW_TESTS=1` in CI when ready

### Example GitHub Actions Configuration

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest tests/
        env:
          # Uncomment when ai_review node is ready for CI testing
          # FORGE_ENABLE_AI_REVIEW_TESTS: "1"
```

## Node Availability Criteria

The `ai_review` node is considered available when:

1. **Force-enable flag is set**: `FORGE_ENABLE_AI_REVIEW_TESTS` environment variable
2. **Import succeeds**: `from forge.workflow.nodes import ai_review` executes without error
3. **Node is not None**: The imported `ai_review` object is not None

If any of these conditions fail, tests are skipped.

## Implementation Pattern

This pattern can be reused for other workflow nodes:

```python
# In conftest.py
def feature_node_available() -> bool:
    if os.environ.get("FORGE_ENABLE_FEATURE_TESTS", "").lower() in ("1", "true", "yes"):
        return True
    try:
        from forge.workflow.nodes import feature_node
        return feature_node is not None
    except (ImportError, AttributeError):
        return False

skip_if_feature_unavailable = pytest.mark.skipif(
    not feature_node_available(),
    reason="feature_node not yet implemented - tests will run when node is available",
)

# In test files
from tests.conftest import skip_if_feature_unavailable

@skip_if_feature_unavailable
class TestFeature:
    pass
```

## Benefits

1. **Early test commitment**: Tests can be written and committed before full implementation
2. **No false failures**: CI doesn't fail on tests for unimplemented features
3. **Clear feedback**: Skip messages clearly explain why tests aren't running
4. **Easy activation**: Single environment variable enables tests when ready
5. **Automatic detection**: No manual configuration needed once feature is implemented
6. **Safe defaults**: Tests run automatically when node is available

## Troubleshooting

### Tests unexpectedly skipped

**Symptom**: Tests are skipped even though you expect them to run

**Solutions**:
1. Verify `ai_review` is exported in `/workspace/src/forge/workflow/nodes/__init__.py`
2. Check that `ai_review` can be imported: `python -c "from forge.workflow.nodes import ai_review; print(ai_review)"`
3. Force-enable: `FORGE_ENABLE_AI_REVIEW_TESTS=1 pytest ...`

### Tests unexpectedly running

**Symptom**: Tests run when you expect them to be skipped

**Solutions**:
1. Check if `FORGE_ENABLE_AI_REVIEW_TESTS` is set in environment
2. Verify the node is actually not available: `python -c "from forge.workflow.nodes import ai_review"` should fail
3. Clear any cached environment variables: `unset FORGE_ENABLE_AI_REVIEW_TESTS`

### Import errors in tests

**Symptom**: Tests fail with `NameError: name 'ai_review' is not defined`

**Cause**: The conditional import uses a try/except that sets `ai_review = None` on failure

**Solution**: This is expected when the node is unavailable. The `@skip_if_ai_review_unavailable` decorator should prevent the test from running. Ensure all test classes/functions are decorated.

## Related Documentation

- [Main Test README](./README.md) - Overall test suite documentation
- [Forge Development Guidelines](../CLAUDE.md) - Project development guidelines
- [pytest skip documentation](https://docs.pytest.org/en/stable/how-to/skipping.html)
