import json
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.realtime import emit_via_redis

# Global session storage
MCP_SESSIONS = {}


class MCPSession:
    """MCP Terminal Session Manager."""

    def __init__(self, session_id: str, user: str):
        self.session_id = session_id
        self.user = user
        self.created_at = time.time()
        self.last_activity = time.time()
        self.is_active = True
        self.command_history = []

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def add_to_history(self, command: str):
        """Add command to history."""
        self.command_history.append({"command": command, "timestamp": time.time()})

        # Keep only last 100 commands
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]


@frappe.whitelist()
def start_mcp_session():
    """Start a new MCP session."""
    try:
        # Check permissions
        if not (
            frappe.has_permission("System Manager")
            or frappe.has_permission("MCP Terminal", "read")
        ):
            frappe.throw(
                _("You don't have permission to use MCP Terminal"),
                frappe.PermissionError,
            )

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Ensure user is not None
        user = frappe.session.user or ""
        if not user:
            frappe.throw(
                _("User is not logged in or session is invalid"), frappe.PermissionError
            )
        # Create session
        session = MCPSession(session_id, user)
        MCP_SESSIONS[session_id] = session

        # Emit session started event
        emit_via_redis(
            event="mcp_session_started",
            message={"session_id": session_id},
            room=frappe.session.user,
        )

        frappe.log(
            f"MCP Terminal session started: session_id={session_id}, user={frappe.session.user}"
        )

        return {
            "success": True,
            "session_id": session_id,
            "message": "MCP session started successfully",
        }

    except Exception as e:
        frappe.log_error(f"Failed to start MCP session: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def end_mcp_session(session_id: str):
    """End an MCP session."""
    try:
        if session_id in MCP_SESSIONS:
            session = MCP_SESSIONS[session_id]
            session.is_active = False
            del MCP_SESSIONS[session_id]

            # Emit session ended event
            emit_via_redis(
                event="mcp_session_ended",
                message={"session_id": session_id},
                room=frappe.session.user,
            )

            frappe.log(
                f"MCP Terminal session ended, session_id={session_id}, user={frappe.session.user}"
            )

        return {"success": True, "message": "Session ended successfully"}

    except Exception as e:
        frappe.log_error(f"Failed to end MCP session: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def execute_mcp_command(session_id: str, command: str, args: Dict[str, Any] = {}):
    """Execute an MCP command."""
    try:
        # Validate session
        if session_id not in MCP_SESSIONS:
            return {"success": False, "error": "Invalid or expired session"}

        session = MCP_SESSIONS[session_id]
        session.update_activity()
        session.add_to_history(command)

        # Execute command in background
        threading.Thread(
            target=_execute_command_async,
            args=(session_id, command, args or {}),
            daemon=True,
        ).start()

        return {"success": True, "message": "Command queued for execution"}

    except Exception as e:
        frappe.log_error(f"Failed to execute MCP command: {str(e)}")
        return {"success": False, "error": str(e)}


def _execute_command_async(session_id: str, command: str, args: Dict[str, Any]):
    """Execute command asynchronously and emit result."""
    try:
        session = MCP_SESSIONS.get(session_id)
        if not session:
            return

        # Execute the command based on type
        result = None

        if command == "list_doctypes":
            result = _list_doctypes()
        elif command == "get_document":
            result = _get_document(
                str(args.get("doctype") or ""), str(args.get("name") or "")
            )
        elif command == "search_documents":
            result = _search_documents(
                str(args.get("doctype") or ""), str(args.get("query") or "")
            )
        elif command == "create_document":
            result = _create_document(
                str(args.get("doctype") or ""), args.get("data") or {}
            )
        elif command == "update_document":
            result = _update_document(
                str(args.get("doctype") or ""),
                str(args.get("name") or ""),
                args.get("data") or {},
            )
        elif command == "execute_sql":
            result = _execute_sql(str(args.get("query") or ""))
        elif command == "get_system_info":
            result = _get_system_info()
        elif command == "bench_command":
            result = _execute_bench_command(str(args.get("command") or ""))
        else:
            result = {"success": False, "error": f"Unknown command: {command}"}

        # Emit result
        emit_via_redis(
            event="mcp_command_result",
            message={
                "session_id": session_id,
                "command": command,
                "success": result.get("success", False),
                "data": result.get("data"),
                "error": result.get("error"),
            },
            room=session.user,
        )

    except Exception as e:
        frappe.log_error(f"Error in async command execution: {str(e)}")
        # Emit error result
        emit_via_redis(
            event="mcp_command_result",
            message={
                "session_id": session_id,
                "command": command,
                "success": False,
                "error": str(e),
            },
            room=session.user if session else frappe.session.user,
        )


def _list_doctypes():
    """List all available DocTypes."""
    try:
        doctypes = frappe.get_all(
            "DocType",
            fields=["name", "module", "custom", "is_submittable", "track_changes"],
            filters={"issingle": 0},
            order_by="name",
        )

        return {
            "success": True,
            "data": json.dumps(doctypes, indent=2),
            "count": len(doctypes),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_document(doctype: str, name: str):
    """Get a specific document."""
    try:
        if not doctype or not name:
            return {"success": False, "error": "DocType and name are required"}

        doc = frappe.get_doc(doctype, name)
        doc_dict = doc.as_dict()

        return {"success": True, "data": json.dumps(doc_dict, indent=2, default=str)}
    except frappe.DoesNotExistError:
        return {"success": False, "error": f"Document {doctype}:{name} does not exist"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _search_documents(doctype: str, query: str, limit: int = 20):
    """Search documents in a DocType."""
    try:
        if not doctype or not query:
            return {"success": False, "error": "DocType and query are required"}

        # Get meta to understand the DocType structure
        meta = frappe.get_meta(doctype)
        search_fields = []

        # Find text fields to search in
        for field in meta.fields:
            if field.fieldtype in ["Data", "Text", "Small Text", "Long Text", "Link"]:
                search_fields.append(field.fieldname)

        # Add name field
        if "name" not in search_fields:
            search_fields.append("name")

        # Build search filters
        filters = []
        for field in search_fields[:5]:  # Limit to first 5 fields
            filters.append([doctype, field, "like", f"%{query}%"])

        # Search documents
        documents = frappe.get_all(
            doctype,
            fields=["name", "creation", "modified"],
            or_filters=filters,
            limit=limit,
            order_by="modified desc",
        )

        return {
            "success": True,
            "data": json.dumps(documents, indent=2, default=str),
            "count": len(documents),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _create_document(doctype: str, data: Dict[str, Any]):
    """Create a new document."""
    try:
        if not doctype or not data:
            return {"success": False, "error": "DocType and data are required"}

        doc = frappe.get_doc({"doctype": doctype, **data})
        doc.insert()
        frappe.db.commit()

        return {
            "success": True,
            "data": json.dumps(doc.as_dict(), indent=2, default=str),
            "message": f"Document {doc.name} created successfully",
        }
    except Exception as e:
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def _update_document(doctype: str, name: str, data: Dict[str, Any]):
    """Update an existing document."""
    try:
        if not doctype or not name or not data:
            return {"success": False, "error": "DocType, name, and data are required"}

        doc = frappe.get_doc(doctype, name)
        for key, value in data.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        doc.save()
        frappe.db.commit()

        return {
            "success": True,
            "data": json.dumps(doc.as_dict(), indent=2, default=str),
            "message": f"Document {doc.name} updated successfully",
        }
    except Exception as e:
        frappe.db.rollback()
        return {"success": False, "error": str(e)}


def _execute_sql(query: str):
    """Execute a SQL query (SELECT only)."""
    try:
        if not query:
            return {"success": False, "error": "SQL query is required"}

        # Security check - only allow SELECT queries
        query_lower = query.lower().strip()
        if not query_lower.startswith("select"):
            return {"success": False, "error": "Only SELECT queries are allowed"}

        # Execute query
        result = frappe.db.sql(query, as_dict=True)
        result_list = list(result)

        return {
            "success": True,
            "data": json.dumps(result_list, indent=2, default=str),
            "count": len(result_list),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_system_info():
    """Get system information."""
    try:
        info = {
            "frappe_version": frappe.__version__,
            "site": frappe.local.site,
            "user": frappe.session.user,
            "db_name": frappe.conf.db_name,
            "redis_cache": frappe.conf.redis_cache,
            "redis_queue": frappe.conf.redis_queue,
            "installed_apps": frappe.get_installed_apps(),
            "active_sessions": len(MCP_SESSIONS),
        }

        return {"success": True, "data": json.dumps(info, indent=2, default=str)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _execute_bench_command(command: str):
    """Execute a bench command (limited set)."""
    try:
        if not command:
            return {"success": False, "error": "Bench command is required"}

        # Allowed bench commands for security
        allowed_commands = ["status", "version", "list-apps", "--help"]

        cmd_parts = command.split()
        if not cmd_parts or cmd_parts[0] not in allowed_commands:
            return {
                "success": False,
                "error": f"Command '{cmd_parts[0] if cmd_parts else command}' not allowed. Allowed: {', '.join(allowed_commands)}",
            }

        # Execute bench command
        result = subprocess.run(
            ["bench"] + cmd_parts,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=frappe.get_app_path("frappe", ".."),
        )

        return {
            "success": True,
            "data": result.stdout + result.stderr,
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_active_sessions():
    """Get list of active MCP sessions."""
    try:
        # Check if user is System Manager
        if not frappe.has_permission("System Manager"):
            frappe.throw(
                _("You don't have permission to view active sessions"),
                frappe.PermissionError,
            )

        sessions = []
        current_time = time.time()

        for session_id, session in MCP_SESSIONS.items():
            # Remove inactive sessions (older than 1 hour)
            if current_time - session.last_activity > 3600:
                session.is_active = False
                continue

            if session.is_active:
                sessions.append(
                    {
                        "session_id": session_id,
                        "user": session.user,
                        "created_at": session.created_at,
                        "last_activity": session.last_activity,
                        "command_count": len(session.command_history),
                    }
                )

        # Clean up inactive sessions
        inactive_sessions = [
            sid for sid, session in MCP_SESSIONS.items() if not session.is_active
        ]
        for sid in inactive_sessions:
            del MCP_SESSIONS[sid]

        return {"success": True, "sessions": sessions, "total_active": len(sessions)}

    except Exception as e:
        frappe.log_error(f"Failed to get active sessions: {str(e)}")
        return {"success": False, "error": str(e)}
