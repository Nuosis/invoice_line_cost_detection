# Interactive Part Discovery - User Guide

The Interactive Part Discovery feature automatically identifies unknown parts during invoice processing and provides an interactive workflow for adding them to your master parts database.

## Overview

When processing invoices, the system compares each line item against your master parts database. If a part is not found, the Interactive Part Discovery system:

1. **Captures** detailed information about the unknown part
2. **Prompts** you to decide what to do with it (always interactive)
3. **Logs** all discovery activities for audit purposes
4. **Manages** discovery sessions across multiple invoices

## Key Features

- ✅ **Real-time Discovery**: Identifies unknown parts during invoice processing
- ✅ **Interactive Prompts**: User-friendly prompts for adding parts (always enabled)
- ✅ **Audit Trail**: Complete logging of all discovery activities
- ✅ **Session Management**: Track discoveries across multiple invoices
- ✅ **Price Analysis**: Analyze price variations across invoices
- ✅ **Immediate Feedback**: Get instant validation of part information

## Getting Started

### Basic Usage

The discovery system activates automatically when processing invoices and always operates in interactive mode:

```bash
# Process invoices with interactive discovery (always enabled)
invoice-checker process /path/to/invoices

# Interactive discovery cannot be disabled - it's always active
```

## Interactive Discovery Workflow

When an unknown part is encountered during processing, you're prompted immediately:

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
  2. Skip this part (don't add to database)
  3. Skip all remaining unknown parts
  4. Stop processing and exit

Enter your choice [1]: 
```

## Discovery Commands

### Review Discovery History

Review and analyze parts that were discovered:

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

## Configuration Options

### Discovery Behavior

| Setting | Default | Description |
|---------|---------|-------------|
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

### 1. Interactive Processing

- Set aside dedicated time for invoice processing to handle prompts
- Review part information carefully before adding to ensure accuracy
- Use consistent naming conventions for part descriptions
- Add category information when available to improve organization
- Include notes for complex or unusual parts for future reference
- Take advantage of immediate feedback to catch pricing discrepancies

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

### 5. Database Maintenance

- Regularly review your parts database for accuracy
- Update part prices when market conditions change
- Use the discovery log to track when parts were added
- Maintain consistent categorization for better reporting

## Troubleshooting

### Common Issues

**Discovery prompts not appearing**
- Ensure parts are actually unknown (not in database)
- Check that invoice processing is working correctly
- Verify part numbers are being extracted properly

**Parts not being discovered**
- Verify invoice processing is working correctly
- Check that part numbers are being extracted properly
- Review discovery logs for errors

### Error Messages

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

# Process with discovery (always interactive)
validation_result, discovery_results = validation_engine.validate_invoice_with_discovery(
    invoice_path
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
    invoice_paths
)

# Review discovered parts
discovery_service = validation_engine.get_discovery_service()
session_data = discovery_service.get_session_data(session_id)

# Process discovery results
for part_data in session_data.discovered_parts:
    # Custom logic for handling discovered parts
    pass
```

## API Reference

### Core Classes

- **`PartDiscoveryService`**: Main discovery service
- **`SimplePartDiscoveryService`**: Simplified discovery service
- **`UnknownPartContext`**: Unknown part information
- **`PartDiscoveryResult`**: Discovery operation result
- **`DiscoverySession`**: Session management

### Key Methods

- **`start_discovery_session()`**: Begin discovery session
- **`discover_unknown_parts_from_invoice()`**: Find unknown parts
- **`process_unknown_parts_interactive()`**: Interactive processing (always used)
- **`get_discovery_stats()`**: Get discovery statistics
- **`end_discovery_session()`**: End session and cleanup

## Support

For additional help:

1. Check the main documentation in `docs/`
2. Review configuration options with `invoice-checker config list`
3. Use `--help` with any command for detailed usage
4. Check discovery logs for troubleshooting

---

*This documentation covers the Interactive Part Discovery feature. Interactive mode is always enabled to ensure the best user experience and database accuracy. For general system documentation, see the main README and other documentation files.*