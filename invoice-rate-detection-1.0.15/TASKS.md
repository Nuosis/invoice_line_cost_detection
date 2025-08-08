# Invoice Rate Detection System – Task Breakdown (Enhanced Scope)

> **This task list is based on the latest SOW and SCOPE documents. For full requirements, see `DEVELOPMENT_GUIDE.md`, `SOW.md`, and `SCOPE.md`.**

---

## Project Overview

- **Single-user, desktop CLI tool for invoice validation**
- **Master parts database (SQLite) with CRUD and audit trail**
- **PDF invoice processing with price and format validation**
- **Enhanced reporting and anomaly categorization**
- **Comprehensive documentation and test suite**

---

## Task Structure

Each task below is marked for either **Architect** (design/planning) or **Coder** (implementation). Dependencies and expected outcomes are specified.

**Status Legend:** ✅ Complete | 🚧 In Progress | ⏳ Pending

---

### 1. Database & Configuration

- **✅ [Architect] Design SQLite schema**
  - Tables: `parts`, `config`, `part_discovery_log`
  - Specify indexes, constraints, and relationships
  - _Outcome: Schema diagram and SQL migration script_
  - **COMPLETED:** Full schema design with comprehensive documentation in `docs/design/database_schema_design.md`

- **✅ [Coder] Implement database layer**
  - CRUD for parts (add, update, delete, list, get)
  - full db reset with cautions
  - Config management (read/write)
  - Part discovery logging
  - Backup/restore functionality
  - _Depends on: Schema design_
  - add database to gitignore
  - ensure database is self generating if not present when cli inits
  - ensure db persists in local env once initialized
  - **COMPLETED:** Full database implementation with models, utilities, migration system, and comprehensive tests

---

### 2. CLI Application

- **✅ [Architect] Define CLI command structure**
  - Commands for invoice processing, part management, import/export, backup/restore
  - build on what already exists
  - _Outcome: CLI command map/specification_
  - **COMPLETED:** Complete CLI specification with 25+ commands in `docs/design/cli_command_structure_design.md`

- **✅ [Coder] Implement CLI interface**
  - build on what already exists
  - Invoice processing: batch, interactive, collect/export unknown parts
  - Part management: CRUD, import/export, bulk update, stats, discovery log
  - Database management: backup/restore
  - _Depends on: CLI spec, database layer_
  - **COMPLETED:** Full CLI implementation with Click framework, comprehensive command structure, and integration tests

---

### 3. Invoice Processing & Validation

- **✅ [Architect] Specify validation logic**
  - Price validation (against master table)
  - Line count/format validation (SUBTOTAL, FREIGHT, TAX, TOTAL)
  - Anomaly classification (price, missing part, line count, format)
  - _Outcome: Validation flowchart and rules_
  - **COMPLETED:** Comprehensive validation specification with workflow, anomaly classification, and business rules in `docs/design/validation_logic_specification.md`

- **✅ [Coder] Implement PDF extraction and parsing**
  - Use `pdfplumber` for text extraction
  - Parse line items, totals, and metadata
  - _Depends on: Validation logic_
  - **COMPLETED:** Full PDF processing system with PDFProcessor class, data models, exception handling, and integration utilities

- **⏳ [Coder] Implement validation engine**
  - Price and format checks
  - Anomaly detection and categorization
  - Graceful error handling
  - _Depends on: Parsing, validation logic_

---

### 4. Reporting

- **✅ [Architect] Design report format**
  - CSV with invoice number, date, line item, rate, quantity, anomaly type/severity, description
  - maintain txt output as an option
  - Processing statistics and metrics
  - _Outcome: Report template_
  - **COMPLETED:** Complete report format specification with multiple report types and templates in `docs/design/report_format_specification.md`

- **⏳ [Coder] Implement report generation**
  - Write categorized anomalies and stats to CSV & txt
  - Support summary and detailed views
  - _Depends on: Validation engine_

---

### 5. Interactive Part Discovery

- **✅ [Coder] Implement interactive and batch part discovery**
  - Prompt user to add unknown parts during processing
  - Collect unknowns for later review
  - Log all discovery actions
  - _Depends on: CLI, database layer_
  - **COMPLETED:** Full interactive part discovery system with service class, prompts, CLI commands, comprehensive tests, configuration options, and complete documentation

---

### 6. Import/Export & Bulk Operations

- **✅ [Coder] Implement import/export for parts**
  - CSV import/export, bulk update
  - _Depends on: Database layer, CLI_
  - **COMPLETED:** Full bulk operations implementation with comprehensive CSV processing, bulk update/delete/activate operations, data transformations, column mapping, progress tracking, dry-run mode, extensive testing, and complete documentation

---

### 7. Documentation

- **[Coder/Documenter] Write user documentation**
  - Installation/setup guide
  - CLI command reference
  - User workflow and troubleshooting
  - Database schema documentation
  - _Depends on: CLI, database_

---

### 8. Testing

- **[Coder] Implement unit and integration tests**
  - >80% coverage for all core components
  - End-to-end workflow tests
  - Sample invoice data and coverage reports
  - _Depends on: All core features_

---

### 9. Packaging & Deployment

- **[Coder] Package application for Windows (and Mac/Linux if possible)**
  - Bundle dependencies, create ZIP/install script
  - _Depends on: All implementation tasks_

---

## Dependencies

- Database schema → Database layer → CLI → Validation/Processing → Reporting/Discovery → Docs/Tests → Packaging

---

## Key Principles

- **Clarity, maintainability, and user-friendliness prioritized**
- **No unnecessary complexity or post-processing**
- **All features must be accessible via CLI**

---

## Example CLI Commands

See `SCOPE.md` for full command list and usage examples.

---

## Acceptance Criteria

- All deliverables in SOW are met
- System processes sample invoices without errors
- Database and CLI operations perform as specified
- Documentation and test suite are complete and accurate
- >80% test coverage
