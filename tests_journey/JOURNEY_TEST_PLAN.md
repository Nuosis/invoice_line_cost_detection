# Journey Test Files - Required Test Coverage

## Critical Journey Test Files (Each with Distinct Concern)

**🔍 EMPHASIS ON DATA VALIDATION**: All journey tests must use realistic, valid data that matches actual system requirements to ensure proper validation engine behavior and real-world accuracy.

### 1. `test_path_input_prompts.py`
**Concern**: Path input handling and PathWithMetadata object creation
**Why Critical**: Would have caught the AttributeError bug we just fixed
**Data Validation Requirements**: Use actual PDF files with known parts in test database
**Tests**:
- Single file selection creates PathWithMetadata correctly
- Directory selection works with regular Path objects
- Invalid path handling and retry flows
- Path escaping (spaces, quotes, backslashes)
- Cross-platform path compatibility

### 2. `test_interactive_command_workflows.py`
**Concern**: Complete `invoice interactive` command user journey
**Why Critical**: Tests the full interactive workflow end-to-end
**Data Validation Requirements**: Use complete parts database with all PDF parts (GP0171NAVY, GS0448NAVY, GS3125NAVY, GP1390NAVY)
**Tests**:
- Complete interactive processing workflow
- User choice flows (single file vs batch)
- Output format selection
- Validation mode selection
- Error recovery in interactive mode

### 3. `test_choice_selection_prompts.py`
**Concern**: All `prompt_for_choice()` interactions
**Why Critical**: Tests user decision-making flows
**Tests**:
- Multiple choice selections
- Default choice handling
- Invalid choice recovery
- Choice validation and processing
- Menu display and user experience

### 4. `test_confirmation_dialogs.py`
**Concern**: All `click.confirm()` interactions
**Why Critical**: Tests user confirmation flows
**Tests**:
- File overwrite confirmations
- Retry confirmations after errors
- Process continuation confirmations
- Default value handling
- User cancellation flows

### 5. `test_parts_discovery_prompts.py`
**Concern**: Interactive parts discovery user flows
**Why Critical**: Tests complex multi-step user interactions
**Tests**:
- Unknown part discovery prompts
- Part addition workflows
- Batch part review flows
- Price entry and validation
- Discovery session management

### 6. `test_error_recovery_journeys.py`
**Concern**: Error scenarios and user recovery paths
**Why Critical**: Tests graceful error handling and user guidance
**Tests**:
- Invalid file path recovery
- Permission error handling
- Database error recovery
- User cancellation handling
- Retry mechanisms

### 7. `test_output_configuration_prompts.py`
**Concern**: Output path and format selection
**Why Critical**: Tests file output user experience
**Tests**:
- Output path prompts
- Format selection (CSV, TXT, JSON)
- Directory creation prompts
- File overwrite handling
- Path validation

### 8. `test_validation_mode_selection.py`
**Concern**: Validation mode and threshold configuration
**Why Critical**: Tests core business logic configuration
**Tests**:
- Parts-based vs threshold-based selection
- Threshold value entry and validation
- Mode-specific prompt flows
- Configuration persistence
- Default value handling

### 9. `test_user_cancellation_flows.py`
**Concern**: Ctrl+C and explicit cancellation handling
**Why Critical**: Tests graceful exit and cleanup
**Tests**:
- Ctrl+C during prompts
- Explicit "Cancel" choices
- Cleanup after cancellation
- State preservation/rollback
- Error message clarity

### 10. `test_multi_step_workflow_state.py`
**Concern**: State preservation across multiple prompts
**Why Critical**: Tests workflow continuity and data consistency
**Tests**:
- State preservation between prompts
- Data flow from input to processing
- Workflow step validation
- Progress indication
- Step-by-step error recovery

## Test Execution Strategy

### Priority Order (Implement in this order):
1. **`test_path_input_prompts.py`** - Would have caught our bug ✅ **IMPLEMENTED**
2. **`test_interactive_command_workflows.py`** - Core user experience
3. **`test_error_recovery_journeys.py`** - Critical for user experience
4. **`test_choice_selection_prompts.py`** - Common interaction pattern
5. **`test_confirmation_dialogs.py`** - Common interaction pattern
6. **`test_parts_discovery_prompts.py`** - Complex business workflow
7. **`test_output_configuration_prompts.py`** - File handling
8. **`test_validation_mode_selection.py`** - Business logic configuration
9. **`test_user_cancellation_flows.py`** - Edge case handling
10. **`test_multi_step_workflow_state.py`** - Advanced workflow testing

### Established Testing Pattern (from test_interactive_command_workflows.py):

#### Test Structure Pattern:
1. **Complexity-Based Ordering**: Tests ordered from most fundamental to most complex
2. **Comprehensive Mocking**: Mock ALL user interactions, use REAL system components
3. **Real Data Testing**: Use actual PDF files (5790265786.pdf) from original bug report
4. **Status Tracking**: Each test documents its verification status in docstring
5. **Issue Documentation**: Problems are documented with investigation steps

#### Test Verification Levels:
- ✅ **VERIFIED PASSING**: Test runs successfully, all assertions pass
- ⚠️ **NEEDS INVESTIGATION**: Test has proper mocking but encounters system issues
- ❌ **FAILING**: Test fails due to implementation or mocking issues
- 🔄 **IN PROGRESS**: Test verification currently underway
- ⏳ **PENDING**: Test not yet verified

#### Mocking Strategy (Proven Pattern):
```python
# Mock ALL user interactions
with patch('cli.prompts.show_welcome_message') as mock_welcome, \
     patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
     patch('cli.prompts.prompt_for_output_format') as mock_output_format, \
     patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
     patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
     patch('cli.prompts.show_processing_summary') as mock_summary, \
     patch('cli.prompts.prompt_for_next_action') as mock_next_action, \
     patch('click.confirm') as mock_confirm, \
     patch('click.prompt') as mock_click_prompt:
    
    # Use REAL system components (database, file system, validation engine)
    # Only mock user keyboard/mouse input
```

#### Real Data Integration:
- Use actual PDF files from `docs/invoices/5790265786.pdf`
- Create real temporary databases for each test with COMPLETE parts data
- Generate actual reports and validate content
- Test against real validation engine behavior

#### Data Validation Requirements (CRITICAL):
```python
# REQUIRED: Complete parts database setup for 5790265786.pdf
def setUp(self):
    # Add ALL parts found in the actual PDF
    self.db_manager.add_part("GP0171NAVY", "PANT WORK DURAPRES COTTON", 25.50)
    self.db_manager.add_part("GS0448NAVY", "SHIRT WORK LS BTN COTTON", 18.75)
    self.db_manager.add_part("GS3125NAVY", "SHIRT SCRUB USS", 22.00)
    self.db_manager.add_part("GP1390NAVY", "PANT SCRUB COTTON", 24.25)
    
    # ValidationEngine will now find all parts and process successfully
    # This prevents "unknown parts" errors that mask real issues
```

#### Why Data Validation is Essential:
- **Prevents false negatives**: Invalid test data can cause tests to fail for wrong reasons
- **Exposes real bugs**: Proper data validation helps identify legitimate system issues
- **Matches user reality**: Tests should reflect actual user scenarios with valid data
- **Validates system integrity**: Ensures validation engine works correctly with real data

### Coverage Goals:
- **100% of interactive prompts** must have journey tests
- **All user input validation paths** must be tested
- **All error recovery flows** must be tested
- **All multi-step workflows** must be tested

### Success Metrics:
- Tests catch CLI interface bugs before deployment
- Tests provide clear feedback on user experience issues
- Tests execute reliably across different environments
- Tests prevent regressions in user interaction flows

## Implementation Notes

### Strategic Mocking Policy:
- ✅ **Mock ONLY user input**: `@patch('click.prompt')`, `@patch('click.confirm')`
- ❌ **DO NOT mock system components**: Database, file system, processing logic

### Test Structure:
- Each file focuses on ONE specific concern
- Tests use real databases and file systems
- Tests simulate only user keyboard/mouse input
- Tests validate both user experience AND system state

### Resource Management:
- Each test creates unique temporary resources
- Each test cleans up ALL created resources
- Tests use UUIDs to prevent conflicts
- Tests handle cross-platform differences

---

**This test plan addresses the critical gap that allowed the PathWithMetadata bug to slip through our existing test coverage.**