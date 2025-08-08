# Changelog

All notable changes to the Invoice Rate Detection System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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


