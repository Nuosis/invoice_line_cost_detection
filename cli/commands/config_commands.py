"""
Configuration management commands for the CLI interface.

This module implements configuration-related commands including:
- get: Get configuration value
- set: Set configuration value
- list: List all configurations
- reset: Reset configuration to defaults
"""

import logging
from typing import Optional, Any

import click

from cli.main import pass_context
from cli.validators import validate_configuration_key
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    format_table, format_json
)
from cli.prompts import prompt_for_confirmation
from cli.exceptions import CLIError, ValidationError
from database.models import Configuration, ConfigurationError, DatabaseError, DEFAULT_CONFIG


logger = logging.getLogger(__name__)


# Create config command group
@click.group(name='config')
def config_group():
    """Configuration management commands."""
    pass


@config_group.command()
@click.argument('key', type=str)
@click.option('--format', '-f', type=click.Choice(['value', 'json']), default='value',
              help='Output format')
@pass_context
def get(ctx, key, format):
    """
    Retrieve a configuration value.
    
    Examples:
        # Get a configuration value
        invoice-checker config get validation_mode
        
        # Get value in JSON format
        invoice-checker config get validation_mode --format json
    """
    try:
        # Validate key format
        key = validate_configuration_key(key)
        
        db_manager = ctx.get_db_manager()
        
        # Get configuration
        config = db_manager.get_config(key)
        
        if format == 'value':
            # Display just the value
            typed_value = config.get_typed_value()
            click.echo(str(typed_value))
        elif format == 'json':
            # Display full configuration details
            config_data = {
                'key': config.key,
                'value': config.get_typed_value(),
                'data_type': config.data_type,
                'description': config.description,
                'category': config.category,
                'last_updated': config.last_updated.isoformat() if config.last_updated else None
            }
            click.echo(format_json(config_data))
        
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except ConfigurationError as e:
        raise CLIError(f"Configuration not found: {key}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to get configuration")
        raise CLIError(f"Failed to get configuration: {e}")


@config_group.command()
@click.argument('key', type=str)
@click.argument('value', type=str)
@click.option('--type', '-t', type=click.Choice(['string', 'number', 'boolean', 'json']),
              help='Value type (auto-detected if not specified)')
@click.option('--description', '-d', type=str, help='Configuration description')
@click.option('--category', '-c', type=str, default='general', help='Configuration category')
@pass_context
def set(ctx, key, value, type, description, category):
    """
    Set a configuration value.
    
    Examples:
        # Set a string value
        invoice-checker config set validation_mode parts_based
        
        # Set a number value
        invoice-checker config set price_tolerance 0.001 --type number
        
        # Set a boolean value
        invoice-checker config set interactive_discovery true --type boolean
        
        # Set with description
        invoice-checker config set my_setting "custom value" \\
            --description "My custom setting" \\
            --category "custom"
    """
    try:
        # Validate key format
        key = validate_configuration_key(key)
        
        db_manager = ctx.get_db_manager()
        
        # Auto-detect type if not provided
        if type is None:
            type = _auto_detect_type(value)
        
        # Create configuration object
        config = Configuration(
            key=key,
            value='',  # Will be set by set_typed_value
            data_type=type,
            description=description,
            category=category
        )
        
        # Set the typed value (this will convert and validate)
        try:
            if type == 'boolean':
                bool_value = value.lower() in ('true', '1', 'yes', 'on')
                config.set_typed_value(bool_value)
            elif type == 'number':
                config.set_typed_value(float(value))
            elif type == 'json':
                import json
                json_value = json.loads(value)
                config.set_typed_value(json_value)
            else:
                config.set_typed_value(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid value for type {type}: {e}")
        
        # Show what will be set
        print_info(f"Setting configuration:")
        print_info(f"  Key: {key}")
        print_info(f"  Value: {config.get_typed_value()}")
        print_info(f"  Type: {type}")
        if description:
            print_info(f"  Description: {description}")
        print_info(f"  Category: {category}")
        
        # Confirm if this is a new configuration
        try:
            existing_config = db_manager.get_config(key)
            action = "update"
            print_info(f"This will update the existing configuration.")
            print_info(f"Current value: {existing_config.get_typed_value()}")
        except ConfigurationError:
            action = "create"
            print_info(f"This will create a new configuration.")
        
        if not prompt_for_confirmation(f"Proceed to {action} this configuration?", default=True):
            print_info("Configuration change cancelled.")
            return
        
        # Set the configuration
        db_manager.set_config_value(
            key=key,
            value=config.get_typed_value(),
            data_type=type,
            description=description,
            category=category
        )
        
        print_success(f"Configuration '{key}' set successfully!")
        
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to set configuration")
        raise CLIError(f"Failed to set configuration: {e}")


@config_group.command()
@click.option('--category', '-c', type=str, help='Filter by category')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@pass_context
def list(ctx, category, format):
    """
    List all configuration settings.
    
    Examples:
        # List all configurations
        invoice-checker config list
        
        # List configurations in a specific category
        invoice-checker config list --category validation
        
        # List in JSON format
        invoice-checker config list --format json
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Get configurations
        configs = db_manager.list_config(category=category)
        
        if not configs:
            if category:
                print_info(f"No configurations found in category '{category}'.")
            else:
                print_info("No configurations found.")
            return
        
        # Convert to display format
        config_data = []
        for config in configs:
            config_data.append({
                'Key': config.key,
                'Value': str(config.get_typed_value()),
                'Type': config.data_type,
                'Category': config.category,
                'Description': config.description or '',
                'Last Updated': config.last_updated.strftime('%Y-%m-%d %H:%M:%S') if config.last_updated else ''
            })
        
        # Display results
        if format == 'table':
            click.echo(format_table(config_data))
        elif format == 'json':
            # Convert to more detailed JSON format
            json_data = []
            for config in configs:
                json_data.append({
                    'key': config.key,
                    'value': config.get_typed_value(),
                    'data_type': config.data_type,
                    'category': config.category,
                    'description': config.description,
                    'created_date': config.created_date.isoformat() if config.created_date else None,
                    'last_updated': config.last_updated.isoformat() if config.last_updated else None
                })
            click.echo(format_json(json_data))
        
        # Show summary
        print_info(f"Found {len(configs)} configuration(s)")
        
        if not category:
            # Show category breakdown
            categories = {}
            for config in configs:
                cat = config.category or 'general'
                categories[cat] = categories.get(cat, 0) + 1
            
            if len(categories) > 1:
                print_info("Categories:")
                for cat, count in sorted(categories.items()):
                    print_info(f"  {cat}: {count} setting(s)")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to list configurations")
        raise CLIError(f"Failed to list configurations: {e}")


@config_group.command()
@click.argument('key', type=str, required=False)
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@pass_context
def reset(ctx, key, force):
    """
    Reset configuration to default values.
    
    Examples:
        # Reset a specific configuration
        invoice-checker config reset validation_mode
        
        # Reset all configurations
        invoice-checker config reset
        
        # Force reset without confirmation
        invoice-checker config reset --force
    """
    try:
        db_manager = ctx.get_db_manager()
        
        if key:
            # Reset specific configuration
            key = validate_configuration_key(key)
            
            # Check if key exists in defaults
            if key not in DEFAULT_CONFIG:
                raise CLIError(f"No default value available for configuration '{key}'")
            
            default_config = DEFAULT_CONFIG[key]
            
            print_info(f"Resetting configuration '{key}' to default value:")
            print_info(f"  Default value: {default_config.get_typed_value()}")
            print_info(f"  Description: {default_config.description}")
            
            if not force and not prompt_for_confirmation(
                f"Reset '{key}' to default value?", default=True
            ):
                print_info("Reset cancelled.")
                return
            
            # Reset the configuration
            db_manager.set_config_value(
                key=default_config.key,
                value=default_config.get_typed_value(),
                data_type=default_config.data_type,
                description=default_config.description,
                category=default_config.category
            )
            
            print_success(f"Configuration '{key}' reset to default value!")
            
        else:
            # Reset all configurations
            print_warning("This will reset ALL configurations to their default values.")
            print_warning("Any custom configurations will be lost!")
            
            if not force and not prompt_for_confirmation(
                "Are you sure you want to reset all configurations?", default=False
            ):
                print_info("Reset cancelled.")
                return
            
            # Reset all default configurations
            reset_count = 0
            for default_key, default_config in DEFAULT_CONFIG.items():
                try:
                    db_manager.set_config_value(
                        key=default_config.key,
                        value=default_config.get_typed_value(),
                        data_type=default_config.data_type,
                        description=default_config.description,
                        category=default_config.category
                    )
                    reset_count += 1
                except Exception as e:
                    logger.warning(f"Failed to reset {default_key}: {e}")
            
            print_success(f"Reset {reset_count} configurations to default values!")
            
            # Optionally remove custom configurations
            if click.confirm("Remove custom configurations not in defaults?", default=False):
                all_configs = db_manager.list_config()
                custom_configs = [c for c in all_configs if c.key not in DEFAULT_CONFIG]
                
                removed_count = 0
                for config in custom_configs:
                    try:
                        db_manager.delete_config(config.key)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove {config.key}: {e}")
                
                if removed_count > 0:
                    print_info(f"Removed {removed_count} custom configurations.")
        
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to reset configuration")
        raise CLIError(f"Failed to reset configuration: {e}")


def _auto_detect_type(value: str) -> str:
    """
    Auto-detect the data type of a configuration value.
    
    Args:
        value: String value to analyze
        
    Returns:
        Detected data type
    """
    # Check for boolean values
    if value.lower() in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
        return 'boolean'
    
    # Check for numeric values
    try:
        float(value)
        return 'number'
    except ValueError:
        pass
    
    # Check for JSON values
    if value.startswith(('{', '[')) and value.endswith(('}', ']')):
        try:
            import json
            json.loads(value)
            return 'json'
        except (ValueError, TypeError):
            pass
    
    # Default to string
    return 'string'


# Add commands to the group
config_group.add_command(get)
config_group.add_command(set)
config_group.add_command(list)
config_group.add_command(reset)