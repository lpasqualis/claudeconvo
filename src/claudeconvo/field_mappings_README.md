# Field Mappings Documentation

## Overview

The `field_mappings.json` file is a critical configuration file that enables claudeconvo's adaptive parser to handle different Claude Code log format versions. As Claude Code evolves and releases new versions (often daily), the internal JSON log format can change. This file acts as a translation dictionary that ensures claudeconvo can parse logs from any Claude Code version without requiring code changes.

## Purpose

This file serves as a **version-agnostic field name translator** that:
- Maps field name variations to standardized internal names
- Defines patterns for extracting content from complex structures
- Identifies tool-related fields across different versions
- Handles special entry types with custom rules

## How It Works

When the adaptive parser (`src/claudeconvo/parsers/adaptive.py`) processes a log entry:

1. **Field Discovery**: Examines all fields in the entry
2. **Alias Resolution**: Maps each field to its standardized name using `field_aliases`
3. **Content Extraction**: Uses `content_extractors` patterns to extract text from complex structures
4. **Type Detection**: Uses `tool_patterns` to identify tool invocations
5. **Normalization**: Converts all variations to a consistent internal format

### Example

If different Claude Code versions use different field names:

**Version 1.0.70:**
```json
{"text": "Hello", "sender": "user", "created": "2025-01-01"}
```

**Version 1.0.85:**
```json
{"content": "Hello", "role": "user", "timestamp": "2025-01-01"}
```

The field mappings normalize both to:
```json
{"content": "Hello", "role": "user", "timestamp": "2025-01-01"}
```

## File Structure

### Top-Level Fields

- **`comment`**: Documentation string (JSON doesn't support real comments)
- **`last_updated`**: Date when mappings were last updated
- **`field_aliases`**: Core mapping dictionary
- **`content_extractors`**: Patterns for extracting text from complex structures
- **`tool_patterns`**: Patterns for identifying tool-related fields
- **`special_entries`**: Rules for handling specific entry types

### Field Aliases

Maps standardized field names to all their possible variations:

```json
"field_aliases": {
  "content": ["content", "text", "message", "body", "data"],
  "role": ["role", "type", "sender", "author"],
  ...
}
```

- **Key**: The standardized field name used internally by claudeconvo
- **Value**: Array of all possible field names that should map to this standard name
- **Order matters**: Put most common variations first for slight performance benefit

### Content Extractors

Defines patterns for extracting text from different content structures:

```json
"content_extractors": {
  "patterns": [
    {
      "description": "Direct string content",
      "type": "string"
    },
    {
      "description": "Array of text objects",
      "type": "array",
      "item_fields": ["text", "content", "value"]
    },
    ...
  ]
}
```

This handles cases where content might be:
- A simple string: `"content": "Hello"`
- An array: `"content": [{"text": "Hello"}, {"text": "World"}]`
- A nested object: `"content": {"text": "Hello"}`

### Tool Patterns

Identifies tool-related fields across versions:

```json
"tool_patterns": {
  "tool_use_types": ["tool_use", "tool", "function_call", "tool_call"],
  "tool_name_fields": ["name", "tool", "function", "tool_name"],
  "tool_id_fields": ["id", "tool_id", "call_id", "use_id"],
  "tool_input_fields": ["input", "arguments", "params", "data", "parameters"]
}
```

### Special Entries

Defines handling rules for specific entry types:

```json
"special_entries": {
  "summary": {
    "minimal_fields": ["type", "summary", "leafUuid"],
    "skip_normalization": true
  },
  "system": {
    "content_fields": ["content", "message", "text"],
    "importance_markers": ["Error", "Warning", "Failed", "Exception"]
  }
}
```

## How to Update

### When to Update

Update this file when:
1. **New Claude Code version** introduces new field names
2. **Diagnostic mode** (`claudeconvo --diagnose`) shows unknown fields
3. **Parser fails** on real-world logs
4. **New entry types** are discovered

### Update Process

1. **Identify the new field variation**
   ```bash
   # Run diagnostic mode to see unknown fields
   claudeconvo --diagnose --verbose
   ```

2. **Determine the standard field it maps to**
   - Check existing entries for similar fields
   - Look at the field's content and purpose

3. **Add to appropriate alias list**
   ```json
   "content": ["content", "text", "message", "body", "data", "new_variation"],
   ```

4. **Test the change**
   ```bash
   # Test with actual log files
   claudeconvo -s
   
   # Run test suite
   pytest tests/
   ```

5. **Update the `last_updated` field**
   ```json
   "last_updated": "2025-09-08"
   ```

### Adding New Field Types

If encountering a completely new field type:

1. **Create new alias entry**
   ```json
   "new_field_type": ["newField", "new_field", "field_variation"],
   ```

2. **Update parser if needed**
   - Most fields work automatically once mapped
   - Complex fields may need parser updates

3. **Document the addition**
   - Add comment in the JSON
   - Update this README if needed

## Testing Changes

After updating field_mappings.json:

1. **Test with real logs**
   ```bash
   # View recent sessions
   claudeconvo -s
   
   # Test specific version files if available
   claudeconvo path/to/specific/session.jsonl
   ```

2. **Run diagnostic mode**
   ```bash
   claudeconvo --diagnose
   ```

3. **Run test suite**
   ```bash
   pytest tests/test_claudeconvo.py -v
   pytest tests/test_version_compatibility.py -v
   ```

4. **Check for unknown fields**
   - Look for fields prefixed with `_unknown_` in output
   - These indicate fields that need mapping

## Version Compatibility

The adaptive parser with field mappings successfully handles Claude Code versions from 1.0.70 through 1.0.108+ (and counting). The system is designed to be forward-compatible, often handling new versions without changes.

### Tested Versions

The parser has been tested with samples from 24+ different versions stored in `tests/fixtures/versions/`. These fixtures are anonymized real-world samples that ensure compatibility.

## Best Practices

1. **Keep aliases comprehensive** - Include all variations, even uncommon ones
2. **Preserve order** - Don't reorder existing aliases unnecessarily
3. **Test thoroughly** - Always test with real log files after changes
4. **Document changes** - Update the `last_updated` field
5. **Be conservative** - If unsure about a mapping, investigate further
6. **Don't remove aliases** - Old logs might still use them

## Common Pitfalls

1. **Case sensitivity** - Field names are case-sensitive
2. **Nested fields** - Some fields appear at different nesting levels
3. **Type variations** - A field might be a string in one version, array in another
4. **Breaking changes** - Rare, but sometimes field semantics change entirely

## Relationship to Code

The field mappings are loaded by:
- `src/claudeconvo/parsers/adaptive.py` - Main parser implementation
- `src/claudeconvo/parsers/registry.py` - Parser registration

The parser uses these mappings to create a normalized view of any log entry, regardless of its original format version.

## Future Considerations

- Consider migrating to Python config file for real comments
- Could auto-generate from fixture analysis
- Might benefit from schema validation
- Could track which versions use which aliases

## Getting Help

If you encounter logs that don't parse correctly:

1. Run `claudeconvo --diagnose` to identify issues
2. Check for `_unknown_` prefixed fields in output
3. Look at the raw JSON with `claudeconvo -r`
4. Create an issue with anonymized samples if needed