---
name: /diagnose-and-fix
description: Run comprehensive diagnostics and fix ALL issues to bring claudeconvo to full compliance
allowed-tools: Bash, Read, Write, Edit, MultiEdit, LS, Glob, Grep, Task
---

Run claudeconvo's diagnostic tool to identify ANY issues, then automatically fix ALL problems found to ensure full compatibility with the latest Claude log formats and best practices.

## Step 1: Run Diagnostics

Execute the diagnostic command and capture the output:

```bash
claudeconvo --diagnose --verbose
```

## Step 2: Analyze ALL Issue Types

Examine the diagnostic output for ANY problems:
- Unknown fields that need mapping
- Parse errors or compatibility issues  
- Missing expected fields
- New content structure variations
- New tool patterns or types
- Version-specific issues
- Performance problems
- Any other warnings or errors

## Step 3: Fix Field Mapping Issues

If unknown fields are found:
1. Read `src/claudeconvo/field_mappings.json`
2. Add unknown fields as aliases to appropriate mappings
3. Update content extractors for new structures
4. Update tool patterns for new tool types

## Step 4: Fix Parser Issues

If parser compatibility < 100%:
1. Analyze failing entries to understand new format
2. Update adaptive parser configuration in `src/claudeconvo/parsers/`
3. Add new parser patterns if needed
4. Update parser registry for new entry types

## Step 5: Fix Content Structure Issues

If new content structures found:
1. Update content extraction patterns
2. Add handlers for new message formats
3. Update formatters to display new content types correctly

## Step 6: Fix Missing Features

If diagnostics reveal unsupported features:
1. Identify what new functionality is needed
2. Implement support for new Claude features
3. Add appropriate tests for new functionality

## Step 7: Fix Distribution Issues

Ensure proper packaging:
1. Verify `MANIFEST.in` includes all necessary files
2. Check JSON files are included: `*.json` and `**/*.json`
3. Verify diagnostic tool fallback works

## Step 8: Update Test Fixtures

If new log formats discovered:
1. Collect new sample entries
2. Update test fixtures in `tests/fixtures/`
3. Add tests for new format variations

## Step 9: Comprehensive Testing

After ALL fixes:
1. Re-run diagnostics to confirm all issues resolved:
   ```bash
   claudeconvo --diagnose
   ```
2. Run full test suite:
   ```bash
   make test
   make lint
   ```
3. Test with actual Claude sessions
4. Verify 100% parser compatibility

## Step 10: Final Report

Provide comprehensive summary:
- All issues found (categorized by type)
- All fixes applied (with file changes)
- Test results (must all pass)
- Parser compatibility (must be 100%)
- Any manual interventions needed
- Recommendations for future improvements

$ARGUMENTS