"""
File Tools for ERPNext MCP Server with Configuration Integration
Handles safe file system operations with security restrictions
"""

import mimetypes
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import frappe


class FileTools:
    """Tools for safe file operations with configuration integration."""

    def __init__(self, config=None):
        print(f"config FileTools {config}")
        # Use provided config or import default
        if config is None:
            from ..config import mcp_config

            self.config = mcp_config
        else:
            self.config = config

        # Define safe directories (relative to site or bench)
        # self.safe_base_paths = [
        #     frappe.get_site_path(),  # Current site directory
        #     frappe.get_site_path(".."),  # Sites directory
        #     frappe.get_site_path("../.."),  # Bench directory
        # ]

        # Define safe subdirectories within allowed paths
        # self.safe_subdirs = [
        #     "sites",
        #     "apps",
        #     "logs",
        #     "config",
        #     "env",
        #     "public",
        #     "private",
        #     "backups",
        #     "archives",
        # ]

        # File extensions that are safe to read
        # self.safe_extensions = {
        #     ".txt",
        #     ".md",
        #     ".rst",
        #     ".json",
        #     ".yml",
        #     ".yaml",
        #     ".py",
        #     ".js",
        #     ".html",
        #     ".css",
        #     ".scss",
        #     ".xml",
        #     ".cfg",
        #     ".conf",
        #     ".ini",
        #     ".log",
        #     ".sql",
        # }

        # Maximum file size to read (10MB)
        # self.max_file_size = 10 * 1024 * 1024

        # Use configuration settings
        self.safe_base_paths = self.config.get_safe_base_paths()
        self.safe_subdirs = self.config.safe_directories
        self.safe_extensions = self.config.allowed_file_extensions
        self.max_file_size = self.config.max_file_size

    def _is_safe_path(self, path: str) -> tuple[bool, str]:
        """Check if path is safe to access using configuration."""
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(path)

            # Check if path is within safe base paths
            for base_path in self.safe_base_paths:
                abs_base = os.path.abspath(base_path)
                if abs_path.startswith(abs_base):
                    return True, "Path is safe"

            # Check if it's a relative path to allowed subdirectories
            path_parts = Path(path).parts
            if path_parts and path_parts[0] in self.safe_subdirs:
                return True, "Path is in allowed subdirectory"

            return (
                False,
                f"Path is outside allowed directories: {', '.join(self.safe_subdirs)}",
            )

        except Exception as e:
            return False, f"Path validation error: {str(e)}"

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0  # type: ignore
        return f"{size_bytes:.1f} TB"

    def _get_file_type_icon(self, path: Path) -> str:
        """Get appropriate icon for file type."""
        if path.is_dir():
            return "📁"

        suffix = path.suffix.lower()
        icon_map = {
            ".py": "🐍",
            ".js": "📜",
            ".html": "🌐",
            ".css": "🎨",
            ".json": "📋",
            ".yml": "⚙️",
            ".yaml": "⚙️",
            ".xml": "📄",
            ".txt": "📝",
            ".md": "📖",
            ".rst": "📚",
            ".log": "📊",
            ".sql": "🗄️",
            ".cfg": "⚙️",
            ".conf": "⚙️",
            ".ini": "⚙️",
            ".png": "🖼️",
            ".jpg": "🖼️",
            ".jpeg": "🖼️",
            ".gif": "🖼️",
            ".pdf": "📕",
            ".doc": "📄",
            ".docx": "📄",
            ".xls": "📊",
            ".zip": "📦",
            ".tar": "📦",
            ".gz": "📦",
        }
        return icon_map.get(suffix, "📄")

    async def list_files(
        self, path: str, recursive: bool = False, pattern: Optional[str] = None
    ) -> str:
        """List files and directories with configuration-aware validation."""
        try:
            # Security check using config
            is_safe, message = self._is_safe_path(path)
            if not is_safe:
                return f"❌ Access denied: {message}"

            path_obj = Path(path)
            if not path_obj.exists():
                return f"❌ Path not found: {path}"

            if not path_obj.is_dir():
                return f"❌ Not a directory: {path}"

            output = [
                f"📁 Directory Listing: {path}",
                "=" * (len(path) + 20),
                f"📋 Config: Max file size {self.config.max_file_size // (1024*1024)}MB, "
                f"Allowed extensions: {len(self.safe_extensions)} types",
                "",
            ]

            try:
                # Get items
                if recursive:
                    if pattern:
                        items = list(path_obj.rglob(pattern))
                    else:
                        items = list(path_obj.rglob("*"))
                else:
                    if pattern:
                        items = list(path_obj.glob(pattern))
                    else:
                        items = list(path_obj.iterdir())

                # Sort items: directories first, then files
                items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

                if not items:
                    return f"📁 Directory is empty: {path}"

                # Format items
                for item in items:
                    try:
                        stat_info = item.stat()

                        # File type and permissions
                        icon = self._get_file_type_icon(item)
                        permissions = stat.filemode(stat_info.st_mode)

                        # Size
                        if item.is_file():
                            size = self._format_file_size(stat_info.st_size)
                        else:
                            size = "<DIR>"

                        # Modified time
                        mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                        mod_str = mod_time.strftime("%Y-%m-%d %H:%M")

                        # Relative path for recursive listing
                        if recursive:
                            rel_path = item.relative_to(path_obj)
                            name = str(rel_path)
                        else:
                            name = item.name

                        # Format line
                        line = f"{icon} {permissions} {size:>10} {mod_str} {name}"
                        output.append(line)

                    except (OSError, PermissionError):
                        output.append(f"❌ {item.name} (access denied)")

                # Summary
                file_count = sum(1 for item in items if item.is_file())
                dir_count = sum(1 for item in items if item.is_dir())

                output.extend(
                    ["", f"📊 Summary: {dir_count} directories, {file_count} files"]
                )

                if recursive:
                    output.append("🔄 (Recursive listing)")
                if pattern:
                    output.append(f"🎯 Pattern: {pattern}")

            except PermissionError:
                return f"❌ Permission denied accessing: {path}"
            except Exception as e:
                return f"❌ Error listing directory: {str(e)}"

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def read_file(
        self, path: str, lines: Optional[int] = None, encoding: str = "utf-8"
    ) -> str:
        """Read and display file contents with configuration validation."""
        try:
            # Security check using config
            is_safe, message = self._is_safe_path(path)
            if not is_safe:
                return f"❌ Access denied: {message}"

            path_obj = Path(path)
            if not path_obj.exists():
                return f"❌ File not found: {path}"

            if not path_obj.is_file():
                return f"❌ Not a file: {path}"

            # Check file size using config
            file_size = path_obj.stat().st_size
            if file_size > self.max_file_size:
                return (
                    f"❌ File too large: {self._format_file_size(file_size)} "
                    f"(max: {self._format_file_size(self.max_file_size)})"
                )

            # Check file extension using config
            if path_obj.suffix.lower() not in self.safe_extensions:
                return f"❌ File type not allowed: {path_obj.suffix} (safe types: {', '.join(sorted(self.safe_extensions))})"

            try:
                # Read file content
                with open(path_obj, "r", encoding=encoding) as f:
                    if lines:
                        content_lines = []
                        for i, line in enumerate(f, 1):
                            if i > lines:
                                break
                            content_lines.append(line.rstrip())
                        content = "\n".join(content_lines)
                        truncated = i > lines
                    else:
                        content = f.read()
                        truncated = False

                # Get file info
                stat_info = path_obj.stat()
                mod_time = datetime.fromtimestamp(stat_info.st_mtime)

                # Detect file type
                mime_type, _ = mimetypes.guess_type(str(path_obj))

                output = [
                    f"📄 File: {path}",
                    "=" * (len(path) + 8),
                    f"Size: {self._format_file_size(file_size)}",
                    f"Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Type: {mime_type or 'text/plain'}",
                    f"Encoding: {encoding}",
                ]

                if lines:
                    output.append(f"Lines shown: {min(lines, len(content.split()))}")

                output.extend(["", "Content:", "-" * 50, content])

                if truncated:
                    output.extend(["", f"⚠️  File truncated to {lines} lines"])

                return "\n".join(output)

            except UnicodeDecodeError:
                return f"❌ Cannot read file: Invalid encoding ({encoding}). Try a different encoding."
            except PermissionError:
                return f"❌ Permission denied reading file: {path}"
            except Exception as e:
                return f"❌ Error reading file: {str(e)}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def get_file_info(self, path: str) -> str:
        """Get detailed information about a file or directory."""
        try:
            # Security check
            is_safe, message = self._is_safe_path(path)
            if not is_safe:
                return f"❌ Access denied: {message}"

            path_obj = Path(path)
            if not path_obj.exists():
                return f"❌ Path not found: {path}"

            stat_info = path_obj.stat()

            output = [f"ℹ️  File Information: {path}", "=" * (len(path) + 20), ""]

            # Basic info
            file_type = "Directory" if path_obj.is_dir() else "File"
            output.extend(
                [
                    f"Type: {file_type}",
                    f"Size: {self._format_file_size(stat_info.st_size)}",
                    f"Permissions: {stat.filemode(stat_info.st_mode)}",
                ]
            )

            # Timestamps
            created = datetime.fromtimestamp(stat_info.st_ctime)
            modified = datetime.fromtimestamp(stat_info.st_mtime)
            accessed = datetime.fromtimestamp(stat_info.st_atime)

            output.extend(
                [
                    "",
                    "Timestamps:",
                    f"  Created:  {created.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"  Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"  Accessed: {accessed.strftime('%Y-%m-%d %H:%M:%S')}",
                ]
            )

            # For files, add more details
            if path_obj.is_file():
                mime_type, encoding = mimetypes.guess_type(str(path_obj))
                output.extend(
                    [
                        "",
                        "File Details:",
                        f"  MIME Type: {mime_type or 'Unknown'}",
                        f"  Extension: {path_obj.suffix or 'None'}",
                    ]
                )

                # Line count for text files
                if path_obj.suffix.lower() in {
                    ".txt",
                    ".py",
                    ".js",
                    ".html",
                    ".css",
                    ".md",
                }:
                    try:
                        with open(path_obj, "r", encoding="utf-8") as f:
                            line_count = sum(1 for _ in f)
                        output.append(f"  Lines: {line_count:,}")
                    except Exception:
                        pass

            # For directories, add content summary
            elif path_obj.is_dir():
                try:
                    items = list(path_obj.iterdir())
                    file_count = sum(1 for item in items if item.is_file())
                    dir_count = sum(1 for item in items if item.is_dir())

                    output.extend(
                        [
                            "",
                            "Directory Contents:",
                            f"  Files: {file_count}",
                            f"  Directories: {dir_count}",
                            f"  Total Items: {len(items)}",
                        ]
                    )
                except PermissionError:
                    output.append("  (Cannot access directory contents)")

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error getting file info: {str(e)}"
