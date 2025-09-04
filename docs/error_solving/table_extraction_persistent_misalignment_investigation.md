# PDF Table Extraction Persistent Data Quality Investigation

## Symptom
PDF table extraction continues to show data misalignment issues despite implementing intelligent insertion position logic fix. While the core insertion position algorithm has been improved and shows significant success in correctly extracting GP0171NAVY ruin charge items with $17.500 rates, there are still some data content misalignments visible in the diagnostic output, particularly with items showing 'None' codes and mismatched descriptions. We know this because:
- Items with 'None' item codes appear in lines 4 and 32 of the diagnostic output
- Some descriptions still appear misaligned with item codes despite the insertion position fix
- While GP0171NAVY ruin charges are now correctly extracted with $17.500 rates, edge cases remain
- The intelligent alignment algorithm works for the core issue but doesn't address all data quality problems

## Steps to Recreate
1. Run `python diagnose_table_extraction.py` on invoice `docs/invoices/5790265775.pdf`
2. Examine the parsed line items output
3. Look for items with 'None' item codes (lines 4, 32)
4. Observe that some descriptions still appear misaligned with item codes
5. Note that while GP0171NAVY ruin charges are now correctly extracted, there are still some data quality issues in the overall extraction

## Attempts to Solve the Problem
1. Successfully implemented improved insertion position logic using evenly distributed wearer transitions instead of early-only transitions [3,7] -> [3,30]
2. Verified that the core misalignment issue (GP0171NAVY ruin charges showing wrong rates) has been resolved
3. Confirmed that the intelligent alignment algorithm correctly identifies 12 wearer transitions and distributes insertions across the full data range
4. The fix shows major success with correct $17.500 ruin charge extraction, but some edge cases with 'None' codes and description mismatches remain
5. Need to investigate remaining data quality issues that may be related to column mapping, cell content parsing, or edge case handling in the multi-line cell processing logic

## Hypotheses

1. **Column Mapping Validation Error** (Most Fundamental)
   - hypothesis: Column mapping fails to correctly identify all required columns, causing 'None' values in item codes
   - null hypothesis: Column mapping correctly identifies all required columns for all data rows

2. **Empty Cell Handling Logic Error**
   - hypothesis: Empty or missing cells in multi-line data are not properly handled during individual row creation
   - null hypothesis: Empty or missing cells are correctly handled and don't cause 'None' values

3. **Multi-Line Cell Content Parsing Error**
   - hypothesis: Some multi-line cells have inconsistent content structure that breaks the parsing logic
   - null hypothesis: Multi-line cell content parsing handles all content structures correctly

4. **Row Validation Logic Error**
   - hypothesis: Row validation logic incorrectly filters out valid data or allows invalid data through
   - null hypothesis: Row validation logic correctly identifies valid vs invalid line items

5. **Data Type Conversion Error**
   - hypothesis: Data type conversion during LineItem creation fails for certain edge cases
   - null hypothesis: Data type conversion works correctly for all data types and edge cases

6. **Column Index Boundary Error** (Most Dependent)
   - hypothesis: Column index calculations go out of bounds for certain rows, causing data extraction failures
   - null hypothesis: Column index calculations stay within bounds for all rows and columns

## Context

## Definitions
- **Valid Evidence**: ONLY direct log output from live application execution showing actual runtime behavior, timestamps, and data values during multi-line cell parsing
- **Invalid Evidence**: Testing results, code analysis, inferences, logic deductions, or any simulated/mocked behavior
- **Log Evidence Requirements**: Must include timestamps, actual data values, and demonstrate real application flow during `_parse_table_row_to_line_item` execution

## Objective
Using the null hypothesis testing approach:

1. Analyze each hypothesis by:
   - Understanding the stated hypothesis
   - Reviewing its corresponding null hypothesis
   - Examining the evidence required to prove/disprove
   - Following the evidence collection process

2. Evaluate evidence by:
   - **ONLY accepting direct log evidence from live application execution**
   - Rejecting any testing, mocking, or simulated evidence as invalid
   - Determining if log evidence supports or refutes the null hypothesis
   - Assessing if log evidence is conclusive with timestamps and actual data
   - Identifying gaps requiring additional log evidence collection
   - Considering alternative explanations supported by log data

3. Process of elimination:
   - For each proven null hypothesis, eliminate that cause
   - For each disproven null hypothesis, focus investigation there
   - Document reasoning for elimination
   - Maintain clear evidence chain

4. Investigation ordering:
   - Start with most fundamental hypotheses
   - Prove/disprove completely before moving on
   - Use evidence to guide next focus
   - Document decision process

## Expected Outcome
A clear determination of which hypotheses can be eliminated through proven null hypotheses, and which remain as potential root causes requiring further investigation.

**CRITICAL**: The investigation is NOT complete until ALL hypotheses have been systematically tested with live application evidence. Eliminating some hypotheses does NOT mean the problem is solved - it means you must continue investigating the remaining hypotheses.

## Solution Implementation and Verification
Once the root cause has been identified through systematic hypothesis testing:

1. **Solution Identification**: Present the proposed solution based on the evidence gathered
2. **User Agreement**: Obtain explicit user confirmation that they agree with the proposed solution
3. **Solution Implementation**: Implement the solution using the same live application approach:
   - Make the necessary code changes to the live application
   - Add logging to verify the solution is working correctly
   - Execute the application to generate verification evidence
   - Analyze live log output to confirm the solution resolves the issue
4. **Solution Verification**: Use **ONLY live application logs** to verify the solution works - no testing frameworks or simulated evidence

## Investigation Process
We are going to attempt to solve this issue systematically. To this end:
1) when a null hypotheses is or remains false then the hypothesis remains true
2) as long as an hypothesis is true it remain **AN ISSUE TO BE SOLVED**
3) Solve issues in order. Once an issue is solved (by proving the null hypothesis is true), verify the problem persists. If it does proceed to the next hypothesis
4) **ALL evidence must come from live application logs, not tests**

## Systematic Investigation Pattern
Follow this exact pattern for EACH hypothesis:

1. **State the Hypothesis**: What might be wrong
2. **State the Null Hypothesis**: What should be working correctly
3. **Add Targeted Logging**: Insert logging statements in live application code to capture runtime behavior
4. **Execute Application**: Trigger the application to generate log evidence
5. **Analyze Live Evidence**: Review actual log output with timestamps and data values
6. **Prove/Disprove Null Hypothesis**: Based ONLY on live application logs
7. **Eliminate or Continue**: If null hypothesis is proven true, eliminate and move to next hypothesis

## Critical Investigation Rules

**DO NOT STOP** after eliminating some hypotheses. The pattern of systematic elimination is:
- ✅ **Eliminated hypotheses** = Null hypothesis proven true = That component works correctly
- ❓ **Remaining hypotheses** = Still require investigation with live application evidence
- 🔍 **Continue investigating** until ALL hypotheses are tested

**NEVER conclude the investigation is complete** until:
- ALL hypotheses have been systematically tested with live application evidence
- The actual root cause has been identified and verified
- The symptom has been resolved or the true cause is definitively proven

**Evidence Standards**:
- ONLY accept direct log output from live application execution
- Reject testing results, code analysis, or logical inference
- Require timestamps, actual data values, and real application flow
- Each hypothesis must have dedicated logging evidence, not reused evidence

## Investigation Results

### Previous Success: Hypothesis 1 from Original Investigation ✅ **RESOLVED**

**Original Issue**: Intelligent Insertion Position Logic Error
**Solution Applied**: Improved insertion position calculation using evenly distributed wearer transitions
**Result**: ✅ **MAJOR SUCCESS** - GP0171NAVY ruin charge items now correctly show $17.500 rates
**Evidence**: Live application logs show correct extraction of ruin charge data with proper alignment

---

## Current Investigation Status

**READY TO BEGIN**: Systematic investigation of remaining data quality issues
**NEXT STEP**: Begin with Hypothesis 1 - Column Mapping Validation Error