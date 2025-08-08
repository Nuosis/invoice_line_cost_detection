#!/usr/bin/env python3
"""
Test script to verify output location selection logic in interactive workflow.

This script tests the logic that determines where reports should be saved
based on configuration and user selections.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_output_location_logic():
    """Test the output location selection logic from the interactive workflow."""
    
    print("Testing output location selection logic...")
    print("=" * 60)
    
    # Mock configuration values that match the user's scenario
    config_values = {
        'default_invoice_location': 'desktop/invoices',
        'auto_output_location': True,
        'default_output_format': 'txt'
    }
    
    # Simulate the user's input path selection
    desktop_path = Path.home() / 'Desktop'
    default_location = str(desktop_path / 'invoices')
    input_path = Path(default_location)
    
    print(f"1. Configuration values:")
    print(f"   - default_invoice_location: {config_values['default_invoice_location']}")
    print(f"   - auto_output_location: {config_values['auto_output_location']}")
    print(f"   - default_output_format: {config_values['default_output_format']}")
    print()
    
    print(f"2. Input path selection:")
    print(f"   - Desktop path: {desktop_path}")
    print(f"   - Default location: {default_location}")
    print(f"   - Input path: {input_path}")
    print(f"   - Input path exists: {input_path.exists()}")
    print(f"   - Input path is directory: {input_path.is_dir()}")
    print()
    
    # Test the logic from run_interactive_processing function (lines 514-522)
    print("3. Testing output path logic from interactive workflow:")
    
    auto_output = config_values.get('auto_output_location', True)
    print(f"   - auto_output config: {auto_output}")
    
    if auto_output:
        # This is the logic from line 518-519 in invoice_commands.py
        output_path = input_path if input_path.is_dir() else input_path.parent
        print(f"   - Selected output path: {output_path}")
        print(f"   - Output path exists: {output_path.exists()}")
        print(f"   - Expected message: 'Using automatic output location: {output_path}'")
    else:
        print("   - Would prompt user for output location")
    
    print()
    
    # Test what happens in the InvoiceProcessor
    print("4. Testing InvoiceProcessor behavior:")
    
    # The InvoiceProcessor gets called with output_path.parent for directory processing
    # Let's see what that would be
    if input_path.is_file():
        processor_output_dir = output_path.parent
        print(f"   - Single file mode: processor output dir = {processor_output_dir}")
    else:
        processor_output_dir = output_path.parent if hasattr(output_path, 'parent') else output_path
        print(f"   - Directory mode: processor output dir = {processor_output_dir}")
    
    print()
    
    # Check if there's a mismatch
    print("5. Potential issue analysis:")
    
    if str(output_path) != str(input_path):
        print(f"   ⚠️  MISMATCH: output_path ({output_path}) != input_path ({input_path})")
    else:
        print(f"   ✅ MATCH: output_path and input_path are the same")
    
    # Check if the InvoiceProcessor might be using get_documents_directory()
    print(f"   - If InvoiceProcessor falls back to get_documents_directory():")
    documents_dir = Path.cwd() / "documents"
    print(f"     Fallback location: {documents_dir}")
    
    if str(output_path) == str(documents_dir):
        print(f"     ❌ PROBLEM: Output path matches documents directory!")
    else:
        print(f"     ✅ OK: Output path does not match documents directory")
    
    print()
    print("6. Summary:")
    print(f"   - Expected output location: {output_path}")
    print(f"   - User should see: 'Using automatic output location: {output_path}'")
    print(f"   - Reports should be created in: {output_path}/YYYYMMDD/")
    
    return {
        'input_path': input_path,
        'output_path': output_path,
        'config_values': config_values,
        'expected_location': output_path
    }

def test_invoice_processor_integration():
    """Test how the InvoiceProcessor handles the output path."""
    
    print("\n" + "=" * 60)
    print("Testing InvoiceProcessor integration...")
    print("=" * 60)
    
    # Simulate the call to _process_invoices from interactive workflow
    desktop_invoices = Path.home() / 'Desktop' / 'invoices'
    
    print(f"1. Simulating _process_invoices call:")
    print(f"   - input_path: {desktop_invoices}")
    print(f"   - output_path: {desktop_invoices}")
    print(f"   - input_path.is_file(): {desktop_invoices.is_file()}")
    print(f"   - input_path.is_dir(): {desktop_invoices.is_dir()}")
    
    # This matches the logic in _process_invoices (lines 760-761)
    if desktop_invoices.is_file():
        print("   - Would call: processor.process_single_invoice(input_path, output_path.parent)")
        processor_output_dir = desktop_invoices.parent
    else:
        print("   - Would call: processor.process_directory(input_path, output_path.parent)")
        processor_output_dir = desktop_invoices.parent
    
    print(f"   - InvoiceProcessor output directory: {processor_output_dir}")
    
    # Check if this is where the issue might be
    if str(processor_output_dir) != str(desktop_invoices):
        print(f"   ⚠️  POTENTIAL ISSUE: InvoiceProcessor gets {processor_output_dir}, not {desktop_invoices}")
    else:
        print(f"   ✅ OK: InvoiceProcessor gets the correct directory")

if __name__ == "__main__":
    try:
        result = test_output_location_logic()
        test_invoice_processor_integration()
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()