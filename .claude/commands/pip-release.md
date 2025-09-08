---
name: /pip-release
description: Bump version and initiate the release process for claudeconvo
argument-hint: [version] (e.g., "0.2.1" or blank for suggestion)
allowed-tools: Bash, Read, Edit, MultiEdit, Glob, Grep
---

# Release claudeconvo

Process the release of claudeconvo with the version: $ARGUMENTS

## Version Determination

If no version was provided, analyze the CHANGELOG.md to suggest the next version:

1. Read the current version from pyproject.toml
2. Check CHANGELOG.md for unreleased changes
3. Suggest version bump based on changes:
   - BREAKING changes → minor version bump (0.x.0)
   - Added/Changed features → patch version bump (0.x.Y)
   - Only fixes → patch version bump (0.x.Y)
4. Display: "Suggested version: X.Y.Z based on [reason]. Run: `/release X.Y.Z` to proceed"
5. Stop here if no version provided

## Release Process

With the version number provided:

1. **Validate version format** - Must be X.Y.Z format

2. **Update version in files**:
   - pyproject.toml: Update `version = "X.Y.Z"`
   - src/claudeconvo/__init__.py: Check if `__version__` exists and update

3. **Update CHANGELOG.md**:
   - Change `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` 
   - Add new `## [Unreleased]` section at top
   - Update comparison links at bottom

4. **Run quality checks**:
   ```bash
   make test
   make lint
   make build
   ```

5. **Commit changes**:
   ```bash
   git add pyproject.toml CHANGELOG.md src/claudeconvo/__init__.py
   git commit -m "Release version X.Y.Z"
   ```

6. **Create and push tag**:
   ```bash
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   git push origin main
   git push origin vX.Y.Z
   ```

7. **Display success message**:
   - "✅ Release vX.Y.Z initiated!"
   - "GitHub Actions will automatically publish to PyPI"
   - "Monitor progress at: https://github.com/lpasqualis/claudeconvo/actions"

If any step fails, stop and report the error clearly.