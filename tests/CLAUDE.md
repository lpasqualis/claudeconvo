# Testing Documentation for claudeconvo

## Overview

This document describes the testing approach for `claudeconvo`, including the comprehensive fixture system, test organization, and testing best practices.

## Test Organization

### Test Structure
- **Main test file**: `tests/test_claudeconvo.py` - Core functionality tests
- **Version compatibility**: `tests/test_version_compatibility.py` - Tests against all collected fixtures
- **Test classes**: Organized by functional area (TestShowOptions, TestMessageFormatting, TestSessionFunctions, etc.)

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test
pytest tests/test_claudeconvo.py::TestShowOptions::test_default_options -v

# Run with verbose output
pytest -v

# Run version compatibility tests
pytest tests/test_version_compatibility.py -v
```

### Mocking Strategy

Tests use extensive mocking to avoid filesystem dependencies:
- Mock `Path.exists()`, `Path.glob()`, and `Path.iterdir()` for session discovery
- Mock file reads with realistic Claude log format entries
- Use dependency injection for testable components
- Mock parser configurations when testing adaptive parsing

### Key Test Areas

1. **ShowOptions**: All flag combinations, uppercase/lowercase behavior, defaults
2. **Message Formatting**: Correct handling of user/assistant/tool messages  
3. **Color Themes**: Theme inheritance and proper ANSI code generation
4. **Session Parsing**: Various log format variations from different Claude versions
5. **Adaptive Parser**: Format detection and normalization across versions
6. **Edge Cases**: Empty files, malformed JSON, missing fields, parse errors

## Test Fixtures System

The test suite includes a comprehensive fixture system to ensure `claudeconvo` remains compatible with all versions of Claude Code logs as they evolve. Claude Code releases new versions frequently (often daily), and the log format can change between versions.

## Fixture Collection System

### Location
- **Fixtures**: `tests/fixtures/versions/*.json`
- **Scripts**: `tests/fixtures/collect_samples.py` and `tests/fixtures/anonymize.py`
- **Tests**: `tests/test_version_compatibility.py`

### Collected Versions
The fixtures contain samples from 24 different Claude Code versions (1.0.70 through 1.0.108), representing the evolution of the log format over time.

## How Fixtures Were Generated

### 1. Collection Process
Fixtures are collected from real Claude Code session logs using `collect_samples.py`:

```bash
python tests/fixtures/collect_samples.py
```

This script:
- Scans `~/.claude/projects/` for all session.jsonl files
- Groups entries by version number
- Collects up to 3 samples per entry type (user, assistant, system, summary) per version
- Saves each version's samples to `tests/fixtures/versions/{version}.json`
- Creates a summary file with statistics about versions and field variations

### 2. Anonymization Process
**CRITICAL**: All fixtures MUST be anonymized before committing to protect privacy:

```bash
python tests/fixtures/anonymize.py
```

The anonymization script replaces:
- **Usernames**: `/Users/lpasqualis` → `/Users/anonymous`
- **Personal names**: "Lorenzo", "Pasqualis" → removed
- **Project paths**: `/Dropbox/`, `/Google Drive/` → `/Projects/`
- **Company names**: "DreamBox", "UIEvolution" → generic names
- **Project names**: "claudeconvo" → "LogViewer", "WritingWithClaude" → "ExampleProject"
- **UUIDs**: Replaced with deterministic fake UUIDs
- **Session IDs**: → "session-xxx"
- **Message content**: → "Sample text" or generic content
- **Timestamps**: → "2025-01-01T12:00:00.000Z"

The script also includes a verification function that checks for any remaining sensitive patterns.

## Keeping Fixtures Updated

### When to Update
Update fixtures when:
1. New Claude Code versions are released with format changes
2. The parser fails on real-world logs
3. New field variations are discovered
4. Diagnostic mode reveals unknown fields

### Update Process
1. **Collect new samples**:
   ```bash
   python tests/fixtures/collect_samples.py
   ```

2. **Anonymize the data**:
   ```bash
   python tests/fixtures/anonymize.py
   ```

3. **Verify anonymization**:
   The script will output "✅ No sensitive data found in fixtures" if successful

4. **Run compatibility tests**:
   ```bash
   pytest tests/test_version_compatibility.py -v
   ```

5. **Check for parser issues**:
   ```bash
   claudeconvo --diagnose
   ```

## Test Coverage

The `test_version_compatibility.py` test suite verifies:

1. **All versions parse** - Every fixture entry can be parsed without errors
2. **Type extraction** - Entry types are correctly identified
3. **Content extraction** - Message content is properly extracted
4. **Version preservation** - Version fields are maintained
5. **Tool extraction** - Tool uses are correctly identified
6. **Unknown field handling** - New fields are preserved with `_unknown_` prefix
7. **Pattern matching** - Field patterns match the summary data

## Adaptive Parser Strategy

The parser uses an adaptive approach rather than version-specific schemas:

1. **Field Discovery**: Dynamically discovers fields in each entry
2. **Alias Mapping**: Uses `src/claudeconvo/field_mappings.json` to handle field name variations
3. **Graceful Degradation**: Shows what it can parse, preserves what it can't
4. **Forward Compatibility**: Unknown fields are preserved as `_unknown_*`

## Adding Support for New Formats

When encountering new log formats:

1. **Collect samples** from the new version
2. **Run diagnostics** to identify unknown fields:
   ```bash
   claudeconvo --diagnose --verbose
   ```

3. **Update field mappings** in `src/claudeconvo/field_mappings.json`:
   ```json
   {
     "field_aliases": {
       "new_field": ["newField", "new_field", "fieldVariation"],
       // ... other mappings
     }
   }
   ```

4. **Test compatibility** with the updated mappings
5. **Commit anonymized fixtures** and updated mappings

## Important Notes

- **Privacy**: NEVER commit non-anonymized fixtures
- **JSON Validity**: Ensure all fixtures are valid JSON (embedded strings must be properly escaped)
- **Version Coverage**: Try to maintain samples from a wide range of versions
- **Test First**: Always run tests after updating fixtures or field mappings
- **Incremental Updates**: Add new versions without removing old ones for regression testing

## Troubleshooting

### JSON Parse Errors
If fixtures fail to parse, check for:
- Improperly escaped quotes in embedded content (especially YAML/JSON strings)
- Missing commas between array elements
- Unclosed brackets or braces

### Anonymization Failures
If sensitive data is detected after anonymization:
- Check the patterns in `anonymize.py`
- Add new patterns for unrecognized sensitive data
- Consider manual editing for complex embedded content

### Test Failures
If compatibility tests fail:
- Run `claudeconvo --diagnose` to understand the issue
- Update field mappings if new fields are discovered
- Consider if the parser logic needs enhancement

## Example Workflow for New Version

```bash
# 1. Collect new samples
python tests/fixtures/collect_samples.py

# 2. Check what was collected
ls -la tests/fixtures/versions/

# 3. Anonymize all fixtures
python tests/fixtures/anonymize.py

# 4. Verify anonymization succeeded
# (Script will output verification results)

# 5. Run tests to ensure compatibility
pytest tests/test_version_compatibility.py -v

# 6. If tests fail, diagnose the issue
claudeconvo --diagnose --verbose

# 7. Update field mappings if needed
# Edit src/claudeconvo/field_mappings.json

# 8. Re-run tests to confirm fixes
pytest tests/test_version_compatibility.py -v
```