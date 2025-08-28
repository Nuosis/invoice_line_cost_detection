# Invoice Line Item Extraction Investigation

## Symptom
Invoice processing function outputs CSV with correct invoice metadata (number, date) but all line item data is missing - Part Number, Description, Line Number, Item Type are empty, and all monetary values default to $0.00. We know this because:
- CSV shows invoice number 5790256943 and date 06/09/2025 correctly
- Multiple rows generated but all line item fields are empty
- All monetary values show $0.00
- Status shows VALID despite missing critical data

## Steps to Recreate
1. Run invoice processing command on invoice file 5790256943
2. System generates CSV output file
3. CSV contains multiple rows with invoice number 5790256943 and date 06/09/2025
4. All line item fields (Part Number, Description, etc.) are empty
5. All monetary values show $0.00
6. Status shows VALID despite missing data

## Attempts to Solve the Problem
Previous developer investigation concluded this was normal/expected behavior, but this contradicts the intended functionality. The system should extract and populate all line item details including part numbers, descriptions, quantities, and rates from the PDF invoice content.

## Hypotheses

1. **PDF Text Extraction** (Most Fundamental) ✅ ELIMINATED
   - hypothesis: PDF text extraction is failing to extract readable content from the invoice
   - null hypothesis: PDF text extraction successfully extracts readable content from the invoice
   - **EVIDENCE**: Live application logs show successful text extraction with character counts and previews
   - **CONCLUSION**: Null hypothesis PROVEN TRUE - text extraction works correctly

2. **Line Item Parsing Logic** ✅ ELIMINATED  
   - hypothesis: Line item parsing logic fails to identify and extract line items from extracted text
   - null hypothesis: Line item parsing logic correctly identifies and extracts line items from text
   - **EVIDENCE**: Live application logs show successful table extraction and line item parsing for working invoices
   - **CONCLUSION**: Null hypothesis PROVEN TRUE - parsing logic works correctly

3. **Table Selection Logic** ❌ ROOT CAUSE IDENTIFIED
   - hypothesis: Table extraction selects wrong tables (e.g., A/R balance tables instead of line item tables)
   - null hypothesis: Table extraction correctly identifies and selects line item tables
   - **EVIDENCE**: Live application logs show extraction of "A/R BALANCES" table instead of line items table
   - **CONCLUSION**: Null hypothesis DISPROVEN - this is the root cause

4. **Data Structure Population**
   - hypothesis: Extracted line item data is not being properly populated into the data structures
   - null hypothesis: Extracted line item data is correctly populated into data structures

5. **Validation Engine Processing**
   - hypothesis: Validation engine incorrectly processes or overwrites line item data
   - null hypothesis: Validation engine preserves and processes line item data correctly

6. **Report Generation Logic**
   - hypothesis: Report generation logic fails to include populated line item data in output
   - null hypothesis: Report generation logic correctly includes all populated line item data

## ROOT CAUSE ANALYSIS

**IDENTIFIED ROOT CAUSE**: Table Selection Logic Failure

The system is extracting the WRONG tables from PDFs. Instead of extracting line item tables, it's extracting other tables like:
- A/R BALANCES tables
- Summary tables  
- Header/footer tables

This explains why:
1. Invoice metadata is correct (extracted from text)
2. Line item fields are empty (wrong table extracted)
3. All monetary values are $0.00 (no line item data)
4. Status shows VALID (system thinks it processed successfully)

## SOLUTION REQUIRED

The table selection and scoring logic in `PDFProcessor._choose_best_tables()` and related methods needs to be improved to:
1. Better identify line item tables vs other table types
2. Improve scoring criteria to prioritize tables with line item characteristics
3. Add validation to ensure selected tables contain actual line item data
4. Fallback mechanisms when line item tables are not found