"""
Journey Tests for Path Input Prompts

This test suite validates user interaction flows with path input prompts,
focusing specifically on the PathWithMetadata object creation and handling.

CRITICAL: This test would have caught the PathWithMetadata AttributeError bug
that slipped through our other test layers!
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch

# Import the modules we're testing
from cli.prompts import prompt_for_input_path, PathWithMetadata
from cli.exceptions import UserCancelledError


class TestPathInputPrompts(unittest.TestCase):
    """
    Test path input prompt user journeys with strategic mocking.
    
    These tests simulate actual user typing and validate both the user
    experience and the resulting system state.
    """
    
    def setUp(self):
        """Set up test environment for path input testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_path_test_{self.test_id}_"))
        
        # Create test invoice files
        self.test_invoices_dir = self.temp_dir / "test_invoices"
        self.test_invoices_dir.mkdir()
        
        # Create test PDF files
        self.single_pdf = self.test_invoices_dir / "single_invoice.pdf"
        self.single_pdf.write_text("Dummy PDF content for testing")
        
        self.multiple_pdf_1 = self.test_invoices_dir / "invoice_001.pdf"
        self.multiple_pdf_1.write_text("Dummy PDF content 1")
        
        self.multiple_pdf_2 = self.test_invoices_dir / "invoice_002.pdf"
        self.multiple_pdf_2.write_text("Dummy PDF content 2")
        
        # Create empty directory for testing
        self.empty_dir = self.temp_dir / "empty_dir"
        self.empty_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.single_pdf, self.multiple_pdf_1, self.multiple_pdf_2]
        self.created_dirs = [self.temp_dir, self.test_invoices_dir, self.empty_dir]
    
    def tearDown(self):
        """Clean up all resources created during the test."""
        # Remove all created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        
        # Remove all created directories
        for dir_path in reversed(self.created_dirs):
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
            except Exception:
                pass
    
    def test_single_file_selection_creates_pathwithmetadata_object(self):
        """
        Test that selecting a single PDF file creates PathWithMetadata correctly.
        
        This test would have caught the AttributeError bug!
        """
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # User provides PDF file path
            mock_prompt.return_value = str(self.single_pdf)
            
            # User chooses to process only this file
            mock_choice.return_value = f"Process only this file ({self.single_pdf.name})"
            
            # Call the function that was failing
            result_path = prompt_for_input_path()
            
            # Verify we get a PathWithMetadata object (not regular Path)
            self.assertIsInstance(result_path, PathWithMetadata)
            
            # Verify single file mode is set correctly
            self.assertTrue(result_path.single_file_mode)
            
            # Verify original file is preserved
            self.assertEqual(result_path.original_file.resolve(), self.single_pdf.resolve())
            
            # Verify the path points to the parent directory
            self.assertEqual(str(result_path.resolve()), str(self.single_pdf.parent.resolve()))
            
            # Verify we can access Path methods (delegation works)
            self.assertTrue(result_path.exists())
            self.assertTrue(result_path.is_dir())
    
    def test_single_file_with_multiple_pdfs_batch_selection(self):
        """
        Test user selecting batch processing when multiple PDFs exist.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # User provides PDF file path (but directory has multiple PDFs)
            mock_prompt.return_value = str(self.multiple_pdf_1)
            
            # User chooses to process all files
            mock_choice.return_value = f"Process all 2 PDF files in {self.test_invoices_dir.name}"
            
            result_path = prompt_for_input_path()
            
            # Should return regular Path (not PathWithMetadata) for batch processing
            self.assertIsInstance(result_path, Path)
            self.assertNotIsInstance(result_path, PathWithMetadata)
            
            # Should point to the directory
            self.assertEqual(result_path.resolve(), self.test_invoices_dir.resolve())
    
    def test_directory_input_returns_regular_path(self):
        """
        Test that providing a directory path returns regular Path object.
        """
        with patch('click.prompt') as mock_prompt:
            
            # User provides directory path directly
            mock_prompt.return_value = str(self.test_invoices_dir)
            
            result_path = prompt_for_input_path()
            
            # Should return regular Path (not PathWithMetadata)
            self.assertIsInstance(result_path, Path)
            self.assertNotIsInstance(result_path, PathWithMetadata)
            
            # Should point to the directory
            self.assertEqual(result_path.resolve(), self.test_invoices_dir.resolve())
    
    def test_path_with_spaces_and_quotes_handling(self):
        """
        Test handling of paths with spaces and quotes (common user input).
        """
        # Create path with spaces
        spaced_dir = self.temp_dir / "dir with spaces"
        spaced_dir.mkdir()
        spaced_pdf = spaced_dir / "file with spaces.pdf"
        spaced_pdf.write_text("Dummy content")
        
        self.created_dirs.append(spaced_dir)
        self.created_files.append(spaced_pdf)
        
        test_cases = [
            # User might quote the path
            f'"{spaced_pdf}"',
            f"'{spaced_pdf}'",
            # User might escape spaces
            str(spaced_pdf).replace(' ', '\\ '),
            # Regular path
            str(spaced_pdf)
        ]
        
        for user_input in test_cases:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt, \
                     patch('click.confirm') as mock_confirm, \
                     patch('cli.prompts.prompt_for_choice') as mock_choice:
                    
                    mock_prompt.return_value = user_input
                    mock_confirm.return_value = True  # User confirms to process single file
                    mock_choice.return_value = f"Process only this file ({spaced_pdf.name})"
                    
                    result_path = prompt_for_input_path()
                    
                    # Should handle the path correctly
                    self.assertIsInstance(result_path, PathWithMetadata)
                    self.assertTrue(result_path.single_file_mode)
                    # Use resolve() to handle symlinks consistently
                    self.assertEqual(result_path.original_file.resolve(), spaced_pdf.resolve())
    
    def test_invalid_path_retry_flow(self):
        """
        Test user recovery when providing invalid path.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # First attempt: invalid path, second attempt: valid path
            mock_prompt.side_effect = ["/invalid/path/file.pdf", str(self.single_pdf)]
            mock_confirm.return_value = True  # User chooses to retry
            mock_choice.return_value = f"Process only this file ({self.single_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Should eventually succeed with valid path
            self.assertIsInstance(result_path, PathWithMetadata)
            self.assertTrue(result_path.single_file_mode)
            self.assertEqual(result_path.original_file.resolve(), self.single_pdf.resolve())
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_user_cancellation_during_retry(self):
        """
        Test user cancellation when prompted to retry after invalid path.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: invalid path
            mock_prompt.return_value = "/invalid/path/file.pdf"
            mock_confirm.return_value = False  # User chooses not to retry
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
    
    def test_empty_directory_handling(self):
        """
        Test handling of directory with no PDF files.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # User provides empty directory
            mock_prompt.return_value = str(self.empty_dir)
            mock_confirm.return_value = True  # User chooses to continue anyway
            
            result_path = prompt_for_input_path()
            
            # Should return the directory path
            self.assertEqual(result_path.resolve(), self.empty_dir.resolve())
            self.assertIsInstance(result_path, Path)
            self.assertNotIsInstance(result_path, PathWithMetadata)
    
    def test_non_pdf_file_rejection(self):
        """
        Test rejection of non-PDF files with retry flow.
        """
        # Create non-PDF file
        txt_file = self.temp_dir / "document.txt"
        txt_file.write_text("Not a PDF")
        self.created_files.append(txt_file)
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: non-PDF file, second attempt: valid PDF
            mock_prompt.side_effect = [str(txt_file), str(self.single_pdf)]
            mock_confirm.return_value = True  # User chooses to retry
            
            with patch('cli.prompts.prompt_for_choice') as mock_choice:
                mock_choice.return_value = f"Process only this file ({self.single_pdf.name})"
                
                result_path = prompt_for_input_path()
                
                # Should eventually succeed with PDF file
                self.assertIsInstance(result_path, PathWithMetadata)
                self.assertEqual(result_path.original_file.resolve(), self.single_pdf.resolve())
    
    def test_pathwithmetadata_attribute_access(self):
        """
        Test that PathWithMetadata properly handles attribute access.
        
        This specifically tests the bug scenario that was occurring.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            mock_prompt.return_value = str(self.single_pdf)
            mock_choice.return_value = f"Process only this file ({self.single_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Test the specific attributes that were causing the bug
            self.assertTrue(hasattr(result_path, '_single_file_mode'))
            self.assertTrue(hasattr(result_path, '_original_file'))
            self.assertTrue(hasattr(result_path, '_pdf_files_override'))
            
            # Test that we can set and get these attributes
            result_path._single_file_mode = True
            self.assertTrue(result_path._single_file_mode)
            
            result_path._original_file = self.single_pdf
            self.assertEqual(result_path._original_file, self.single_pdf)
            
            result_path._pdf_files_override = [self.single_pdf]
            self.assertEqual(result_path._pdf_files_override, [self.single_pdf])
    
    def test_pathwithmetadata_path_delegation(self):
        """
        Test that PathWithMetadata properly delegates to underlying Path.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            mock_prompt.return_value = str(self.single_pdf)
            mock_choice.return_value = f"Process only this file ({self.single_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Test Path method delegation
            self.assertTrue(result_path.exists())
            self.assertTrue(result_path.is_dir())
            self.assertEqual(result_path.name, self.test_invoices_dir.name)
            self.assertEqual(result_path.parent.resolve(), self.test_invoices_dir.parent.resolve())
            
            # Test that glob works (important for PDF discovery)
            pdf_files = list(result_path.glob("*.pdf"))
            self.assertGreater(len(pdf_files), 0)
    
    def test_choose_different_path_retry_flow(self):
        """
        Test user choosing "Choose a different path" option.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # First attempt: user chooses different path, second attempt: valid choice
            mock_prompt.side_effect = [str(self.single_pdf), str(self.single_pdf)]
            mock_choice.side_effect = [
                "Choose a different path",
                f"Process only this file ({self.single_pdf.name})"
            ]
            
            result_path = prompt_for_input_path()
            
            # Should eventually succeed
            self.assertIsInstance(result_path, PathWithMetadata)
            self.assertTrue(result_path.single_file_mode)
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            self.assertEqual(mock_choice.call_count, 2)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)