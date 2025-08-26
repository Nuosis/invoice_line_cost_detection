# Invoice Rate Detection System - User Flows

This document provides visual representations of the various user flows supported by the Invoice Rate Detection System.

## Primary User Flow - Modern CLI Processing

```mermaid
flowchart TD
    A[User downloads/extracts app] --> B[User opens terminal/command prompt]
    B --> C[Navigate to application directory]
    C --> D[Run: uv run invoice-checker]
    D --> E{Command specified?}
    E -->|No| F[Interactive processing mode]
    E -->|Yes| G[Execute specific command]
    
    F --> F1[Guided invoice processing workflow]
    F1 --> N[User reviews results]
    
    G --> H{Command type?}
    H -->|invoice process| I[Invoice Processing Flow]
    H -->|parts| J[Parts Management Flow]
    H -->|database| K[Database Operations Flow]
    H -->|discovery| L[Discovery Management Flow]
    H -->|config| M[Configuration Flow]
    H -->|status| S[System Status Check]
    
    I --> I1[Validate input parameters]
    I1 --> I2{Input type?}
    I2 -->|Single PDF file| I2A[Process single invoice file]
    I2 -->|Folder| I2B[Process folder of invoices]
    I2A --> I3[Extract PDF data using pdfplumber]
    I2B --> I3
    I3 --> I4[Validate against parts database]
    I4 --> I5[Handle unknown parts discovery]
    I5 --> I6[Generate CSV/TXT report]
    I6 --> I7[Display processing summary]
    I7 --> N
    
    J --> J1[Execute parts operation]
    J1 --> N
    
    K --> K1[Execute database operation]
    K1 --> N
    
    L --> L1[Execute discovery operation]
    L1 --> N
    
    M --> M1[Execute configuration operation]
    M1 --> N
    
    S --> S1[Display system health info]
    S1 --> N
    
    N --> O[User opens report in Excel/Notepad]
```

## Simplified Processing Flow

```mermaid
flowchart TD
    A[User runs: uv run invoice-checker invoice process] --> A1{Input type?}
    A1 -->|Single PDF| A2[Validate PDF file exists]
    A1 -->|Folder| A3[Validate folder contains PDFs]
    A2 --> B[Initialize database connection]
    A3 --> B
    
    B --> C[Create InvoiceProcessor instance]
    C --> D[Extract PDF data using PDFProcessor]
    D --> E[Parse line items and metadata]
    E --> F[For each line item]
    
    F --> G{Part exists in database?}
    G -->|Yes| H[Validate against authorized price]
    G -->|No| I[Handle unknown part]
    
    H --> J{Price matches within tolerance?}
    J -->|Yes| K[Mark as valid]
    J -->|No| L[Flag as potential overcharge]
    
    I --> N[Prompt user to add part]
    
    N --> P{User adds part?}
    P -->|Yes| Q[Save to database]
    P -->|No| R[Continue processing]
    
    Q --> R
    K --> R
    L --> R
    
    R --> S{More line items?}
    S -->|Yes| F
    S -->|No| T[Generate report using SimpleReportGenerator]
    T --> U[Save CSV/TXT report]
    U --> V[Display processing summary]
```

## Parts Management Flow

```mermaid
flowchart TD
    A[User runs: uv run invoice-checker parts] --> B{What operation?}
    
    B -->|add| C[Add single part]
    B -->|list| D[List parts]
    B -->|get| E[Get part details]
    B -->|update| F[Update part]
    B -->|delete| G[Delete part]
    B -->|import| H[Import from CSV]
    B -->|export| I[Export to CSV]
    B -->|stats| J[Show statistics]
    B -->|bulk-*| K[Bulk operations]
    
    C --> C1[Validate part_number and price]
    C1 --> C2[Create Part instance]
    C2 --> C3[Save to database via DatabaseManager]
    C3 --> L[Operation complete]
    
    D --> D1[Query database with filters]
    D1 --> D2[Format and display results]
    D2 --> L
    
    H --> H1[Read CSV file]
    H1 --> H2[Validate data format]
    H2 --> H3[Batch create Part instances]
    H3 --> H4[Save to database]
    H4 --> L
    
    K --> K1[Read CSV with part numbers]
    K1 --> K2[Perform bulk operation]
    K2 --> K3[Update database in batches]
    K3 --> L
```

## Database Operations Flow

```mermaid
flowchart TD
    A[User runs: uv run invoice-checker database] --> B{What operation?}
    
    B -->|backup| C[Create backup]
    B -->|restore| D[Restore from backup]
    B -->|migrate| E[Database migration]
    B -->|maintenance| F[Run maintenance]
    B -->|reset| G[Reset database]
    
    C --> C1[Use DatabaseManager.create_backup]
    C1 --> C2[Optional compression]
    C2 --> C3[Save backup file]
    C3 --> H[Operation complete]
    
    D --> D1[Validate backup file]
    D1 --> D2[Create safety backup]
    D2 --> D3[Restore from backup]
    D3 --> H
    
    E --> E1[Check current schema version]
    E1 --> E2[Apply migrations if needed]
    E2 --> E3[Update schema version]
    E3 --> H
    
    F --> F1[Vacuum database]
    F1 --> F2[Cleanup old logs]
    F2 --> F3[Verify integrity]
    F3 --> H
```

## Discovery Management Flow

```mermaid
flowchart TD
    A[User runs: uv run invoice-checker discovery] --> B{What operation?}
    
    B -->|review| C[Review unknown parts]
    B -->|sessions| D[List discovery sessions]
    B -->|stats| E[Show discovery statistics]
    B -->|export| F[Export discovery data]
    
    C --> C1[Get most recent session or specify session ID]
    C1 --> C3[Present parts for user decision]
    C3 --> C5[User adds/skips parts]
    C5 --> G[Operation complete]
    
    D --> D1[Query discovery logs from database]
    D1 --> D2[Format session information]
    D2 --> G
    
    E --> E1[Calculate statistics from logs]
    E1 --> E2[Display summary information]
    E2 --> G
    
    F --> F1[Export discovery data to CSV]
    F1 --> G
```

## Configuration Management Flow

```mermaid
flowchart TD
    A[User runs: uv run invoice-checker config] --> B{What operation?}
    
    B -->|get| C[Get configuration value]
    B -->|set| D[Set configuration value]
    B -->|list| E[List all configurations]
    B -->|reset| F[Reset to defaults]
    B -->|setup| G[Interactive setup]
    
    C --> C1[Query Configuration from database]
    C1 --> C2[Display value]
    C2 --> H[Operation complete]
    
    D --> D1[Validate key and value]
    D1 --> D2[Create/Update Configuration]
    D2 --> D3[Save to database]
    D3 --> H
    
    E --> E1[Query all configurations]
    E1 --> E2[Filter by category if specified]
    E2 --> E3[Display formatted list]
    E3 --> H
    
    F --> F1[Reset specified key or all]
    F1 --> F2[Update database]
    F2 --> H
    
    G --> G1[Interactive configuration wizard]
    G1 --> G2[Set common configuration values]
    G2 --> H
```

## System Status Flow

```mermaid
flowchart TD
    A[User runs: uv run invoice-checker status] --> B[Initialize DatabaseManager]
    B --> C[Collect system information]
    C --> D[Get database statistics]
    D --> E[Check Python version and platform]
    E --> F{Output format?}
    F -->|table| G[Display formatted table]
    F -->|json| H[Display JSON output]
    G --> I[Show system health summary]
    H --> I
```

---

## Flow Descriptions

### Primary User Flow
The main workflow for invoice processing using the modern CLI system. Users can run the tool without arguments for interactive mode, or use specific commands for direct operations. The system automatically initializes the database and provides comprehensive parts-based validation.

### Processing Flow
The core invoice processing workflow showing how the system extracts PDF data using PDFProcessor, validates against the parts database using ValidationEngine, handles unknown parts through SimplePartDiscoveryService (always in interactive mode), and generates reports using SimpleReportGenerator.

### Parts Management Flow
Comprehensive workflow for managing the parts database through the `parts` command group. Includes operations for adding, listing, updating, deleting, importing, exporting, and bulk operations on parts data stored in the SQLite database.

### Database Operations Flow
Workflow for database maintenance operations through the `database` command group. Includes backup creation, restoration, schema migration, maintenance tasks, and database reset functionality.

### Discovery Management Flow
Workflow for managing unknown parts discovery through the `discovery` command group. The system always operates in interactive mode when unknown parts are encountered. Users can review discovered parts from previous processing sessions, view statistics, and export discovery data.

### Configuration Management Flow
Workflow for system configuration through the `config` command group. Provides get/set operations for configuration values stored in the database, with support for different data types and categories.

### System Status Flow
Simple workflow for checking system health and database connectivity through the `status` command. Displays key system information including database statistics, Python version, and platform details.