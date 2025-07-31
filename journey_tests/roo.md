# CLI User Journey Testing Rules and Guidelines

## Core Testing Philosophy

**Journey tests validate the complete user experience from CLI prompt to system response.**

These tests fill the critical gap between unit tests (isolated functions) and e2e tests (complete workflows) by focusing specifically on **user interaction flows** and **CLI interface behavior**.

## Quick Start

### Prerequisites
```bash
# Install test dependencies
uv sync --group dev
```

### Running Tests
```bash
# Run all journey tests
PYTHONPATH=. uv run python -m pytest journey_tests/ -v

# Run specific journey test
PYTHONPATH=. uv run python journey_tests/test_interactive_prompts.py

# Run with detailed output
PYTHONPATH=. uv run python -m pytest journey_tests/ -v -s
```

Real invoice PDFs for testing are available at `~/docs/invoices/`

---

## STRATEGIC MOCKING POLICY

### ✅ MOCK ONLY USER INPUT
- **Mock user typing**: `@patch('click.prompt')`
- **Mock user choices**: `@patch('click.confirm')`
- **Mock user selections**: `@patch('cli.prompts.prompt_for_choice')`

### ❌ DO NOT MOCK SYSTEM COMPONENTS
- **Database operations**: Use real SQLite databases
- **File system**: Use real files and directories
- **PDF processing**: Use real PDF processing
- **Validation logic**: Use real validation engines
- **CLI commands**: Use real command implementations

### Critical Distinction
```python
# ❌ BAD: Over-mocking undermines validity
@patch('database.DatabaseManager')
@patch('processing.PDFProcessor')
@patch('click.prompt')
def test_user_journey():
    # This doesn't test real interactions!

# ✅ GOOD: Strategic mocking preserves validity
@patch('click.prompt')  # Only mock what user types
@patch('click.confirm') # Only mock user decisions
def test_user_journey():
    # Real database, real processing, real validation
    # Only simulated: user keyboard input
```

---

## Test Isolation and Cleanup

### Resource Management
- **Each test MUST create unique temporary databases**
- **Each test MUST create unique temporary directories**
- **Each test MUST clean up ALL resources it creates**
- **Use UUIDs in file/database names to prevent conflicts**

### Setup Pattern
```python
def setUp(self):
    self.test_id = str(uuid.uuid4())[:8]
    self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_test_{self.test_id}_"))
    self.db_path = self.temp_dir / f"test_db_{self.test_id}.db"
    # Create real test resources...

def tearDown(self):
    # Clean up ALL created resources
    # Remove files, close connections, delete directories
```

---

## Journey Test Categories

### 1. Interactive Prompt Testing
**Purpose**: Test CLI prompt flows and user input handling
**Focus**: Path input, choice selection, confirmation dialogs
**Example**: Testing `prompt_for_input_path()` with various user inputs

### 2. Command Flow Testing  
**Purpose**: Test complete command execution with user interaction
**Focus**: Full CLI command workflows from start to finish
**Example**: Testing `invoice interactive` command end-to-end

### 3. Error Recovery Testing
**Purpose**: Test user error scenarios and recovery paths
**Focus**: Invalid input handling, retry mechanisms, graceful failures
**Example**: Testing invalid file paths, permission errors, user cancellation

### 4. Multi-Step Workflow Testing
**Purpose**: Test complex user journeys across multiple prompts
**Focus**: State preservation, workflow continuity, data consistency
**Example**: Testing complete interactive invoice processing workflow

---

## Test Structure Requirements

### Test Naming Convention
- `test_[user_action]_[expected_outcome]_[scenario]`
- Examples:
  - `test_single_file_selection_creates_metadata_object`
  - `test_invalid_path_input_prompts_retry_with_confirmation`
  - `test_user_cancellation_exits_gracefully_without_errors`

### Test Organization
```python
class TestInteractivePrompts(unittest.TestCase):
    """Test individual prompt functions and user input handling."""
    
class TestCommandWorkflows(unittest.TestCase):
    """Test complete CLI command workflows with user interaction."""
    
class TestErrorRecovery(unittest.TestCase):
    """Test error scenarios and user recovery paths."""
```

### Required Test Components
1. **Setup**: Create real test environment (database, files, directories)
2. **Mock Setup**: Configure user input simulation
3. **Execution**: Run the actual CLI function/command
4. **Validation**: Verify both user experience AND system state
5. **Cleanup**: Remove all created resources

---

## User Input Simulation Patterns

### Basic Prompt Simulation
```python
with patch('click.prompt') as mock_prompt:
    mock_prompt.return_value = "/path/to/test/file.pdf"
    result = prompt_for_input_path()
    # Verify result and system state
```

### Choice Selection Simulation
```python
with patch('cli.prompts.prompt_for_choice') as mock_choice:
    mock_choice.return_value = "Process only this file (test.pdf)"
    result = some_interactive_function()
    # Verify choice handling
```

### Multi-Step Interaction Simulation
```python
with patch('click.prompt') as mock_prompt, \
     patch('click.confirm') as mock_confirm, \
     patch('cli.prompts.prompt_for_choice') as mock_choice:
    
    # Simulate complete user journey
    mock_prompt.side_effect = ["/path/to/file.pdf", "report.csv"]
    mock_confirm.return_value = True
    mock_choice.return_value = "Process only this file"
    
    # Execute and verify
```

---

## Validation Requirements

### User Experience Validation
- **Verify correct prompts are shown to user**
- **Verify user choices are properly handled**
- **Verify error messages are clear and actionable**
- **Verify workflow progression is logical**

### System State Validation
- **Verify objects are created correctly (e.g., PathWithMetadata)**
- **Verify database operations execute properly**
- **Verify files are processed as expected**
- **Verify reports are generated correctly**

### Integration Validation
- **Verify prompt responses flow correctly to processing**
- **Verify user choices affect downstream behavior**
- **Verify error conditions are handled gracefully**
- **Verify cleanup occurs properly on cancellation**

---

## Error Handling and Edge Cases

### Required Error Scenarios
- **Invalid file paths**: Non-existent files, permission errors
- **Invalid user input**: Empty strings, invalid formats
- **User cancellation**: Ctrl+C, explicit cancellation choices
- **System errors**: Database failures, processing errors

### Error Testing Pattern
```python
def test_invalid_path_prompts_retry(self):
    with patch('click.prompt') as mock_prompt, \
         patch('click.confirm') as mock_confirm:
        
        # First attempt: invalid path
        # Second attempt: valid path
        mock_prompt.side_effect = ["/invalid/path", "/valid/path.pdf"]
        mock_confirm.return_value = True  # User chooses to retry
        
        result = prompt_for_input_path()
        
        # Verify retry behavior and final success
        self.assertEqual(mock_prompt.call_count, 2)
        self.assertTrue(result.exists())
```

---

## Cross-Platform Compatibility

### Path Handling
- **Test with both forward and backslashes**
- **Test with spaces in paths**
- **Test with special characters**
- **Test with very long paths**

### File System Operations
- **Test file creation and deletion**
- **Test directory operations**
- **Test permission scenarios**
- **Test case sensitivity differences**

---

## Performance and Reliability

### Test Execution Time
- **Journey tests should complete within reasonable time (< 30s each)**
- **Use efficient test data and minimal processing**
- **Implement timeouts for long-running operations**

### Test Reliability
- **Tests must be deterministic and repeatable**
- **Avoid race conditions and timing dependencies**
- **Handle system resource limitations gracefully**
- **Implement proper retry logic for flaky operations**

---

## Documentation and Maintenance

### Test Documentation
- **Each test must clearly document the user journey being tested**
- **Complex scenarios should include step-by-step comments**
- **Document any special setup requirements**
- **Maintain examples of expected user interactions**

### Maintenance Guidelines
- **Update tests when CLI prompts or flows change**
- **Add new tests for new interactive features**
- **Remove obsolete tests when features are removed**
- **Regular review of test coverage and effectiveness**

---

## Integration with Other Test Layers

### Relationship to Other Tests
- **Unit Tests**: Test individual functions in isolation
- **Journey Tests**: Test user interaction flows and CLI interface
- **E2E Tests**: Test complete business workflows without user interaction
- **Integration Tests**: Test component interactions

### Coverage Coordination
- **Journey tests focus on CLI interface and user experience**
- **E2E tests focus on business logic and system integration**
- **Avoid duplicating business logic testing in journey tests**
- **Focus on what makes journey tests unique: user interaction**

---

## Execution Guidelines

### Local Development
```bash
# Run journey tests during CLI development
PYTHONPATH=. uv run python -m pytest journey_tests/ -v

# Run specific test for debugging
PYTHONPATH=. uv run python journey_tests/test_interactive_prompts.py -v

# Run with output capture disabled for debugging
PYTHONPATH=. uv run python -m pytest journey_tests/ -v -s
```

### Continuous Integration
- **Journey tests must pass consistently in CI/CD**
- **Handle environment differences between local and CI**
- **Provide clear failure reporting and debugging information**
- **Support parallel execution where safe**

---

## Key Success Metrics

### Coverage Goals
- **All interactive CLI prompts must have journey tests**
- **All user input validation paths must be tested**
- **All error recovery flows must be tested**
- **All multi-step workflows must be tested**

### Quality Indicators
- **Tests catch CLI interface bugs before deployment**
- **Tests provide clear feedback on user experience issues**
- **Tests execute reliably across different environments**
- **Tests are maintainable and easy to understand**

---

## Examples of Critical Journey Tests

### Must-Have Test Cases
1. **Single file selection workflow** (would have caught PathWithMetadata bug)
2. **Interactive invoice processing complete workflow**
3. **Parts discovery and addition workflow**
4. **Error recovery and retry workflows**
5. **User cancellation and cleanup workflows**

### Test Scenarios That Prevent Regressions
- **Path input with various formats and edge cases**
- **Choice selection with different user preferences**
- **Multi-step workflows with state preservation**
- **Error conditions with proper user guidance**

---

**Remember: Journey tests are the bridge between "does the code work?" (unit/e2e tests) and "does the user experience work?" (manual testing). They catch the interface bugs that other test layers miss.**

---

**Quick Reference**: `PYTHONPATH=. uv run python -m pytest journey_tests/ -v`