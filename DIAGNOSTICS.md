# Claude Log Diagnostics

## Overview

`claudeconvo` includes a diagnostic mode to help understand and adapt to evolving Claude log formats. As Claude Code releases new versions frequently, the log format can change, and this diagnostic tool helps identify those changes.

## Usage

### Basic Diagnostics

Run diagnostics on collected fixture samples:

```bash
claudeconvo --diagnose
```

### Analyze Specific File

Analyze a specific session file:

```bash
claudeconvo --diagnose-file ~/.claude/projects/your-project/session.jsonl
```

### Verbose Mode

Get detailed field pattern information:

```bash
claudeconvo --diagnose --verbose
```

## What It Analyzes

The diagnostic tool examines:

1. **Version Distribution**: All versions found and their entry counts
2. **Entry Types**: Distribution of user, assistant, system, and summary entries
3. **Unknown Fields**: Fields not recognized by the current parser configuration
4. **Content Structures**: Different content format variations (string, array, etc.)
5. **Tool Patterns**: Types of tool uses found (tool_use, tool_result, etc.)
6. **Parse Errors**: Any entries that failed to parse
7. **Missing Expected Fields**: Fields that should be present but aren't
8. **Parser Compatibility**: Success rate of the adaptive parser

## Collecting Samples

To update the test fixtures with new samples:

```bash
python tests/fixtures/collect_samples.py
```

This collects sample entries from your local Claude logs and saves them as test fixtures.

## Adapting to New Formats

When the diagnostic tool identifies unknown fields:

1. **Update field mappings**: Edit `src/claudeconvo/field_mappings.json` to add new field aliases
2. **Run tests**: Verify compatibility with `make test`
3. **Collect new samples**: Update fixtures if encountering new versions

### Example Field Mapping Update

If diagnostics show a new field `toolCallId`:

```json
"tool_use_id": ["toolUseID", "tool_use_id", "toolId", "toolCallId"],
```

## Version History Found

Current versions in the wild (as of last collection):
- v1.0.70 - v1.0.108
- 24 unique versions identified
- 4-9 field pattern variations per version

## Adaptive Parser Strategy

The parser uses:
- **Field discovery** instead of hardcoded schemas
- **Pattern matching** to find fields regardless of naming
- **Graceful degradation** - shows what it can, skips what it can't
- **Forward compatibility** - unknown fields preserved as `_unknown_*`

## Testing Compatibility

Run version compatibility tests:

```bash
pytest tests/test_version_compatibility.py -v
```

This tests the parser against all collected fixture samples.