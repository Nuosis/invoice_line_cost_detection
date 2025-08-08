# Legacy System Removal Refactor Plan

**Date**: July 30, 2025  
**Objective**: Remove legacy `invoice_checker.py` system and consolidate on modern CLI architecture

## Overview

The project currently maintains two separate invoice processing systems:
1. **Legacy Script** (`invoice_checker.py`) - Monolithic, threshold-based processing
2. **Modern CLI System** (`cli/` modules) - Modular, parts-based validation with advanced features

This refactor will **eliminate the legacy system entirely** and focus solely on fixing and delivering the modern CLI system.

---

## Files to Remove

### 1. Legacy Script Files
- [ ] `invoice_checker.py` - Main legacy script (20,709 bytes)
- [ ] Any legacy-specific configuration or documentation references

### 2. Legacy Test Files
Review and remove unit tests that are specific to the legacy system:
- [ ] Tests in `unit_tests/` that import or test `invoice_checker.py` directly
- [ ] Legacy-specific test data or fixtures
- [ ] Duplicate test coverage that overlaps with modern CLI tests

### 3. Documentation References
- [ ] Remove legacy command examples from `docs/USER_MANUAL.md`
- [ ] Remove legacy system references from `docs/USER_FLOWS.md`
- [ ] Update `README.md` to remove legacy installation/usage instructions
- [ ] Update `.roo/rules/DEVELOPMENT_GUIDE.md` CLI examples

---

## Modern CLI System Fixes Required

### 1. Import Path Resolution
**Problem**: `ModuleNotFoundError: No module named 'cli'`

**Root Cause**: Package installation and import path issues

**Fix Steps**:
1. Ensure all module directories have proper `__init__.py` files:
   - `cli/__init__.py`
   - `processing/__init__.py` 
   - `database/__init__.py`

2. Verify `pyproject.toml` entry point configuration:
   ```toml
   [project.scripts]
   invoice-checker = "cli.main:main"
   ```

3. Install package in editable mode:
   ```bash
   pip install -e .
   ```

4. Test entry point:
   ```bash
   uv run invoice-checker --help
   ```

### 2. Module Structure Validation
Ensure the following files exist and are properly structured:
- [ ] `cli/main.py` with `main()` function
- [ ] `cli/commands/` with all command modules
- [ ] Proper imports between modules

### 3. Dependency Integration
Verify that the modern CLI system properly integrates:
- [ ] PDF processing (`processing/pdf_processor.py`)
- [ ] Database operations (`database/`)
- [ ] Validation engines (`processing/validation_engine.py`)

---

## Unit Test Simplification

### Tests to Remove/Consolidate

#### 1. Legacy-Specific Tests
Remove tests that directly test `invoice_checker.py`:
- [ ] `test_invoice_checker_main()` functions
- [ ] Legacy command-line argument parsing tests
- [ ] Legacy-specific PDF processing tests (if duplicated)

#### 2. Duplicate Coverage
Identify and remove duplicate test coverage:
- [ ] PDF processing tests that exist in both legacy and modern test suites
- [ ] Validation logic tests that are duplicated
- [ ] Report generation tests that overlap

#### 3. Tests to Refactor
Convert legacy-focused tests to modern CLI tests:
- [ ] Command-line interface tests → CLI command tests
- [ ] Integration tests → Modern workflow tests
- [ ] Error handling tests → Modern exception handling tests

### Tests to Keep/Enhance

#### 1. Core Functionality Tests
- [ ] `unit_tests/test_pdf_processing.py` - Core PDF extraction logic
- [ ] `unit_tests/test_validation_helpers.py` - Validation logic
- [ ] `unit_tests/test_database.py` - Database operations

#### 2. Modern CLI Tests
- [ ] `unit_tests/test_cli.py` - CLI command interface tests
- [ ] `unit_tests/test_interactive_functions.py` - Interactive discovery tests
- [ ] `unit_tests/test_bulk_operations.py` - Batch processing tests

#### 3. Integration Tests
- [ ] `unit_tests/test_invoice_processing_refactored.py` - End-to-end workflows
- [ ] `unit_tests/test_part_discovery.py` - Parts discovery workflows

---

## Configuration Updates

### 1. Package Configuration
Update `pyproject.toml`:
- [ ] Verify entry points are correct
- [ ] Ensure all required dependencies are listed
- [ ] Remove any legacy-specific configurations

### 2. Development Environment
- [ ] Update development scripts to use modern CLI
- [ ] Update CI/CD configurations (if any)
- [ ] Update development documentation

---

## Documentation Updates Required

### 1. User Documentation
- [ ] `docs/USER_MANUAL.md` - Remove all legacy command references
- [ ] `docs/USER_FLOWS.md` - Remove legacy system flows
- [ ] `README.md` - Update with modern CLI only

### 2. Developer Documentation
- [ ] Update architecture documentation
- [ ] Update development setup instructions
- [ ] Update testing documentation

### 3. Troubleshooting
- [ ] Remove legacy troubleshooting sections
- [ ] Focus troubleshooting on modern CLI import issues
- [ ] Update error handling documentation

---

## Migration Strategy

### Phase 1: Fix Modern CLI System
1. Resolve import path issues
2. Ensure all CLI commands work
3. Verify end-to-end functionality

### Phase 2: Remove Legacy Components
1. Delete `invoice_checker.py`
2. Remove legacy-specific tests
3. Clean up documentation

### Phase 3: Consolidate Tests
1. Remove duplicate test coverage
2. Enhance modern CLI test coverage
3. Ensure >80% test coverage maintained

### Phase 4: Final Validation
1. Full system testing
2. Documentation review
3. User acceptance testing

---

## Risk Mitigation

### Backup Strategy
- [ ] Create git branch before starting refactor
- [ ] Document current test coverage metrics
- [ ] Backup current working state

### Validation Checkpoints
- [ ] Verify modern CLI works after each major change
- [ ] Maintain test coverage above 80%
- [ ] Ensure all documented features are accessible

### Rollback Plan
- [ ] Keep legacy system in separate branch until refactor complete
- [ ] Document rollback procedures
- [ ] Test rollback process

---

## Success Criteria

### Functional Requirements
- [ ] Modern CLI system works without import errors
- [ ] All documented features are accessible via CLI
- [ ] End-to-end invoice processing works
- [ ] Interactive discovery functions properly

### Technical Requirements
- [ ] No legacy code remains in main branch
- [ ] Test coverage remains >80%
- [ ] No duplicate test coverage
- [ ] Clean, maintainable codebase

### Documentation Requirements
- [ ] All documentation references modern CLI only
- [ ] User manual provides working commands
- [ ] Troubleshooting focuses on actual issues
- [ ] Developer documentation is current

---

## Timeline Estimate

- **Phase 1** (Fix Modern CLI): 4-6 hours
- **Phase 2** (Remove Legacy): 2-3 hours  
- **Phase 3** (Consolidate Tests): 3-4 hours
- **Phase 4** (Final Validation): 2-3 hours

**Total Estimated Time**: 11-16 hours

---

## Notes

- This refactor eliminates technical debt from maintaining two systems
- Focuses development effort on the superior modern architecture
- Simplifies user experience with single, consistent interface
- Reduces maintenance burden and testing complexity
- Aligns with project goal of delivering production-ready system