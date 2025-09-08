"""
Diagnostic and analysis tools for Claude log format.

This module provides comprehensive analysis of Claude log files to detect
format variations, parsing issues, and compatibility problems across
different versions of the Claude logging system.

Example usage:
    analyzer = LogAnalyzer(verbose=True)
    file_stats = analyzer.analyze_file(filepath)
    report = analyzer.generate_report()
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import MAX_PARSE_ERRORS_DISPLAY, MAX_TYPE_COUNTS_DISPLAY
from .parsers.adaptive import AdaptiveParser
from .themes import Colors

################################################################################

class LogAnalyzer:
    """Analyze Claude log files for format variations and issues."""

    ################################################################################

    def __init__(self, verbose: bool = False):
        """
        Initialize the analyzer.

        Args:
            verbose: If True, show detailed output including warnings
                    and verbose field pattern information
        """
        self.verbose = verbose
        self.parser  = AdaptiveParser()
        self.stats   = {
            "versions"           : Counter(),
            "entry_types"        : Counter(),
            "field_patterns"     : defaultdict(set),
            "parse_errors"       : [],
            "unknown_fields"     : defaultdict(set),
            "tool_patterns"      : defaultdict(set),
            "content_structures" : defaultdict(set),
            "missing_expected"   : defaultdict(list),
        }

    ################################################################################

    def analyze_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Analyze a single session file.

        Args:
            filepath: Path to the JSONL file

        Returns:
            Analysis results for the file including entry counts,
            versions found, types discovered, and any errors
        """
        file_stats = {
            "filename" : filepath.name,
            "entries"  : 0,
            "versions" : set(),
            "types"    : set(),
            "errors"   : [],
            "warnings" : [],
        }

        try:
            with open(filepath) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        self._analyze_entry(entry, file_stats, line_num)
                        file_stats["entries"] += 1

                    except json.JSONDecodeError as e:
                        error = f"Line {line_num}: JSON decode error: {e}"
                        file_stats["errors"].append(error)
                        self.stats["parse_errors"].append({
                            "file"  : filepath.name,
                            "line"  : line_num,
                            "error" : str(e)
                        })

        except Exception as e:
            file_stats["errors"].append(f"File read error: {e}")

        return file_stats

    ################################################################################

    def _analyze_entry(
        self,
        entry      : Dict[str, Any],
        file_stats : Dict,
        line_num   : int
    ) -> None:
        """
        Analyze a single log entry.

        Args:
            entry: The log entry to analyze
            file_stats: File statistics dictionary to update
            line_num: Line number in the file for error reporting
        """
        # Track version
        version    = entry.get("version", "no_version")
        entry_type = entry.get("type", "unknown")

        self.stats["versions"][version] += 1
        self.stats["entry_types"][entry_type] += 1
        file_stats["versions"].add(version)
        file_stats["types"].add(entry_type)

        # Track field patterns
        fields = tuple(sorted(entry.keys()))
        self.stats["field_patterns"][version].add(fields)

        # Check for unknown fields not in our parser config
        known_fields = {
            "type", "version", "timestamp", "sessionId", "uuid",
            "parentUuid", "isSidechain", "isMeta", "userType", "cwd",
            "gitBranch", "level", "requestId", "message", "toolUseResult",
            "summary", "leafUuid", "content", "role",
        }

        for field in entry.keys():
            if field not in known_fields:
                self.stats["unknown_fields"][version].add(field)
                if self.verbose:
                    file_stats["warnings"].append(
                        f"Line {line_num}: Unknown field '{field}' in version {version}"
                    )

        # Analyze message structure
        if "message" in entry:
            msg = entry["message"]
            if isinstance(msg, dict):
                # Track content structure
                content = msg.get("content")
                if content is not None:
                    content_type = self._get_content_type(content)
                    self.stats["content_structures"][version].add(content_type)

                # Check for tool uses
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "type" in item:
                            self.stats["tool_patterns"][version].add(item["type"])

        # Check for expected fields based on type
        expected_by_type = {
            "user"      : ["message", "timestamp", "sessionId"],
            "assistant" : ["message", "timestamp", "sessionId"],
            "system"    : ["content", "timestamp"],
            "summary"   : ["summary", "leafUuid"],
        }

        if entry_type in expected_by_type:
            for expected in expected_by_type[entry_type]:
                if expected not in entry and "message" not in entry:
                    self.stats["missing_expected"][version].append({
                        "type"  : entry_type,
                        "field" : expected,
                        "line"  : line_num
                    })

    ################################################################################

    def _get_content_type(self, content: Any) -> str:
        """
        Determine the type/structure of content.

        Args:
            content: Content to analyze

        Returns:
            String description of content type and structure
        """
        if content is None:
            return "none"
        elif isinstance(content, str):
            return "string"
        elif isinstance(content, list):
            if not content:
                return "empty_list"
            # Check what's in the list
            types = set()
            for item in content:
                if isinstance(item, dict):
                    if "type" in item:
                        types.add(f"dict_with_type_{item['type']}")
                    else:
                        types.add("dict_no_type")
                else:
                    types.add(type(item).__name__)
            return f"list[{','.join(sorted(types))}]"
        elif isinstance(content, dict):
            return f"dict_keys[{','.join(sorted(content.keys()))}]"
        else:
            return type(content).__name__

    ################################################################################

    def generate_report(self) -> str:
        """
        Generate a detailed analysis report.

        Returns:
            Formatted report string with color codes and analysis results
        """
        report = []
        report.append(f"\n{Colors.BOLD}=== Claude Log Format Analysis Report ==={Colors.RESET}\n")

        # Version Summary
        report.append(f"{Colors.BOLD}Version Distribution:{Colors.RESET}")
        for version, count in sorted(self.stats["versions"].items()):
            pattern_count = len(self.stats["field_patterns"][version])
            report.append(f"  {version}: {count} entries, {pattern_count} field patterns")

        # Entry Types
        report.append(f"\n{Colors.BOLD}Entry Types:{Colors.RESET}")
        for entry_type, count in sorted(self.stats["entry_types"].items()):
            report.append(f"  {entry_type}: {count} entries")

        # Unknown Fields
        if self.stats["unknown_fields"]:
            report.append(f"\n{Colors.WARNING}Unknown Fields Found:{Colors.RESET}")
            for version, fields in sorted(self.stats["unknown_fields"].items()):
                report.append(f"  {version}: {', '.join(sorted(fields))}")

        # Content Structures
        report.append(f"\n{Colors.BOLD}Content Structure Variations:{Colors.RESET}")
        for version, structures in sorted(self.stats["content_structures"].items()):
            report.append(f"  {version}:")
            for struct in sorted(structures):
                report.append(f"    - {struct}")

        # Tool Patterns
        if self.stats["tool_patterns"]:
            report.append(f"\n{Colors.BOLD}Tool/Action Types Found:{Colors.RESET}")
            for version, patterns in sorted(self.stats["tool_patterns"].items()):
                report.append(f"  {version}: {', '.join(sorted(patterns))}")

        # Parse Errors
        if self.stats["parse_errors"]:
            report.append(f"\n{Colors.ERROR}Parse Errors:{Colors.RESET}")
            for error in self.stats["parse_errors"][:MAX_PARSE_ERRORS_DISPLAY]:
                report.append(f"  {error['file']}:{error['line']} - {error['error']}")
            if len(self.stats["parse_errors"]) > 10:
                report.append(f"  ... and {len(self.stats['parse_errors']) - 10} more")

        # Missing Expected Fields
        if self.stats["missing_expected"]:
            report.append(f"\n{Colors.WARNING}Missing Expected Fields:{Colors.RESET}")
            summary = defaultdict(int)
            for version, issues in self.stats["missing_expected"].items():
                for issue in issues:
                    key = f"{version}/{issue['type']}/{issue['field']}"
                    summary[key] += 1

            for key, count in sorted(summary.items())[:MAX_TYPE_COUNTS_DISPLAY]:
                report.append(f"  {key}: {count} occurrences")

        # Field Pattern Details (if verbose)
        if self.verbose:
            report.append(f"\n{Colors.BOLD}Field Pattern Details:{Colors.RESET}")
            for version in sorted(self.stats["field_patterns"].keys())[:5]:  # Show first 5 versions
                report.append(f"\n  {version}:")
                for i, pattern in enumerate(sorted(self.stats["field_patterns"][version]), 1):
                    # Limit field display
                    fields_str = ", ".join(pattern[:MAX_PARSE_ERRORS_DISPLAY])
                    if len(pattern) > 10:
                        fields_str += f", ... ({len(pattern) - 10} more)"
                    report.append(f"    Pattern {i}: [{fields_str}]")

        return "\n".join(report)

    ################################################################################

    def test_parser_compatibility(self) -> Dict[str, Any]:
        """
        Test the adaptive parser against collected samples.

        Returns:
            Test results including success rate and failure details
        """
        results = {
            "total_tested" : 0,
            "successful"   : 0,
            "failed"       : [],
            "warnings"     : []
        }

        # Try to find test fixtures - these may not exist in production installations
        fixtures_dir = Path("tests/fixtures/versions")
        if not fixtures_dir.exists():
            # This is expected in production installations
            results["warnings"].append("Test fixtures not available (expected in production).")
            return results

        for version_file in sorted(fixtures_dir.glob("*.json")):
            if version_file.name == "summary.json":
                continue

            with open(version_file) as f:
                data = json.load(f)

            version = data["version"]

            for entry_type, entries in data["entry_types"].items():
                for entry in entries:
                    results["total_tested"] += 1

                    try:
                        # Try to parse
                        parsed = self.parser.parse_entry(entry)

                        # Check if essential fields were extracted
                        if parsed.get("type") != entry_type and entry_type != "unknown":
                            results["warnings"].append(
                                f"{version}/{entry_type}: Type mismatch (got {parsed.get('type')})"
                            )

                        # Try to extract content
                        if "message" in parsed:
                            self.parser.extract_content_text(parsed)
                            # Just checking it doesn't crash

                        results["successful"] += 1

                    except Exception as e:
                        results["failed"].append({
                            "version" : version,
                            "type"    : entry_type,
                            "error"   : str(e)
                        })

        return results


################################################################################

def run_diagnostics(
    session_file : Optional[str] = None,
    verbose      : bool          = False
) -> None:
    """
    Run diagnostics on Claude log files.

    Args:
        session_file: Specific file to analyze (optional)
        verbose: Show detailed output including warnings and verbose patterns
    """
    analyzer = LogAnalyzer(verbose=verbose)

    if session_file:
        # Analyze specific file
        filepath = Path(session_file).resolve()

        # Validate path is within expected session directories
        home_sessions = Path.home() / ".claude" / "projects"
        valid_path = filepath.is_file() and (
            home_sessions in filepath.parents or filepath.parent == home_sessions
        )
        if not valid_path:
            print(f"{Colors.ERROR}Invalid session file path: {session_file}{Colors.RESET}")
            print(f"Session files must be within {home_sessions}")
            return

        if not filepath.exists():
            print(f"{Colors.ERROR}File not found: {session_file}{Colors.RESET}")
            return

        print(f"\n{Colors.BOLD}Analyzing: {filepath.name}{Colors.RESET}")
        file_stats = analyzer.analyze_file(filepath)

        print(f"  Entries: {file_stats['entries']}")
        print(f"  Versions: {', '.join(sorted(file_stats['versions']))}")
        print(f"  Types: {', '.join(sorted(file_stats['types']))}")

        if file_stats["errors"]:
            print(f"\n{Colors.ERROR}Errors:{Colors.RESET}")
            for error in file_stats["errors"]:
                print(f"  - {error}")

        if verbose and file_stats["warnings"]:
            print(f"\n{Colors.WARNING}Warnings:{Colors.RESET}")
            for warning in file_stats["warnings"]:
                print(f"  - {warning}")

    else:
        # Try to analyze fixture samples if available (developer mode)
        fixtures_dir = Path("tests/fixtures/versions")

        if fixtures_dir.exists():
            print(f"\n{Colors.BOLD}Analyzing test fixtures (developer mode){Colors.RESET}")
            for version_file in sorted(fixtures_dir.glob("*.json")):
                if version_file.name == "summary.json":
                    continue

                with open(version_file) as f:
                    data = json.load(f)

                for entry_type, entries in data["entry_types"].items():
                    for entry in entries:
                        analyzer._analyze_entry(
                            entry,
                            {"versions": set(), "types": set(), "warnings": [], "errors": []},
                            0,
                        )

            # Generate report
            print(analyzer.generate_report())

            # Test parser compatibility (only with fixtures)
            print(f"\n{Colors.BOLD}=== Parser Compatibility Test ==={Colors.RESET}")
            test_results = analyzer.test_parser_compatibility()

            success_rate = (
                test_results["successful"] / test_results["total_tested"] * 100
                if test_results["total_tested"] > 0
                else 0
            )

            print(f"  Tested: {test_results['total_tested']} entries")
            print(f"  Success rate: {success_rate:.1f}%")

            if test_results["failed"]:
                print(f"\n{Colors.ERROR}Failed parses:{Colors.RESET}")
                for failure in test_results["failed"][:MAX_PARSE_ERRORS_DISPLAY]:
                    print(f"  {failure['version']}/{failure['type']}: {failure['error']}")

            if test_results["warnings"]:
                print(f"\n{Colors.WARNING}Warnings:{Colors.RESET}")
                for warning in test_results["warnings"][:MAX_PARSE_ERRORS_DISPLAY]:
                    print(f"  {warning}")
        else:
            # No fixtures available in production
            print(f"\n{Colors.BOLD}Log Format Analysis{Colors.RESET}")
            print("=" * 60)
            msg1 = "Note: Test fixtures not available in production installation"
            print(f"{Colors.DIM}{msg1}{Colors.RESET}")
            msg2 = "Use --diagnose-file <session-file> to analyze a specific session"
            print(f"{Colors.DIM}{msg2}{Colors.RESET}")
