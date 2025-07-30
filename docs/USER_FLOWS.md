# Invoice Rate Detection System - User Flows

This document provides visual representations of the various user flows supported by the Invoice Rate Detection System.

## Primary User Flow - Modern CLI Processing

```mermaid
flowchart TD
    A[User downloads/extracts app] --> B[User opens terminal/command prompt]
    B --> C[Navigate to application directory]
    C --> D[Run: uv run invoice-checker]
    D --> E{Command specified?}
    E -->|No| F[Show help and available commands]
    E -->|Yes| G[Execute specific command]
    
    F --> F1[User selects desired operation]
    F1 --> G
    
    G --> H{Command type?}
    H -->|process| I[Invoice Processing Flow]
    H -->|parts| J[Parts Management Flow]
    H -->|database| K[Database Operations Flow]
    H -->|discovery| L[Discovery Management Flow]
    H -->|config| M[Configuration Flow]
    
    I --> I1[Validate input parameters]
    I1 --> I2{Input type?}
    I2 -->|Single PDF file| I2A[Process single invoice file]
    I2 -->|Folder| I2B[Process folder of invoices]
    I2A --> I3[Initialize validation engine]
    I2B --> I3
    I3 --> I4[Process invoices with parts-based validation]
    I4 --> I5[Handle unknown parts discovery]
    I5 --> I6[Generate comprehensive report]
    I6 --> I7[Display processing summary]
    I7 --> N[User reviews results]
    
    J --> J1[Execute parts operation]
    J1 --> N
    
    K --> K1[Execute database operation]
    K1 --> N
    
    L --> L1[Execute discovery operation]
    L1 --> N
    
    M --> M1[Execute configuration operation]
    M1 --> N
    
    N --> O[User opens report in Excel/Notepad]
```

## Advanced User Flow - Parts-Based Validation

```mermaid
flowchart TD
    A[User starts processing] --> A1{Input type?}
    A1 -->|Single PDF| A2[Validate single PDF file]
    A1 -->|Folder| A3[Validate folder contains PDFs]
    A2 --> B[Check if parts database exists]
    A3 --> B
    
    B -->|No| C[Create empty database]
    B -->|Yes| D[Load existing database]
    
    C --> E[Start invoice processing]
    D --> E
    
    E --> F[Extract invoice data]
    F --> G[For each line item]
    G --> H{Part exists in database?}
    
    H -->|Yes| I[Compare invoice price vs authorized price]
    H -->|No| J[Unknown part discovered]
    
    I --> K{Price difference > tolerance?}
    K -->|Yes| L[Flag as overcharge]
    K -->|No| M[Mark as valid]
    
    J --> N{Interactive mode enabled?}
    N -->|Yes| O[Prompt user for action]
    N -->|No| P[Collect for later review]
    
    O --> Q{User choice}
    Q -->|Add now| R[Add part to database]
    Q -->|Review later| P
    Q -->|Skip| S[Continue without adding]
    
    R --> T[Prompt for part details]
    T --> U[Save part to database]
    U --> V[Continue processing]
    
    P --> V
    S --> V
    L --> V
    M --> V
    
    V --> W{More line items?}
    W -->|Yes| G
    W -->|No| X[Generate comprehensive report]
    X --> Y[Save report and unknown parts list]
    Y --> Z[Display processing summary]
```

## Database Management Flow

```mermaid
flowchart TD
    A[User wants to manage parts] --> B{What operation?}
    
    B -->|Add single part| C[Manual part addition]
    B -->|Import many parts| D[Bulk import from CSV]
    B -->|Update existing| E[Part update operations]
    B -->|View/Search| F[Part lookup operations]
    B -->|Backup/Restore| G[Database maintenance]
    
    C --> C1[Specify part number and price]
    C1 --> C2[Add optional details]
    C2 --> C3[Validate part data]
    C3 --> C4[Save to database]
    C4 --> H[Operation complete]
    
    D --> D1[Prepare CSV file]
    D1 --> D2[Validate CSV format]
    D2 --> D3[Import parts in batches]
    D3 --> D4[Handle duplicates/errors]
    D4 --> H
    
    E --> E1[Identify part to update]
    E1 --> E2[Specify new values]
    E2 --> E3[Validate changes]
    E3 --> E4[Update database]
    E4 --> H
    
    F --> F1[Specify search criteria]
    F1 --> F2[Query database]
    F2 --> F3[Display results]
    F3 --> H
    
    G --> G1{Backup or Restore?}
    G1 -->|Backup| G2[Create database backup]
    G1 -->|Restore| G3[Select backup file]
    G2 --> G4[Compress and save]
    G3 --> G5[Validate backup]
    G5 --> G6[Restore database]
    G4 --> H
    G6 --> H
```

## Batch Processing Flow

```mermaid
flowchart TD
    A[User has multiple invoice folders] --> B[Organize folders by period/vendor]
    B --> C[Choose processing approach]
    C --> D{Sequential or Parallel?}
    
    D -->|Sequential| E[Process folders one by one]
    D -->|Parallel| F[Process multiple folders simultaneously]
    
    E --> E1[For each folder]
    E1 --> E2[Process all PDFs in folder]
    E2 --> E3[Generate folder-specific report]
    E3 --> E4{More folders?}
    E4 -->|Yes| E1
    E4 -->|No| G[Combine all reports]
    
    F --> F1[Distribute folders across workers]
    F1 --> F2[Each worker processes assigned folders]
    F2 --> F3[Collect results from all workers]
    F3 --> G
    
    G --> H[Generate master summary report]
    H --> I[Save individual and combined reports]
    I --> J[Display batch processing summary]
    J --> K[User reviews all reports]
```

## Error Handling and Recovery Flow

```mermaid
flowchart TD
    A[Processing encounters error] --> B{Error type?}
    
    B -->|PDF read error| C[Skip problematic PDF]
    B -->|Database error| D[Attempt database recovery]
    B -->|File system error| E[Check permissions and paths]
    B -->|Memory error| F[Reduce batch size]
    B -->|Network error| G[Retry operation]
    
    C --> C1[Log error details]
    C1 --> C2[Continue with next PDF]
    C2 --> H[Complete processing with warnings]
    
    D --> D1[Create backup of current state]
    D1 --> D2[Attempt to repair database]
    D2 --> D3{Repair successful?}
    D3 -->|Yes| I[Resume processing]
    D3 -->|No| J[Restore from backup]
    
    E --> E1[Display permission error message]
    E1 --> E2[Suggest solutions to user]
    E2 --> K[User fixes permissions]
    K --> L[Retry operation]
    
    F --> F1[Reduce processing batch size]
    F1 --> F2[Clear memory caches]
    F2 --> I
    
    G --> G1[Wait with exponential backoff]
    G1 --> G2[Retry operation]
    G2 --> G3{Retry successful?}
    G3 -->|Yes| I
    G3 -->|No| M[Fail with error message]
    
    H --> N[Generate partial report]
    I --> O[Continue normal processing]
    J --> P[Manual intervention required]
    L --> O
    M --> P
    N --> Q[User reviews results and errors]
    O --> R[Processing completes successfully]
    P --> S[User contacts support or fixes issue]
```

## Single File Processing Flow

```mermaid
flowchart TD
    A[User has single PDF invoice] --> B[Open terminal/command prompt]
    B --> C[Navigate to application directory]
    C --> D[Run: uv run invoice-checker process invoice.pdf]
    D --> E[System validates PDF file]
    E --> F{PDF validation result?}
    
    F -->|Valid PDF| G[Initialize processing engine]
    F -->|Invalid PDF| H[Display error message]
    F -->|File not found| I[Display file not found error]
    
    H --> J[User corrects file path/format]
    I --> J
    J --> D
    
    G --> K[Extract invoice data from PDF]
    K --> L[Load parts database]
    L --> M[Process line items]
    M --> N{Unknown parts found?}
    
    N -->|Yes, Interactive mode| O[Prompt user for each unknown part]
    N -->|Yes, Batch mode| P[Collect unknown parts for later]
    N -->|No unknown parts| Q[Validate all parts against database]
    
    O --> O1{User choice for each part?}
    O1 -->|Add now| O2[Add part to database]
    O1 -->|Skip| O3[Continue without adding]
    O1 -->|Review later| P
    
    O2 --> Q
    O3 --> Q
    P --> Q
    
    Q --> R[Generate validation report]
    R --> S[Save report to specified output file]
    S --> T[Display processing summary]
    T --> U[User opens report in Excel/Notepad]
    
    U --> V{Satisfied with results?}
    V -->|Yes| W[Processing complete]
    V -->|No| X[Process another file or adjust settings]
    X --> A
```

## Configuration and Setup Flow

```mermaid
flowchart TD
    A[First time user] --> B[Install Python and dependencies]
    B --> C[Download and extract application]
    C --> D[Run initial setup test]
    D --> E{Setup successful?}
    
    E -->|Yes| F[Configure default settings]
    E -->|No| G[Troubleshoot installation]
    
    G --> G1[Check Python version]
    G1 --> G2[Verify UV installation]
    G2 --> G3[Check file permissions]
    G3 --> G4[Reinstall dependencies]
    G4 --> D
    
    F --> H[Set default threshold]
    H --> I[Configure output preferences]
    I --> J[Set up parts database]
    J --> K{Import existing parts?}
    
    K -->|Yes| L[Prepare parts CSV file]
    K -->|No| M[Start with empty database]
    
    L --> L1[Import parts from CSV]
    L1 --> L2[Verify import results]
    L2 --> N[System ready for use]
    
    M --> N
    N --> O[Run first invoice processing test]
    O --> P[User training complete]
```

## Troubleshooting Flow

```mermaid
flowchart TD
    A[User encounters problem] --> B{Problem type?}
    
    B -->|Command not found| C[Check installation]
    B -->|PDF processing fails| D[Check PDF files]
    B -->|Database issues| E[Database troubleshooting]
    B -->|Performance problems| F[Performance optimization]
    B -->|Import/Export errors| G[Data format validation]
    
    C --> C1[Verify Python installation]
    C1 --> C2[Check UV package manager]
    C2 --> C3[Verify file paths]
    C3 --> C4[Use correct command syntax]
    C4 --> H[Problem resolved]
    
    D --> D1[Check PDF file integrity]
    D1 --> D2[Verify PDF is not password protected]
    D2 --> D3[Ensure PDF contains text not images]
    D3 --> D4[Test with different PDF files]
    D4 --> H
    
    E --> E1[Check database file permissions]
    E1 --> E2[Verify database integrity]
    E2 --> E3[Restore from backup if needed]
    E3 --> E4[Recreate database if corrupted]
    E4 --> H
    
    F --> F1[Reduce batch sizes]
    F1 --> F2[Enable parallel processing]
    F2 --> F3[Run database maintenance]
    F3 --> F4[Close other applications]
    F4 --> H
    
    G --> G1[Validate CSV format]
    G1 --> G2[Check column headers]
    G2 --> G3[Verify data types]
    G3 --> G4[Test with sample data]
    G4 --> H
    
    H --> I{Problem resolved?}
    I -->|Yes| J[Continue normal operation]
    I -->|No| K[Escalate to advanced troubleshooting]
    K --> L[Enable debug logging]
    L --> M[Collect error details]
    M --> N[Contact support or review documentation]
```

---

## Flow Descriptions

### Primary User Flow
The main workflow for invoice processing using the modern CLI system with comprehensive parts-based validation and interactive discovery features. Now supports both single file and folder processing.

### Advanced User Flow
The comprehensive workflow for parts-based validation with interactive discovery, representing the full feature set of the modern CLI system. Includes support for processing individual PDF files or entire folders.

### Database Management Flow
Comprehensive workflow for managing the parts database, including adding, updating, importing, and maintaining parts data through the modern CLI interface.

### Batch Processing Flow
Workflow for processing multiple folders of invoices simultaneously, with options for sequential or parallel processing using the modern CLI batch commands.

### Error Handling and Recovery Flow
System behavior when encountering various types of errors, with automatic recovery mechanisms, user guidance, and centralized error handling.

### Single File Processing Flow
Dedicated workflow for processing individual PDF invoice files, showing the complete process from file validation through report generation. This flow demonstrates how the system handles single files differently from batch processing, including specific error handling and user interaction patterns.

### Configuration and Setup Flow
Initial setup process for new users, including installation verification, basic configuration, and modern CLI system initialization.

### Troubleshooting Flow
Systematic approach to diagnosing and resolving common issues users may encounter with the modern CLI system.