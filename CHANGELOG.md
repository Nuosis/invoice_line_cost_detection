# Changelog

All notable changes to the Invoice Rate Detection System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.23] - 2025-08-20

### Removed
- auto_add_discovered_parts configuration and any auto-add behavior

### Changed
- Tests updated to remove any dependence on auto_add_discovered_parts
- Documentation updated to reflect that unknown parts are never auto-added; additions require explicit interactive confirmation
- Clarified CLI help text indicating "no auto-add" behavior across discovery flows

## [1.0.22] - 2025-08-08

### Changes

Modified files:
  - Modified: invoice-launcher.bat
  - Modified: invoice-launcher.sh

**Deployment:** 2025-08-08 14:41:49 MDT


## [1.0.21] - 2025-08-08

### Changes

Modified files:
  - Modified: cli/main.py
  - Modified: invoice-launcher.bat
  - Modified: invoice-launcher.sh

**Deployment:** 2025-08-08 14:26:28 MDT


## [1.0.20] - 2025-08-08

### Changes

Modified files:
  - Modified: cli/commands/invoice_commands.py
  - Modified: invoice-launcher.bat
  - Modified: invoice-launcher.sh
  - Modified: processing/invoice_processor.py
  - Modified: processing/part_discovery.py
  - Modified: processing/report_generator.py
  - Modified: processing/report_utils.py
New files:
  - Added: test_output_location_logic.py

**Deployment:** 2025-08-08 14:21:34 MDT


## [1.0.19] - 2025-08-08

### Changes

Modified files:
  - Modified: README.md
  - Modified: cli/commands/config_commands.py
  - Modified: cli/commands/database_commands.py
  - Modified: cli/commands/parts_commands.py
  - Modified: cli/context.py
  - Modified: cli/main.py
  - Modified: database/database.py
  - Modified: database/db_migration.py
  - Modified: database/models.py
  - Modified: invoice-launcher.bat
  - Modified: invoice-launcher.sh

**Deployment:** 2025-08-08 12:57:08 MDT


## [1.0.18] - 2025-08-08

### Changes

Modified files:
  - Modified: cli/main.py
  - Modified: invoice-launcher.bat

**Deployment:** 2025-08-08 11:21:41 MDT


## [1.0.17] - 2025-08-08

### Changes

Modified files:
  - Modified: invoice-launcher.bat
  - Modified: invoice-launcher.sh
  - Modified: invoice-rate-detection-1.0.15/.deployed
  - Modified: invoice-rate-detection-1.0.15/.deployment_info
  - Modified: invoice-rate-detection-1.0.15/.version
  - Modified: invoice-rate-detection-1.0.15/BULK_OPERATIONS_GUIDE.md
  - Modified: invoice-rate-detection-1.0.15/CHANGELOG.md
  - Modified: invoice-rate-detection-1.0.15/Clarity Invoice Validator.bat
  - Modified: invoice-rate-detection-1.0.15/Clarity Invoice Validator.command
  - Modified: invoice-rate-detection-1.0.15/ERROR_HANDLING_GUIDE.md
  - Modified: invoice-rate-detection-1.0.15/INTERACTIVE_PART_DISCOVERY.md
  - Modified: invoice-rate-detection-1.0.15/README.md
  - Modified: invoice-rate-detection-1.0.15/REFACTOR.md
  - Modified: invoice-rate-detection-1.0.15/REFACTOR_TODO.md
  - Modified: invoice-rate-detection-1.0.15/TASKS.md
  - Modified: invoice-rate-detection-1.0.15/USER_FLOWS.md
  - Modified: invoice-rate-detection-1.0.15/USER_MANUAL.md
  - Modified: invoice-rate-detection-1.0.15/Uninstaller.command
  - Modified: invoice-rate-detection-1.0.15/__init__.py
  - Modified: invoice-rate-detection-1.0.15/commands/__init__.py
  - Modified: invoice-rate-detection-1.0.15/commands/bulk_operations.py
  - Modified: invoice-rate-detection-1.0.15/commands/config_commands.py
  - Modified: invoice-rate-detection-1.0.15/commands/database_commands.py
  - Modified: invoice-rate-detection-1.0.15/commands/discovery_commands.py
  - Modified: invoice-rate-detection-1.0.15/commands/invoice_commands.py
  - Modified: invoice-rate-detection-1.0.15/commands/parts_commands.py
  - Modified: invoice-rate-detection-1.0.15/commands/utils_commands.py
  - Modified: invoice-rate-detection-1.0.15/context.py
  - Modified: invoice-rate-detection-1.0.15/database.py
  - Modified: invoice-rate-detection-1.0.15/db_migration.py
  - Modified: invoice-rate-detection-1.0.15/db_utils.py
  - Modified: invoice-rate-detection-1.0.15/deploy.sh
  - Modified: invoice-rate-detection-1.0.15/design/cli_command_structure_design.md
  - Modified: invoice-rate-detection-1.0.15/design/database_schema_design.md
  - Modified: invoice-rate-detection-1.0.15/design/report_format_specification.md
  - Modified: invoice-rate-detection-1.0.15/design/validation_logic_specification.md
  - Modified: invoice-rate-detection-1.0.15/error_handlers.py
  - Modified: invoice-rate-detection-1.0.15/error_solving/error_solving_prompt.md
  - Modified: invoice-rate-detection-1.0.15/error_solving/error_solving_template.md
  - Modified: invoice-rate-detection-1.0.15/error_solving/validation_engine_data_quality_error.md
  - Modified: invoice-rate-detection-1.0.15/exceptions.py
  - Modified: invoice-rate-detection-1.0.15/formatters.py
  - Modified: invoice-rate-detection-1.0.15/invoice-launcher.bat
  - Modified: invoice-rate-detection-1.0.15/invoice-launcher.sh
  - Modified: invoice-rate-detection-1.0.15/invoice_processor.py
  - Modified: invoice-rate-detection-1.0.15/invoices/5790265775.pdf
  - Modified: invoice-rate-detection-1.0.15/invoices/5790265776.pdf
  - Modified: invoice-rate-detection-1.0.15/invoices/5790265781.pdf
  - Modified: invoice-rate-detection-1.0.15/invoices/5790265785.pdf
  - Modified: invoice-rate-detection-1.0.15/invoices/5790265786.pdf
  - Modified: invoice-rate-detection-1.0.15/main.py
  - Modified: invoice-rate-detection-1.0.15/models.py
  - Modified: invoice-rate-detection-1.0.15/part_discovery.py
  - Modified: invoice-rate-detection-1.0.15/pdf_processor.py
  - Modified: invoice-rate-detection-1.0.15/progress.py
  - Modified: invoice-rate-detection-1.0.15/project/SCOPE.md
  - Modified: invoice-rate-detection-1.0.15/project/SOW.md
  - Modified: invoice-rate-detection-1.0.15/project/SOW.pdf
  - Modified: invoice-rate-detection-1.0.15/project/Safety_Supply_Proposal.pdf
  - Modified: invoice-rate-detection-1.0.15/prompts.py
  - Modified: invoice-rate-detection-1.0.15/pyproject.toml
  - Modified: invoice-rate-detection-1.0.15/report_generator.py
  - Modified: invoice-rate-detection-1.0.15/report_utils.py
  - Modified: invoice-rate-detection-1.0.15/uv.lock
  - Modified: invoice-rate-detection-1.0.15/validation_engine.py
  - Modified: invoice-rate-detection-1.0.15/validation_helpers.py
  - Modified: invoice-rate-detection-1.0.15/validators.py
  - Modified: invoice-rate-detection-1.0.15/version.py
  - Modified: uv.lock

**Deployment:** 2025-08-08 11:18:21 MDT


## [1.0.16] - 2025-08-08

### Changes

Modified files:
  - Modified: cli/commands/config_commands.py
  - Modified: cli/commands/database_commands.py
  - Modified: cli/commands/parts_commands.py
  - Modified: cli/main.py
  - Modified: docs/USER_MANUAL.md

**Deployment:** 2025-08-08 10:51:43 MDT


## [1.0.15] - 2025-08-08

### Changes

New files:
  - Added: invoice-rate-detection-1.0.15.zip
  - Added: invoice-rate-detection-1.0.15/.deployed
  - Added: invoice-rate-detection-1.0.15/.deployment_info
  - Added: invoice-rate-detection-1.0.15/.version
  - Added: invoice-rate-detection-1.0.15/BULK_OPERATIONS_GUIDE.md
  - Added: invoice-rate-detection-1.0.15/CHANGELOG.md
  - Added: invoice-rate-detection-1.0.15/Clarity Invoice Validator.bat
  - Added: invoice-rate-detection-1.0.15/Clarity Invoice Validator.command
  - Added: invoice-rate-detection-1.0.15/ERROR_HANDLING_GUIDE.md
  - Added: invoice-rate-detection-1.0.15/INTERACTIVE_PART_DISCOVERY.md
  - Added: invoice-rate-detection-1.0.15/README.md
  - Added: invoice-rate-detection-1.0.15/REFACTOR.md
  - Added: invoice-rate-detection-1.0.15/REFACTOR_TODO.md
  - Added: invoice-rate-detection-1.0.15/TASKS.md
  - Added: invoice-rate-detection-1.0.15/USER_FLOWS.md
  - Added: invoice-rate-detection-1.0.15/USER_MANUAL.md
  - Added: invoice-rate-detection-1.0.15/Uninstaller.command
  - Added: invoice-rate-detection-1.0.15/__init__.py
  - Added: invoice-rate-detection-1.0.15/commands/__init__.py
  - Added: invoice-rate-detection-1.0.15/commands/bulk_operations.py
  - Added: invoice-rate-detection-1.0.15/commands/config_commands.py
  - Added: invoice-rate-detection-1.0.15/commands/database_commands.py
  - Added: invoice-rate-detection-1.0.15/commands/discovery_commands.py
  - Added: invoice-rate-detection-1.0.15/commands/invoice_commands.py
  - Added: invoice-rate-detection-1.0.15/commands/parts_commands.py
  - Added: invoice-rate-detection-1.0.15/commands/utils_commands.py
  - Added: invoice-rate-detection-1.0.15/context.py
  - Added: invoice-rate-detection-1.0.15/database.py
  - Added: invoice-rate-detection-1.0.15/db_migration.py
  - Added: invoice-rate-detection-1.0.15/db_utils.py
  - Added: invoice-rate-detection-1.0.15/deploy.sh
  - Added: invoice-rate-detection-1.0.15/design/cli_command_structure_design.md
  - Added: invoice-rate-detection-1.0.15/design/database_schema_design.md
  - Added: invoice-rate-detection-1.0.15/design/report_format_specification.md
  - Added: invoice-rate-detection-1.0.15/design/validation_logic_specification.md
  - Added: invoice-rate-detection-1.0.15/error_handlers.py
  - Added: invoice-rate-detection-1.0.15/error_solving/error_solving_prompt.md
  - Added: invoice-rate-detection-1.0.15/error_solving/error_solving_template.md
  - Added: invoice-rate-detection-1.0.15/error_solving/validation_engine_data_quality_error.md
  - Added: invoice-rate-detection-1.0.15/exceptions.py
  - Added: invoice-rate-detection-1.0.15/formatters.py
  - Added: invoice-rate-detection-1.0.15/invoice-launcher.bat
  - Added: invoice-rate-detection-1.0.15/invoice-launcher.sh
  - Added: invoice-rate-detection-1.0.15/invoice_processor.py
  - Added: invoice-rate-detection-1.0.15/invoices/5790265775.pdf
  - Added: invoice-rate-detection-1.0.15/invoices/5790265776.pdf
  - Added: invoice-rate-detection-1.0.15/invoices/5790265781.pdf
  - Added: invoice-rate-detection-1.0.15/invoices/5790265785.pdf
  - Added: invoice-rate-detection-1.0.15/invoices/5790265786.pdf
  - Added: invoice-rate-detection-1.0.15/main.py
  - Added: invoice-rate-detection-1.0.15/models.py
  - Added: invoice-rate-detection-1.0.15/part_discovery.py
  - Added: invoice-rate-detection-1.0.15/pdf_processor.py
  - Added: invoice-rate-detection-1.0.15/progress.py
  - Added: invoice-rate-detection-1.0.15/project/SCOPE.md
  - Added: invoice-rate-detection-1.0.15/project/SOW.md
  - Added: invoice-rate-detection-1.0.15/project/SOW.pdf
  - Added: invoice-rate-detection-1.0.15/project/Safety_Supply_Proposal.pdf
  - Added: invoice-rate-detection-1.0.15/prompts.py
  - Added: invoice-rate-detection-1.0.15/pyproject.toml
  - Added: invoice-rate-detection-1.0.15/report_generator.py
  - Added: invoice-rate-detection-1.0.15/report_utils.py
  - Added: invoice-rate-detection-1.0.15/uv.lock
  - Added: invoice-rate-detection-1.0.15/validation_engine.py
  - Added: invoice-rate-detection-1.0.15/validation_helpers.py
  - Added: invoice-rate-detection-1.0.15/validators.py
  - Added: invoice-rate-detection-1.0.15/version.py

**Deployment:** 2025-08-08 10:27:36 MDT


## [1.0.14] - 2025-08-08

### Changes

Modified files:
  - Modified: README.md
  - Modified: cli/version.py
  - Modified: deploy.sh
  - Modified: invoice-launcher.sh

**Deployment:** 2025-08-08 10:27:22 MDT


## [1.0.13] - 2025-08-08

### Changes

Modified files:
  - Modified: .gitignore
  - Modified: README.md
  - Modified: cli/__init__.py
  - Modified: cli/commands/config_commands.py
  - Modified: cli/commands/database_commands.py
  - Modified: cli/commands/discovery_commands.py
  - Modified: cli/commands/invoice_commands.py
  - Modified: cli/commands/parts_commands.py
  - Modified: cli/main.py
  - Modified: database/database.py
  - Modified: database/db_migration.py
  - Modified: database/models.py
  - Modified: docs/USER_FLOWS.md
  - Modified: docs/USER_MANUAL.md
  - Modified: docs/invoices/5790265781.pdf
  - Modified: docs/invoices/5790265785.pdf
  - Modified: docs/invoices/output/5790265775_actual_output.txt
  - Modified: docs/invoices/output/5790265775_extracted_text.txt
  - Modified: docs/invoices/output/5790265775_line_items_CORRECTED_log.txt
  - Modified: docs/invoices/output/5790265775_line_items_WITH_VALIDATION_log.txt
  - Modified: docs/invoices/output/5790265775_line_items_log.txt
  - Modified: docs/invoices/output/5790265776_extracted_text.txt
  - Modified: docs/invoices/output/5790265781_extracted_text.txt
  - Modified: docs/invoices/output/5790265785_extracted_text.txt
  - Modified: docs/invoices/output/5790265786_extracted_text.txt
  - Modified: docs/invoices/output/parse_line_items_5790265775_corrected.py
  - Modified: invoice-launcher.bat
  - Modified: invoice-launcher.sh
  - Modified: processing/__init__.py
  - Modified: processing/integration.py
  - Modified: processing/models.py
  - Modified: processing/part_discovery_models.py
  - Modified: processing/part_discovery_prompts.py
  - Modified: processing/part_discovery_service.py
  - Modified: processing/pdf_processor.py
  - Modified: processing/report_generator.py
  - Modified: processing/validation_engine.py
  - Modified: processing/validation_integration.py
  - Modified: processing/validation_models.py
  - Modified: processing/validation_strategies.py
  - Modified: processing/validation_strategies_extended.py
  - Modified: pyproject.toml
  - Modified: test_validation/README.md
  - Modified: test_validation/expectations/5790265785_expectations.json
  - Modified: test_validation/extract_invoice_text.py
  - Modified: test_validation/run_validation_tests.py
  - Modified: test_validation/test_cli_validation_output.py
  - Modified: test_validation/test_expectation_generator.py
  - Modified: test_validation/test_text_extraction_validation.py
  - Modified: tests_unit/test_bulk_operations.py
  - Modified: tests_unit/test_cleanup_utils.py
  - Modified: tests_unit/test_database.py
  - Modified: tests_unit/test_interactive_functions.py
  - Modified: tests_unit/test_invoice_processing_refactored.py
  - Modified: tests_unit/test_part_discovery.py
  - Modified: tests_unit/test_pdf_processing.py
  - Modified: uv.lock
New files:
  - Added: cli/version.py
  - Added: deploy.sh
  - Added: processing/invoice_processor.py
  - Added: processing/part_discovery.py
  - Added: processing/report_utils.py
  - Added: test_validation/extract_lines.py
  - Added: test_validation/extract_parts.py
  - Added: test_validation/extract_tables.py
  - Added: test_validation/extract_text.py
  - Added: test_validation/extraction.py
  - Added: test_validation/roo.md
  - Added: test_validation/validate_database.py
  - Added: test_validation/validate_invoice.py
  - Added: test_validation/validation.py

**Deployment:** 2025-08-08 09:56:06 MDT


