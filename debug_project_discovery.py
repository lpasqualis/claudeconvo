#!/usr/bin/env python3
"""Debug script for claudeconvo project discovery issues."""

import os
import sys
from pathlib import Path


def debug_project_discovery():
    """Debug project discovery logic."""
    print("=" * 80)
    print("CLAUDECONVO PROJECT DISCOVERY DEBUG")
    print("=" * 80)

    # Current working directory
    cwd = os.getcwd()
    print(f"\n1. Current Working Directory:")
    print(f"   {cwd}")

    # Find project root (using improved logic)
    print(f"\n2. Searching for project root...")
    ROOT_MARKERS = [".git", "pyproject.toml", "package.json", "setup.py", ".hg", ".svn", ".claude"]

    current = Path(cwd).resolve()
    start_resolved = str(current)
    print(f"   Starting from: {current}")

    # FIRST: Check if current directory has a Claude session
    claude_projects = Path.home() / ".claude" / "projects"
    parts = Path(start_resolved).parts
    converted_parts = []
    for part in parts:
        if part and part != os.sep:
            part = part.replace("_", "-")
            if part.startswith("."):
                converted_parts.append("-" + part[1:])
            else:
                converted_parts.append(part)

    current_session_name = "-" + "-".join(converted_parts)
    current_session_dir = claude_projects / current_session_name

    print(f"\n   Checking current directory for session:")
    print(f"      Path: {start_resolved}")
    print(f"      Session dir: {current_session_name}")
    print(f"      Session exists: {current_session_dir.exists()}")

    if current_session_dir.exists():
        project_root = start_resolved
        found_marker = "Claude session (no marker needed)"
        print(f"   ✓ Current directory has Claude session - using it!")
        candidates = []
    else:
        print(f"   → Current directory has no session, walking up tree...")
        candidates = []

        # Walk up and collect all candidates
        while current != current.parent:
            for marker in ROOT_MARKERS:
                marker_path = current / marker
                if marker_path.exists():
                    print(f"   ✓ Found marker: {marker} at {current}")

                    # Check if session exists for this path
                    parts = Path(current).parts
                    converted_parts = []
                    for part in parts:
                        if part and part != os.sep:
                            part = part.replace("_", "-")
                            if part.startswith("."):
                                converted_parts.append("-" + part[1:])
                            else:
                                converted_parts.append(part)

                    session_name = "-" + "-".join(converted_parts)
                    session_dir = claude_projects / session_name
                    has_session = session_dir.exists()

                    print(f"      Session dir: {session_name}")
                    print(f"      Session exists: {has_session}")

                    candidates.append((str(current), marker, has_session))
                    break
            current = current.parent

        if not candidates:
            project_root = start_resolved
            found_marker = None
            print(f"   ⚠ No markers found")
        else:
            # Apply prioritization
            print(f"\n   Prioritizing {len(candidates)} candidate(s)...")

            # 1. Prefer candidates with existing sessions
            session_candidates = [c for c in candidates if c[2]]
            if session_candidates:
                project_root = session_candidates[0][0]
                found_marker = session_candidates[0][1]
                print(f"   → Using deepest path with existing session")
            else:
                # 2. Prefer project-specific markers
                project_markers = [".git", "pyproject.toml", "package.json", "setup.py", ".hg", ".svn"]
                found = False
                for candidate in candidates:
                    if candidate[1] in project_markers:
                        project_root = candidate[0]
                        found_marker = candidate[1]
                        print(f"   → Using deepest path with project marker")
                        found = True
                        break

                if not found:
                    # 3. Fall back to any marker
                    project_root = candidates[0][0]
                    found_marker = candidates[0][1]
                    print(f"   → Using deepest path with any marker")

    print(f"\n3. Project Root: {project_root}")
    print(f"   Marker: {found_marker or 'None'}")

    # Convert to session directory name
    print(f"\n4. Converting to session directory name...")
    parts = project_root.split(os.sep)  # Use OS-specific separator
    print(f"   Path parts: {parts}")

    converted_parts = []
    for part in parts:
        if part:
            original = part
            part = part.replace("_", "-")
            if part.startswith("."):
                part = "-" + part[1:]
                print(f"   Converting hidden folder: '{original}' -> '{part}'")
            else:
                if "_" in original:
                    print(f"   Converting underscores: '{original}' -> '{part}'")
            converted_parts.append(part)

    session_name = "-" + "-".join(converted_parts)
    print(f"   Session name: {session_name}")

    # Check if session directory exists
    claude_projects = Path.home() / ".claude" / "projects"
    session_dir = claude_projects / session_name

    print(f"\n5. Session Directory:")
    print(f"   Expected: {session_dir}")
    print(f"   Exists: {session_dir.exists()}")

    if not session_dir.exists():
        print(f"\n   ⚠ Session directory not found!")
        print(f"\n   Available projects in {claude_projects}:")
        if claude_projects.exists():
            dirs = sorted([d.name for d in claude_projects.iterdir() if d.is_dir()])
            for i, d in enumerate(dirs[:20], 1):  # Show first 20
                print(f"      {i}. {d}")
            if len(dirs) > 20:
                print(f"      ... and {len(dirs) - 20} more")
        else:
            print(f"      ERROR: {claude_projects} does not exist!")
    else:
        print(f"\n   ✓ Session directory found!")
        # List session files
        session_files = sorted(session_dir.glob("*.jsonl"),
                             key=lambda x: x.stat().st_mtime,
                             reverse=True)
        print(f"   Session files ({len(session_files)}):")
        for i, f in enumerate(session_files[:5], 1):
            mtime = f.stat().st_mtime
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"      {i}. {f.name} ({date_str})")
        if len(session_files) > 5:
            print(f"      ... and {len(session_files) - 5} more")

    print("\n" + "=" * 80)

    # Suggestions
    if not session_dir.exists():
        print("\nTROUBLESHOOTING SUGGESTIONS:")
        print("1. Check if you've opened this project in Claude Code")
        print("2. Verify the project path matches exactly (case-sensitive)")
        print("3. Try running from the actual project root directory")
        print(f"4. Look for similar names in: {claude_projects}")
        print("\nYou can use: claudeconvo -p <project-name>")
        print("to explicitly specify the project")


if __name__ == "__main__":
    try:
        debug_project_discovery()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
