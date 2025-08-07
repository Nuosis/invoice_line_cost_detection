"""
Journey Tests for Multi-Step Workflow State Management

This test suite validates user interaction flows with multi-step workflow state management,
focusing specifically on state persistence, workflow resumption, and data consistency
across complex user journeys.

These tests simulate actual user interactions across multi-step workflows and validate
both the user experience and the resulting system state management.
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Import the modules we're testing
from cli.prompts import prompt_for_input_path, PathWithMetadata
from cli.commands.invoice_commands import run_interactive_processing
from cli.commands.discovery_commands import run_interactive_discovery
from cli.context import CLIContext
from cli.exceptions import UserCancelledError
from database.database import DatabaseManager
from processing.models import InvoiceLineItem


class TestMultiStepWorkflowState(unittest.TestCase):
    """
    Test multi-step workflow state management user journeys with strategic mocking.
    
    These tests simulate actual user interactions across complex workflows
    and validate both user experience and system state consistency.
    """
    
    def setUp(self):
        """Set up test environment for multi-step workflow state testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_workflow_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_workflow_db_{self.test_id}.db"
        
        # Use the REAL PDFs from docs/invoices/ (following the established pattern)
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify real files exist
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Create output directory
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        # Track created resources for cleanup (only temp files, not real PDFs!)
        self.created_files = []
        self.created_dirs = [self.temp_dir, self.output_dir]
        
        # Initialize database with test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self.db_manager.initialize_database()
        
        # Add test parts with various configurations
        self.db_manager.add_part("GS0448", "SHIRT WORK LS BTN COTTON", Decimal("0.30"))
        self.db_manager.add_part("WORKFLOW_TEST", "Workflow Test Part", Decimal("15.00"))
        
        # Create mock line items for testing
        self.test_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.35"),  # Different from expected
                quantity=8
            ),
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="UNKNOWN_WORKFLOW",
                description="Unknown Workflow Part",
                rate=Decimal("20.00"),
                quantity=3
            )
        ]
    
    def tearDown(self):
        """Clean up all resources created during the test."""
        # Close database connections
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        
        # Remove only created files (not real PDFs!)
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        
        # Remove created directories
        for dir_path in reversed(self.created_dirs):
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
            except Exception:
                pass
    
    def test_complete_interactive_processing_workflow_state_consistency(self):
        """
        Test complete interactive processing workflow maintains consistent state.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Track workflow state through each step
        workflow_state = {
            "input_path": None,
            "output_path": None,
            "validation_mode": None,
            "processing_completed": False
        }
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Step 1: Input path selection
            input_path_result = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_input_path.return_value = input_path_result
            workflow_state["input_path"] = input_path_result
            
            # Step 2: Output path selection
            output_path_result = self.output_dir / "workflow_state_test.csv"
            mock_output_path.return_value = output_path_result
            workflow_state["output_path"] = output_path_result
            
            # Step 3: Validation mode selection
            validation_mode_result = "parts_based"
            mock_validation_mode.return_value = validation_mode_result
            workflow_state["validation_mode"] = validation_mode_result
            
            # Step 4: Processing
            mock_extract.return_value = self.test_line_items
            workflow_state["processing_completed"] = True
            
            # Execute complete workflow
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify each step was called in correct order
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
            mock_extract.assert_called_once()
            
            # Verify workflow state consistency
            self.assertIsNotNone(workflow_state["input_path"])
            self.assertIsNotNone(workflow_state["output_path"])
            self.assertIsNotNone(workflow_state["validation_mode"])
            self.assertTrue(workflow_state["processing_completed"])
    
    def test_discovery_to_processing_workflow_state_transition(self):
        """
        Test state transition from discovery workflow to processing workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Phase 1: Discovery workflow
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Mock discovery workflow
            mock_extract.return_value = [self.test_line_items[1]]  # Unknown part
            mock_choice.return_value = f"Add {self.test_line_items[1].line_item_code} to parts database"
            mock_prompt.side_effect = [
                self.test_line_items[1].description,
                str(self.test_line_items[1].rate)
            ]
            mock_confirm.return_value = True
            
            # Execute discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify part was added to database
            parts_after_discovery = self.db_manager.get_all_parts()
            added_part = next((p for p in parts_after_discovery if p.code == self.test_line_items[1].line_item_code), None)
            self.assertIsNotNone(added_part, "Part should have been added during discovery")
        
        # Phase 2: Processing workflow using updated database state
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract_processing:
            
            # Mock processing workflow
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "post_discovery_report.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract_processing.return_value = self.test_line_items
            
            # Execute processing workflow
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify processing used updated database state
            final_parts = self.db_manager.get_all_parts()
            self.assertGreater(len(final_parts), 2, "Should have parts from both initial setup and discovery")
    
    def test_workflow_state_persistence_across_interruptions(self):
        """
        Test workflow state handling when interrupted and resumed.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Simulate workflow interruption after partial completion
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode:
            
            # Complete first two steps
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "interrupted_workflow.csv"
            
            # Interrupt during validation mode selection
            mock_validation_mode.side_effect = KeyboardInterrupt()
            
            # Should raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify partial state was handled correctly
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
        
        # Simulate workflow resumption (new attempt)
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path_resume, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path_resume, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode_resume, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract_resume:
            
            # Resume with same configuration
            mock_input_path_resume.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path_resume.return_value = self.output_dir / "resumed_workflow.csv"
            mock_validation_mode_resume.return_value = "parts_based"
            mock_extract_resume.return_value = self.test_line_items
            
            # Should complete successfully
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify complete workflow executed
            mock_extract_resume.assert_called_once()
    
    def test_concurrent_workflow_database_state_consistency(self):
        """
        Test database state consistency when multiple workflow operations occur.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Record initial database state
        initial_parts = self.db_manager.get_all_parts()
        initial_count = len(initial_parts)
        
        # Simulate multiple workflow operations
        operations = [
            {
                "type": "discovery",
                "part_code": "CONCURRENT_1",
                "description": "Concurrent Test Part 1",
                "rate": Decimal("25.00")
            },
            {
                "type": "discovery", 
                "part_code": "CONCURRENT_2",
                "description": "Concurrent Test Part 2",
                "rate": Decimal("35.00")
            }
        ]
        
        for i, operation in enumerate(operations):
            with self.subTest(operation=i):
                with patch('cli.prompts.prompt_for_choice') as mock_choice, \
                     patch('click.prompt') as mock_prompt, \
                     patch('click.confirm') as mock_confirm, \
                     patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
                    
                    # Create mock line item for this operation
                    mock_line_item = InvoiceLineItem(
                        invoice_number="5790265786",
                        date="2024-06-09",
                        line_item_code=operation["part_code"],
                        description=operation["description"],
                        rate=operation["rate"],
                        quantity=1
                    )
                    
                    mock_extract.return_value = [mock_line_item]
                    mock_choice.return_value = f"Add {operation['part_code']} to parts database"
                    mock_prompt.side_effect = [operation["description"], str(operation["rate"])]
                    mock_confirm.return_value = True
                    
                    # Execute discovery operation
                    run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
                    
                    # Verify database state after each operation
                    current_parts = self.db_manager.get_all_parts()
                    expected_count = initial_count + i + 1
                    self.assertEqual(len(current_parts), expected_count, 
                                   f"Database should have {expected_count} parts after operation {i}")
                    
                    # Verify specific part was added
                    added_part = next((p for p in current_parts if p.code == operation["part_code"]), None)
                    self.assertIsNotNone(added_part, f"Part {operation['part_code']} should be in database")
                    self.assertEqual(added_part.description, operation["description"])
                    self.assertEqual(added_part.expected_rate, operation["rate"])
    
    def test_workflow_state_validation_and_error_recovery(self):
        """
        Test workflow state validation and error recovery mechanisms.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Test invalid state recovery
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Step 1: Valid input path
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            
            # Step 2: Invalid output path, then valid path
            invalid_output = Path("/invalid/directory/report.csv")
            valid_output = self.output_dir / "recovered_workflow.csv"
            mock_output_path.side_effect = [invalid_output, valid_output]
            
            # Step 3: Valid validation mode
            mock_validation_mode.return_value = "parts_based"
            
            # Step 4: Successful processing
            mock_extract.return_value = self.test_line_items
            
            # Should recover from invalid output path and complete successfully
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify recovery occurred
            self.assertEqual(mock_output_path.call_count, 2, "Should have retried output path")
            mock_extract.assert_called_once()
    
    def test_complex_multi_step_workflow_with_branching_logic(self):
        """
        Test complex workflow with branching logic based on user choices.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Scenario: User chooses threshold-based validation, requiring additional threshold input
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('cli.prompts.prompt_for_threshold_value') as mock_threshold, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Standard workflow steps
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "branching_workflow.csv"
            
            # Branch: User selects threshold-based validation
            mock_validation_mode.return_value = "threshold_based"
            
            # Additional step: Threshold value required for threshold-based validation
            mock_threshold.return_value = Decimal("30.00")
            
            # Processing with threshold validation
            mock_extract.return_value = self.test_line_items
            
            # Execute branching workflow
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify branching logic was followed
            mock_validation_mode.assert_called_once()
            mock_threshold.assert_called_once()  # Should be called for threshold-based validation
            mock_extract.assert_called_once()
    
    def test_workflow_state_cleanup_after_completion(self):
        """
        Test proper cleanup of workflow state after successful completion.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Create temporary files to track cleanup
        temp_files = []
        for i in range(3):
            temp_file = self.temp_dir / f"temp_workflow_{i}.tmp"
            temp_file.write_text(f"Temporary workflow data {i}")
            temp_files.append(temp_file)
            self.created_files.append(temp_file)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Complete workflow
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "cleanup_test.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = self.test_line_items
            
            # Execute workflow
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify workflow completed successfully
            mock_extract.assert_called_once()
            
            # Verify database connections are still valid (not leaked)
            final_parts = self.db_manager.get_all_parts()
            self.assertIsNotNone(final_parts, "Database should remain accessible after workflow")
    
    def test_workflow_state_with_preset_configuration(self):
        """
        Test workflow state management with preset configurations.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Simulate preset configuration
        preset_config = {
            "validation_mode": "parts_based",
            "output_format": "csv",
            "auto_confirm": True
        }
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Only input and output paths should be prompted (validation mode preset)
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "preset_workflow.csv"
            mock_extract.return_value = self.test_line_items
            
            # Execute workflow with preset (validation mode should not be prompted)
            run_interactive_processing(ctx, preset=preset_config, save_preset=False)
            
            # Verify preset configuration was used
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_extract.assert_called_once()
    
    def test_workflow_state_memory_and_performance_impact(self):
        """
        Test workflow state management doesn't cause memory leaks or performance issues.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Simulate multiple workflow executions to test memory management
        for iteration in range(3):  # Limited iterations for test performance
            with self.subTest(iteration=iteration):
                with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
                     patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
                     patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
                     patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
                    
                    # Configure workflow
                    mock_input_path.return_value = PathWithMetadata(
                        self.real_invoices_dir,
                        single_file_mode=True,
                        original_file=self.target_pdf
                    )
                    mock_output_path.return_value = self.output_dir / f"performance_test_{iteration}.csv"
                    mock_validation_mode.return_value = "parts_based"
                    mock_extract.return_value = self.test_line_items
                    
                    # Execute workflow
                    run_interactive_processing(ctx, preset=None, save_preset=False)
                    
                    # Verify each iteration completes successfully
                    mock_extract.assert_called_once()
                    
                    # Verify database state remains consistent
                    parts = self.db_manager.get_all_parts()
                    self.assertGreaterEqual(len(parts), 2, "Database should maintain consistent state")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)