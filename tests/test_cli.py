"""
Integration tests for the CLI interface.

This module tests the CLI commands and their integration with the database layer.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from decimal import Decimal

from cli.main import cli
from database.database import DatabaseManager
from database.models import Part


class TestCLIIntegration:
    """Test CLI integration with database operations."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        
        # Initialize test database
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create CLI runner
        self.runner = CliRunner()
        
        # Set environment variable for test database
        self.env = {'INVOICE_CHECKER_DB': str(self.db_path)}
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Close database connection
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_help(self):
        """Test that CLI help command works."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Invoice Rate Detection System' in result.output
        assert 'Commands:' in result.output
    
    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert 'Invoice Rate Detection System' in result.output
    
    def test_status_command(self):
        """Test status command."""
        result = self.runner.invoke(cli, ['status'], env=self.env)
        assert result.exit_code == 0
        assert 'System Status' in result.output
    
    def test_parts_add_command(self):
        """Test adding a part via CLI."""
        result = self.runner.invoke(
            cli, 
            ['parts', 'add', 'TEST123', '15.50', '--description', 'Test Part'],
            env=self.env,
            input='y\n'  # Confirm addition
        )
        assert result.exit_code == 0
        assert 'added successfully' in result.output
        
        # Verify part was added to database
        part = self.db_manager.get_part('TEST123')
        assert part.part_number == 'TEST123'
        assert part.authorized_price == Decimal('15.50')
        assert part.description == 'Test Part'
    
    def test_parts_list_command(self):
        """Test listing parts via CLI."""
        # Add a test part first
        test_part = Part(
            part_number='LIST123',
            authorized_price=Decimal('10.00'),
            description='List Test Part'
        )
        self.db_manager.create_part(test_part)
        
        # Test list command
        result = self.runner.invoke(cli, ['parts', 'list'], env=self.env)
        assert result.exit_code == 0
        assert 'LIST123' in result.output
        assert '10.00' in result.output
    
    def test_parts_get_command(self):
        """Test getting a specific part via CLI."""
        # Add a test part first
        test_part = Part(
            part_number='GET123',
            authorized_price=Decimal('20.00'),
            description='Get Test Part'
        )
        self.db_manager.create_part(test_part)
        
        # Test get command
        result = self.runner.invoke(cli, ['parts', 'get', 'GET123'], env=self.env)
        assert result.exit_code == 0
        assert 'GET123' in result.output
        assert '20.00' in result.output
        assert 'Get Test Part' in result.output
    
    def test_parts_update_command(self):
        """Test updating a part via CLI."""
        # Add a test part first
        test_part = Part(
            part_number='UPDATE123',
            authorized_price=Decimal('25.00'),
            description='Update Test Part'
        )
        self.db_manager.create_part(test_part)
        
        # Test update command
        result = self.runner.invoke(
            cli,
            ['parts', 'update', 'UPDATE123', '--price', '30.00'],
            env=self.env,
            input='y\n'  # Confirm update
        )
        assert result.exit_code == 0
        assert 'updated successfully' in result.output
        
        # Verify part was updated
        updated_part = self.db_manager.get_part('UPDATE123')
        assert updated_part.authorized_price == Decimal('30.00')
    
    def test_parts_delete_command(self):
        """Test deleting a part via CLI."""
        # Add a test part first
        test_part = Part(
            part_number='DELETE123',
            authorized_price=Decimal('35.00'),
            description='Delete Test Part'
        )
        self.db_manager.create_part(test_part)
        
        # Test delete command (soft delete)
        result = self.runner.invoke(
            cli,
            ['parts', 'delete', 'DELETE123'],
            env=self.env,
            input='y\n'  # Confirm deletion
        )
        assert result.exit_code == 0
        assert 'deactivated successfully' in result.output
        
        # Verify part was deactivated
        deleted_part = self.db_manager.get_part('DELETE123')
        assert not deleted_part.is_active
    
    def test_config_set_get_commands(self):
        """Test configuration set and get commands."""
        # Test set command
        result = self.runner.invoke(
            cli,
            ['config', 'set', 'test_setting', 'test_value'],
            env=self.env,
            input='y\n'  # Confirm setting
        )
        assert result.exit_code == 0
        assert 'set successfully' in result.output
        
        # Test get command
        result = self.runner.invoke(
            cli,
            ['config', 'get', 'test_setting'],
            env=self.env
        )
        assert result.exit_code == 0
        assert 'test_value' in result.output
    
    def test_config_list_command(self):
        """Test configuration list command."""
        # Set a test configuration first
        self.db_manager.set_config_value('list_test', 'list_value')
        
        # Test list command
        result = self.runner.invoke(cli, ['config', 'list'], env=self.env)
        assert result.exit_code == 0
        assert 'list_test' in result.output
        assert 'list_value' in result.output
    
    def test_database_backup_command(self):
        """Test database backup command."""
        result = self.runner.invoke(cli, ['database', 'backup'], env=self.env)
        assert result.exit_code == 0
        assert 'backup created successfully' in result.output
    
    def test_database_maintenance_command(self):
        """Test database maintenance command."""
        result = self.runner.invoke(cli, ['database', 'maintenance'], env=self.env)
        assert result.exit_code == 0
        assert 'maintenance completed' in result.output
    
    def test_discovery_list_command(self):
        """Test discovery log list command."""
        result = self.runner.invoke(cli, ['discovery', 'list'], env=self.env)
        assert result.exit_code == 0
        # Should show no entries message for empty database
        assert 'No discovery log entries found' in result.output
    
    def test_parts_stats_command(self):
        """Test parts statistics command."""
        # Add some test parts
        for i in range(3):
            test_part = Part(
                part_number=f'STATS{i:03d}',
                authorized_price=Decimal(f'{10 + i}.00'),
                description=f'Stats Test Part {i}'
            )
            self.db_manager.create_part(test_part)
        
        # Test stats command
        result = self.runner.invoke(cli, ['parts', 'stats'], env=self.env)
        assert result.exit_code == 0
        assert 'Parts Statistics' in result.output
        assert 'total_parts' in result.output or '3' in result.output
    
    def test_error_handling(self):
        """Test CLI error handling."""
        # Test getting non-existent part
        result = self.runner.invoke(cli, ['parts', 'get', 'NONEXISTENT'], env=self.env)
        assert result.exit_code != 0
        assert 'not found' in result.output
        
        # Test invalid part number format
        result = self.runner.invoke(
            cli,
            ['parts', 'add', 'invalid part', '15.50'],
            env=self.env
        )
        assert result.exit_code != 0
    
    def test_interactive_prompts(self):
        """Test interactive prompts when arguments are missing."""
        # Test parts add without arguments (should prompt)
        result = self.runner.invoke(
            cli,
            ['parts', 'add'],
            env=self.env,
            input='PROMPT123\n25.00\nPrompt Test Part\n\n\ny\n'
        )
        assert result.exit_code == 0
        assert 'added successfully' in result.output
        
        # Verify part was added
        part = self.db_manager.get_part('PROMPT123')
        assert part.part_number == 'PROMPT123'
        assert part.authorized_price == Decimal('25.00')


class TestCLIValidation:
    """Test CLI input validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "validation_test.db"
        self.env = {'INVOICE_CHECKER_DB': str(self.db_path)}
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_price_validation(self):
        """Test price validation in CLI commands."""
        # Test negative price
        result = self.runner.invoke(
            cli,
            ['parts', 'add', 'TEST123', '-5.00'],
            env=self.env
        )
        assert result.exit_code != 0
        
        # Test invalid price format
        result = self.runner.invoke(
            cli,
            ['parts', 'add', 'TEST123', 'invalid_price'],
            env=self.env
        )
        assert result.exit_code != 0
    
    def test_part_number_validation(self):
        """Test part number validation."""
        # Test empty part number
        result = self.runner.invoke(
            cli,
            ['parts', 'add', '', '15.00'],
            env=self.env
        )
        assert result.exit_code != 0
        
        # Test part number with invalid characters
        result = self.runner.invoke(
            cli,
            ['parts', 'add', 'TEST@123', '15.00'],
            env=self.env
        )
        assert result.exit_code != 0


class TestCLIFileOperations:
    """Test CLI file operations like import/export."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "file_test.db"
        self.env = {'INVOICE_CHECKER_DB': str(self.db_path)}
        
        # Initialize database
        self.db_manager = DatabaseManager(str(self.db_path))
    
    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parts_export_command(self):
        """Test parts export command."""
        # Add test parts
        for i in range(2):
            test_part = Part(
                part_number=f'EXPORT{i:03d}',
                authorized_price=Decimal(f'{15 + i}.00'),
                description=f'Export Test Part {i}'
            )
            self.db_manager.create_part(test_part)
        
        # Test export command
        export_file = Path(self.temp_dir) / "export_test.csv"
        result = self.runner.invoke(
            cli,
            ['parts', 'export', str(export_file)],
            env=self.env
        )
        assert result.exit_code == 0
        assert 'Exported' in result.output
        assert export_file.exists()
        
        # Verify export file content
        content = export_file.read_text()
        assert 'EXPORT000' in content
        assert 'EXPORT001' in content
    
    def test_parts_import_command(self):
        """Test parts import command."""
        # Create test CSV file
        import_file = Path(self.temp_dir) / "import_test.csv"
        csv_content = """part_number,authorized_price,description,category
IMPORT001,20.00,Import Test Part 1,Test Category
IMPORT002,25.00,Import Test Part 2,Test Category"""
        
        import_file.write_text(csv_content)
        
        # Test import command
        result = self.runner.invoke(
            cli,
            ['parts', 'import', str(import_file)],
            env=self.env,
            input='y\n'  # Confirm import
        )
        assert result.exit_code == 0
        assert 'import completed' in result.output
        
        # Verify parts were imported
        part1 = self.db_manager.get_part('IMPORT001')
        assert part1.authorized_price == Decimal('20.00')
        assert part1.description == 'Import Test Part 1'
        
        part2 = self.db_manager.get_part('IMPORT002')
        assert part2.authorized_price == Decimal('25.00')
        assert part2.description == 'Import Test Part 2'


if __name__ == '__main__':
    pytest.main([__file__])