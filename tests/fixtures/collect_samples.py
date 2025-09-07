#!/usr/bin/env python3
"""Collect sample entries from Claude logs for testing."""

import json
import os
from pathlib import Path
from collections import defaultdict


def collect_version_samples():
    """Collect sample entries for each version and entry type."""

    claude_dir = Path.home() / ".claude" / "projects"
    samples = defaultdict(lambda: defaultdict(list))

    # Track unique field combinations
    field_patterns = defaultdict(set)

    for project_dir in claude_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line_num, line in enumerate(f):
                        if line_num > 100:  # Only check first 100 lines per file
                            break

                        line = line.strip()
                        if not line:
                            continue

                        try:
                            entry = json.loads(line)
                            version = entry.get("version", "no_version")
                            entry_type = entry.get("type", "unknown")

                            # Track field patterns
                            fields = tuple(sorted(entry.keys()))
                            field_patterns[version].add(fields)

                            # Collect up to 3 samples per version/type combination
                            key = f"{version}_{entry_type}"
                            if len(samples[version][entry_type]) < 3:
                                samples[version][entry_type].append(entry)

                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                print(f"Error reading {jsonl_file}: {e}")
                continue

    return samples, field_patterns


def save_samples(samples, field_patterns):
    """Save collected samples to fixture files."""

    fixtures_dir = Path("tests/fixtures/versions")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Save samples for each version
    for version, types in sorted(samples.items()):
        version_file = fixtures_dir / f"{version.replace('.', '_')}.json"

        version_data = {
            "version": version,
            "entry_types": {},
            "field_patterns": [list(pattern) for pattern in field_patterns[version]],
        }

        for entry_type, entries in types.items():
            version_data["entry_types"][entry_type] = entries

        with open(version_file, "w") as f:
            json.dump(version_data, f, indent=2, default=str)

        print(
            f"Saved {version_file.name}: {len(types)} types, {sum(len(e) for e in types.values())} entries"
        )

    # Create a summary file
    summary = {
        "versions": sorted(samples.keys()),
        "version_count": len(samples),
        "entry_types": sorted(set(t for types in samples.values() for t in types.keys())),
        "field_variations": {},
    }

    for version, patterns in field_patterns.items():
        summary["field_variations"][version] = len(patterns)

    with open(fixtures_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(
        f"\nSummary: {summary['version_count']} versions, {len(summary['entry_types'])} entry types"
    )
    return summary


if __name__ == "__main__":
    print("Collecting sample entries from Claude logs...")
    samples, field_patterns = collect_version_samples()
    summary = save_samples(samples, field_patterns)

    print("\nVersions found:")
    for v in sorted(summary["versions"]):
        print(f"  - {v} ({summary['field_variations'][v]} field patterns)")

    print("\nEntry types found:")
    for t in summary["entry_types"]:
        print(f"  - {t}")
