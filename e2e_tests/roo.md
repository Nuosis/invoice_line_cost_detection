# End-to-End Testing Rules and Guidelines

## Core Testing Principles

### NO MOCKING POLICY
- **MOCKING IS STRICTLY PROHIBITED** in all e2e tests
- Tests must use real database connections, file systems, and external dependencies
- All interactions must be with actual system components, not mocked versions
- This ensures tests validate real-world behavior and catch integration issues

### Test Isolation and Cleanup
- **Each test suite MUST create all necessary files and resources it needs**
- **Each test suite MUST clean up ALL resources it creates**
- Tests must not depend on external state or leave artifacts behind
- Database files, temporary directories, and test data must be properly managed
- Use unique identifiers (UUIDs, timestamps) to avoid conflicts between parallel test runs

### Resource Management
- **Database Files**: Each test must create its own database file with unique naming
- **Temporary Files**: Use system temp directories with proper cleanup
- **Test Data**: Generate test data programmatically rather than relying on external files
- **File Permissions**: Ensure proper file permissions for cross-platform compatibility

## Test Structure Requirements

### Test Suite Organization
- Each test suite focuses on a specific functional area (e.g., Initial Database Setup)
- Test methods should be atomic and independent
- Use descriptive test names that clearly indicate what is being tested
- Group related tests using test classes or modules

### Setup and Teardown
- **setUp/setUpClass**: Create necessary test resources (databases, directories, etc.)
- **tearDown/tearDownClass**: Clean up ALL created resources without exception
- Use context managers where appropriate for automatic cleanup
- Implement robust error handling in cleanup code to prevent resource leaks

### Test Data Management
- Generate test data programmatically using factories or builders
- Use realistic but deterministic test data
- Avoid hardcoded paths or system-specific assumptions
- Create test data that covers edge cases and boundary conditions

## Database Testing Specific Rules

### Database File Management
- Each test must use a unique database file path
- Database files must be created in temporary directories
- All database connections must be properly closed
- Database files must be deleted after test completion

### Schema and Data Validation
- Verify database schema matches expected structure
- Validate that all required tables, indexes, and constraints exist
- Test default data insertion and retrieval
- Verify foreign key constraints and data integrity rules

### Transaction Testing
- Test both successful and failed transactions
- Verify rollback behavior on errors
- Test concurrent access scenarios where applicable
- Validate connection pooling and resource management

## Error Handling and Edge Cases

### Comprehensive Error Testing
- Test all error conditions and exception paths
- Verify proper error messages and logging
- Test recovery from various failure scenarios
- Validate graceful degradation when possible

### Boundary Conditions
- Test with empty databases and missing files
- Test with corrupted or invalid data
- Test with insufficient permissions or disk space
- Test with extremely large or small data sets

### Cross-Platform Compatibility
- Tests must work on Windows, macOS, and Linux
- Use platform-agnostic file paths and operations
- Handle platform-specific file system limitations
- Test with different Python versions where applicable

## Performance and Reliability

### Test Execution Time
- E2E tests may take longer than unit tests but should remain reasonable
- Optimize test data size while maintaining coverage
- Use efficient database operations and queries
- Implement timeouts for long-running operations

### Test Reliability
- Tests must be deterministic and repeatable
- Avoid race conditions and timing dependencies
- Handle system resource limitations gracefully
- Implement proper retry logic for flaky operations

## Documentation and Maintenance

### Test Documentation
- Each test suite must have clear documentation explaining its purpose
- Complex test scenarios should include inline comments
- Document any special setup requirements or dependencies
- Maintain up-to-date test coverage reports

### Test Maintenance
- Keep tests synchronized with code changes
- Update tests when database schema or business logic changes
- Remove obsolete tests and add new ones as features evolve
- Regular review and refactoring of test code for maintainability

## Execution Guidelines

### Running Tests
- Tests should be runnable individually or as part of a suite
- Provide clear instructions for test execution
- Support both local development and CI/CD environments
- Include test discovery and reporting mechanisms

### Continuous Integration
- Tests must pass consistently in CI/CD pipelines
- Handle environment differences between local and CI systems
- Provide clear failure reporting and debugging information
- Support parallel test execution where safe

## Additional Rules

### Security Considerations
- Do not include sensitive data in test files
- Use secure temporary file creation methods
- Clean up any potentially sensitive test data
- Follow security best practices for test environments

### Logging and Debugging
- Include appropriate logging for test execution
- Provide detailed error information for test failures
- Support debug mode for detailed test execution tracing
- Log resource creation and cleanup operations

### Version Control
- Do not commit temporary test files or databases
- Include proper .gitignore entries for test artifacts
- Keep test code under version control with proper history
- Document test changes in commit messages

---

**Remember: The goal of e2e tests is to validate that the entire system works correctly in real-world conditions. No shortcuts, no mocking, no compromises on cleanup.**