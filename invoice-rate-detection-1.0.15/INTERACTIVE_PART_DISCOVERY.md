# Interactive Part Discovery - User Guide

The Interactive Part Discovery feature automatically identifies unknown parts during invoice processing and provides flexible workflows for adding them to your master parts database.

## Overview

When processing invoices, the system compares each line item against your master parts database. If a part is not found, the Interactive Part Discovery system:

1. **Captures** detailed information about the unknown part
2. **Prompts** you to decide what to do with it (interactive mode)
3. **Logs** all discovery activities for audit purposes
4. **Manages** discovery sessions across multiple invoices

## Key Features

- ✅ **Real-time Discovery**: Identifies unknown parts during invoice processing
- ✅ **Interactive Prompts**: User-friendly prompts for adding parts
- ✅ **Batch Processing**: Collect unknown parts for later review
- ✅ **Audit Trail**: Complete logging of all discovery activities
- ✅ **Session Management**: Track discoveries across multiple invoices
- ✅ **Flexible Configuration**: Customize discovery behavior
- ✅ **Price Analysis**: Analyze price variations across invoices

## Getting Started

### Basic Usage

The discovery system activates automatically when processing invoices:

```bash
# Process invoices with interactive discovery (default)
invoice-checker process /path/to/invoices

# Process with batch collection (no interruptions)
invoice-checker process /path/to/invoices --discovery-mode batch

# Disable discovery completely
invoice-checker process /path/to/invoices --no-discovery
```

### Configuration

Configure discovery behavior using the config commands:

```bash
# Enable/disable interactive discovery
invoice-checker config set interactive_discovery true

# Enable batch mode (collect for later review)
invoice-checker config set discovery_batch_mode true

# Set default category for discovered parts
invoice-checker config set discovery_default_category "discovered"

# Require descriptions when adding parts
invoice-checker config set discovery_require_description true
```

## Discovery Modes

### 1. Interactive Mode (Default)

In interactive mode, you're prompted immediately when unknown parts are discovered:

```
┌─ Unknown Part Discovered ─────────────────────────────────────┐
│ Field          │ Value                                        │
├────────────────┼──────────────────────────────────────────────┤
│ Part Number    │ GS0448                                       │
│ Description    │ SHIRT WORK LS BTN COTTON                     │
│ Discovered Price│ $15.50                                      │
│ Quantity       │ 2                                            │
│ Invoice Number │ 5790256943                                   │
│ Invoice Date   │ 06/09/2025                                   │
└────────────────┴──────────────────────────────────────────────┘

What would you like to do with this unknown part?

  1. Add to database now (with full details)
  2. Mark for later review (collect for batch processing)
  3. Skip this part (don't add to database)
  4. Skip all remaining unknown parts
  5. Stop processing and exit

Enter your choice [1]: 
```

### 2. Batch Collection Mode

In batch mode, unknown parts are collected silently and can be reviewed later:

```bash
# Process invoices in batch mode
invoice-checker process /path/to/invoices --discovery-mode batch

# Review collected unknown parts
invoice-checker discovery review
```

### 3. Auto-Add Mode

Configure the system to automatically add discovered parts:

```bash
# Enable auto-add (use with caution)
invoice-checker config set auto_add_discovered_parts true
```

## Discovery Commands

### Review Unknown Parts

Review and process unknown parts that were collected:

```bash
# Review most recent discovery session
invoice-checker discovery review

# Review specific session
invoice-checker discovery review --session-id abc123

# Export unknown parts to CSV
invoice-checker discovery review --output unknown_parts.csv --no-interactive
```

### Discovery Statistics

View discovery statistics and trends:

```bash
# Show overall discovery stats
invoice-checker discovery stats

# Show stats for specific session
invoice-checker discovery stats --session-id abc123

# Show stats for last 7 days
invoice-checker discovery stats --days 7
```

### Discovery Sessions

Manage discovery sessions:

```bash
# List recent discovery sessions
invoice-checker discovery sessions

# Show detailed session information
invoice-checker discovery sessions --detailed

# Limit number of sessions shown
invoice-checker discovery sessions --limit 20
```

### Export Discovery Data

Export discovery data for analysis:

```bash
# Export all discovery data
invoice-checker discovery export --output all_discoveries.csv

# Export specific session
invoice-checker discovery export --session-id abc123 --output session_data.csv

# Include parts that were added to database
invoice-checker discovery export --output complete_data.csv --include-added
```

## Interactive Workflows

### Adding a New Part

When you choose to add a part to the database:

1. **Confirm Part Number**: Verify or modify the part number
2. **Set Authorized Price**: Use discovered price or enter custom price
3. **Add Description**: Use discovered description or enter custom
4. **Set Category**: Choose or enter a category
5. **Add Notes**: Optional notes about the part

Example interaction:
```
Please provide details for the new part:

Use part number 'GS0448'? [Y/n]: y

Discovered price: $15.50
Use this as the authorized price? [Y/n]: y

Discovered description: SHIRT WORK LS BTN COTTON
Use this description? [Y/n]: y

Category (optional): workwear
Size (optional): 
Item type (optional): 
Notes (optional) [Added via interactive discovery]: 

✓ Part GS0448 added to database successfully!
```

### Batch Review Workflow

When reviewing unknown parts in batch:

1. **View Summary**: See all unknown parts with price analysis
2. **Review Each Part**: Go through parts one by one
3. **Make Decisions**: Add, skip, or stop for each part
4. **View Results**: See summary of actions taken

## Configuration Options

### Discovery Behavior

| Setting | Default | Description |
|---------|---------|-------------|
| `interactive_discovery` | `true` | Enable interactive part discovery |
| `discovery_batch_mode` | `false` | Collect unknown parts for batch review |
| `auto_add_discovered_parts` | `false` | Automatically add parts without confirmation |
| `discovery_auto_skip_duplicates` | `true` | Skip parts already discovered in session |

### Discovery Prompts

| Setting | Default | Description |
|---------|---------|-------------|
| `discovery_prompt_timeout` | `300` | Timeout for interactive prompts (seconds) |
| `discovery_require_description` | `false` | Require description when adding parts |
| `discovery_default_category` | `discovered` | Default category for new parts |

### Price Analysis

| Setting | Default | Description |
|---------|---------|-------------|
| `discovery_max_price_variance` | `0.10` | Flag parts with high price variance |

### Maintenance

| Setting | Default | Description |
|---------|---------|-------------|
| `discovery_session_cleanup_days` | `7` | Days to keep inactive sessions |

## Best Practices

### 1. Regular Review

- Review unknown parts regularly to keep your database current
- Use batch mode for large invoice processing jobs
- Export discovery data periodically for analysis

### 2. Price Validation

- Pay attention to price variations across invoices
- Investigate parts with high price variance
- Use discovered prices as starting points, not final values

### 3. Categorization

- Set up consistent categories for discovered parts
- Use the default category setting for consistency
- Review and update categories periodically

### 4. Session Management

- Use meaningful session IDs for tracking
- Clean up old sessions regularly
- Export important discovery data before cleanup

## Troubleshooting

### Common Issues

**Discovery prompts not appearing**
- Check that `interactive_discovery` is enabled
- Verify you're not in batch mode
- Ensure parts are actually unknown (not in database)

**Parts not being discovered**
- Verify invoice processing is working correctly
- Check that part numbers are being extracted properly
- Review discovery logs for errors

**Batch review showing no parts**
- Confirm you processed invoices in batch mode
- Check the correct session ID
- Verify discovery logs exist

### Error Messages

**"No active discovery session found"**
- The session ID doesn't exist or has expired
- Start a new processing session
- Check available sessions with `discovery sessions`

**"Part already exists in database"**
- The part was added since discovery
- Use `parts get <part-number>` to view existing part
- Consider updating the existing part if needed

**"Discovery session timeout"**
- Interactive prompt timed out
- Restart the discovery process
- Adjust timeout setting if needed

## Advanced Usage

### Custom Discovery Workflows

You can integrate discovery into custom workflows:

```python
from processing.validation_engine import ValidationEngine
from database.database import DatabaseManager

# Initialize components
db_manager = DatabaseManager()
validation_engine = ValidationEngine(db_manager, config)

# Process with discovery
validation_result, discovery_results = validation_engine.validate_invoice_with_discovery(
    invoice_path, 
    interactive_discovery=True
)

# Handle results
for result in discovery_results:
    if result.was_successful:
        print(f"✓ {result.part_number}: {result.action_taken}")
    else:
        print(f"✗ {result.part_number}: {result.error_message}")
```

### Batch Processing Integration

```python
# Process multiple invoices with discovery
validation_results, discovery_results = validation_engine.validate_batch_with_discovery(
    invoice_paths,
    interactive_discovery=False  # Use batch mode
)

# Review discovered parts
discovery_service = validation_engine.get_discovery_service()
unknown_parts = discovery_service.get_unknown_parts_for_review(session_id)

# Process unknown parts programmatically
for part_data in unknown_parts:
    # Custom logic for handling unknown parts
    pass
```

## API Reference

### Core Classes

- **`InteractivePartDiscoveryService`**: Main discovery service
- **`PartDiscoveryPrompt`**: Interactive prompt handler
- **`UnknownPartContext`**: Unknown part information
- **`PartDiscoveryResult`**: Discovery operation result
- **`DiscoverySession`**: Session management

### Key Methods

- **`start_discovery_session()`**: Begin discovery session
- **`discover_unknown_parts_from_invoice()`**: Find unknown parts
- **`process_unknown_parts_interactive()`**: Interactive processing
- **`process_unknown_parts_batch()`**: Batch processing
- **`get_unknown_parts_for_review()`**: Get parts for review
- **`end_discovery_session()`**: End session and cleanup

## Support

For additional help:

1. Check the main documentation in `docs/`
2. Review configuration options with `invoice-checker config list`
3. Use `--help` with any command for detailed usage
4. Check discovery logs for troubleshooting

---

*This documentation covers the Interactive Part Discovery feature. For general system documentation, see the main README and other documentation files.*