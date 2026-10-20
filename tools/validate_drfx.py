#!/usr/bin/env python3
"""Validate DaVinci Resolve .drfx template bundles.

This module validates that a .drfx bundle is a valid, secure ZIP archive
conforming to DaVinci Resolve Fusion template specifications:
- All paths are sanitized with no directory traversal or root escapes.
- No macOS metadata pollution (.DS_Store, __MACOSX).
- Every .setting file contains balanced braces and quotation marks.
- Mandatory Fusion macro components exist (MacroOperator, ActiveTool).
- ActiveTool matches the declared macro operator table key.
"""
from __future__ import annotations

import re
import sys
import zipfile


def brace_balance(source_text: str) -> bool:
    """Verify whether curly braces are balanced outside string literals.

    Args:
        source_text: The Fusion setting text to validate.

    Returns:
        True if all curly braces are strictly balanced and no unclosed
        string literals exist; False otherwise.
    """
    brace_depth = 0
    in_string_literal = False
    char_index = 0
    text_length = len(source_text)

    while char_index < text_length:
        current_char = source_text[char_index]
        if in_string_literal:
            if current_char == "\\":
                char_index += 1
            elif current_char == '"':
                in_string_literal = False
        else:
            if current_char == '"':
                in_string_literal = True
            elif current_char == "{":
                brace_depth += 1
            elif current_char == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    return False
        char_index += 1

    return brace_depth == 0 and not in_string_literal


def validate(bundle_path: str) -> tuple[list[str], list[str]]:
    """Inspect and validate a DaVinci Resolve .drfx bundle.

    Args:
        bundle_path: Filesystem path to the .drfx archive.

    Returns:
        A tuple of (error_messages, diagnostic_notes).
    """
    error_messages: list[str] = []
    diagnostic_notes: list[str] = []

    try:
        with zipfile.ZipFile(bundle_path) as zip_archive:
            archive_entry_names = zip_archive.namelist()

            if zip_archive.testzip() is not None:
                error_messages.append("zip CRC error")

            for entry_name in archive_entry_names:
                has_backslash = "\\" in entry_name
                is_absolute = (
                    entry_name.startswith("/")
                    or bool(re.match(r"^[A-Za-z]:", entry_name))
                )
                has_traversal = ".." in entry_name.split("/")

                if has_backslash or is_absolute or has_traversal:
                    error_messages.append(f"bad path in zip: {entry_name}")

                if "__MACOSX" in entry_name or entry_name.endswith(".DS_Store"):
                    error_messages.append(f"junk file in zip: {entry_name}")

                if not entry_name.startswith("Edit/Effects/"):
                    error_messages.append(
                        f"entry outside Edit/Effects/: {entry_name}"
                    )

            setting_files = [
                name for name in archive_entry_names
                if name.endswith(".setting")
            ]
            if not setting_files:
                error_messages.append("no .setting files found in bundle")

            registered_macros: dict[str, str] = {}
            for setting_file_path in setting_files:
                raw_bytes = zip_archive.read(setting_file_path)
                setting_content = raw_bytes.decode("utf-8", errors="replace")
                parent_folder = setting_file_path.rsplit("/", 1)[0]

                if setting_content.startswith("\ufeff"):
                    error_messages.append(f"{setting_file_path}: has BOM")

                if not brace_balance(setting_content):
                    error_messages.append(
                        f"{setting_file_path}: unbalanced braces/quotes"
                    )

                required_components = (
                    "MacroOperator",
                    "MainInput1",
                    "MainOutput1",
                    "Merge",
                    "ActiveTool",
                )
                for component in required_components:
                    if component not in setting_content:
                        error_messages.append(
                            f"{setting_file_path}: missing '{component}'"
                        )

                active_tool_match = re.search(
                    r'ActiveTool\s*=\s*"([^"]+)"', setting_content
                )
                macro_decl_pattern = (
                    r"Tools\s*=\s*ordered\(\)\s*\{\s*([A-Za-z_]\w*)"
                    r"\s*=\s*MacroOperator"
                )
                macro_decl_match = re.search(
                    macro_decl_pattern, setting_content
                )

                if not (
                    active_tool_match
                    and macro_decl_match
                    and active_tool_match.group(1)
                    == macro_decl_match.group(1)
                ):
                    error_messages.append(
                        f"{setting_file_path}: ActiveTool does not match "
                        "top-level macro name"
                    )
                else:
                    macro_name = active_tool_match.group(1)
                    if macro_name in registered_macros:
                        error_messages.append(
                            f"{setting_file_path}: macro name {macro_name} "
                            f"duplicates {registered_macros[macro_name]}"
                        )
                    else:
                        registered_macros[macro_name] = setting_file_path

                # Validate any external asset references
                filename_pattern = r'Filename\s*=\s*"([^"]*)"'
                referenced_filenames = re.findall(
                    filename_pattern, setting_content
                )
                for ref_filename in referenced_filenames:
                    if not ref_filename.startswith(("Setting:", "Setting:/")):
                        error_messages.append(
                            f"{setting_file_path}: Filename must start with "
                            f"'Setting:' (got {ref_filename!r})"
                        )
                        continue

                    clean_filename = (
                        ref_filename.replace("Setting:/", "")
                        .replace("Setting:", "")
                    )
                    expected_target = f"{parent_folder}/{clean_filename}"
                    if expected_target not in archive_entry_names:
                        error_messages.append(
                            f"{setting_file_path}: referenced file missing "
                            f"in bundle: {expected_target}"
                        )

                setting_basename = setting_file_path.split("/")[-1]
                diagnostic_notes.append(
                    f"{setting_basename} (procedural / vector)"
                )

    except zipfile.BadZipFile:
        return [f"{bundle_path}: not a valid zip archive"], diagnostic_notes

    return error_messages, diagnostic_notes


def main() -> int:
    """Execute bundle validation command-line interface."""
    if len(sys.argv) < 2:
        print(
            "usage: validate_drfx.py BUNDLE.drfx [...]",
            file=sys.stderr,
        )
        return 1

    total_failures = 0
    for bundle_argument in sys.argv[1:]:
        errors, notes = validate(bundle_argument)
        status = "PASS" if not errors else "FAIL"
        print(
            f"== {bundle_argument}: {status}  ({len(notes)} effects checked)"
        )
        for note in notes:
            print(f"   ok: {note}")
        for err in errors:
            print(f"   ERROR: {err}")
            total_failures += 1

    return 1 if total_failures else 0


if __name__ == "__main__":
    sys.exit(main())
