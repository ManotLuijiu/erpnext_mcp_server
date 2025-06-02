"""
Document Tools for ERPNext MCP Server
Handles document-related operations like listing, retrieving, and searching
"""

import json
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.model.document import get_doc


class DocumentTools:
    """Tools for ERPNext document operations."""

    def __init__(self, config=None) -> None:
        print(f"config DocumentTools {config}")
        self.safe_doctypes = self._get_safe_doctypes()

    def _get_safe_doctypes(self) -> List[str]:
        """Get list of safe doctypes that can be accessed."""
        # In production, you might want to restrict this further
        return frappe.get_all(
            "DocType", filters={"custom": 0, "istable": 0}, pluck="name"
        )

    async def list_doctypes(self, module_filter: Optional[str] = None) -> str:
        """List all available document types with module information."""
        try:
            filters = {"custom": 0, "istable": 0}
            if module_filter:
                filters["module"] = module_filter  # type: ignore

            doctypes = frappe.get_all(
                "DocType",
                filters=filters,
                fields=[
                    "name",
                    "module",
                    "description",
                    "is_submittable",
                    "track_changes",
                ],
                order_by="module, name",
            )

            if not doctypes:
                return "📋 No document types found."

            # Group by module
            modules = {}

            for doctype in doctypes:
                module = doctype.get("module", "Unknown")
                if module not in modules:
                    modules[module] = []
                modules[module].append(doctype)

            result = ["📋 Available Document Types:", "=" * 50]

            for module_name, module_doctypes in modules.items():
                result.append(f"\n📂 {module_name}")
                result.append("-" * 30)

                for dt in module_doctypes:
                    flags = []
                    if dt.get("is_submittable"):
                        flags.append("📝 Submittable")
                    if dt.get("track_changes"):
                        flags.append("🔍 Tracked")

                    flag_text = f" ({', '.join(flags)})" if flags else ""
                    desc = (
                        f" - {dt.get('description', '')}"
                        if dt.get("description")
                        else ""
                    )

                    result.append(f"  • {dt['name']}{flag_text}{desc}")

            result.append(
                f"\n📊 Total: {len(doctypes)} document types across {len(modules)} modules"
            )
            return "\n".join(result)

        except Exception as e:
            return f"❌ Error listing document types: {str(e)}"

    async def get_document(
        self, doctype: str, name: str, fields: Optional[List[str]] = None
    ) -> str:
        """Get a specific document with formatting."""
        try:
            # Security check
            if doctype not in self.safe_doctypes:
                return f"❌ Access denied: {doctype} is not accessible"

            # Check if document exists
            if not frappe.db.exists(doctype, name):
                return f"❌ Document not found: {doctype} '{name}'"

            # Get document
            doc = get_doc(doctype, name)

            # Check permissions
            if not doc.has_permission("read"):  # type: ignore
                return f"❌ Permission denied: Cannot read {doctype} '{name}'"

            # Format output
            result = [f"📄 {doctype}: {name}", "=" * (len(doctype) + len(name) + 4), ""]

            # Get meta information
            meta = frappe.get_meta(doctype)

            # If specific fields requested, show only those
            if fields:
                for field in fields:
                    if hasattr(doc, field):
                        value = getattr(doc, field)
                        result.append(f"{field}: {value}")
                    else:
                        result.append(f"{field}: (field not found)")
            else:
                # Show all standard fields in organized manner
                sections = {
                    "📋 Basic Information": [
                        "name",
                        "title",
                        "owner",
                        "creation",
                        "modified",
                        "modified_by",
                    ],
                    "📊 Status": ["docstatus", "workflow_state", "enabled", "disabled"],
                    "🏷️  Classification": [
                        "company",
                        "customer",
                        "supplier",
                        "item_group",
                        "territory",
                    ],
                }

                # Add custom sections based on doctype
                if doctype == "Customer":
                    sections["👤 Customer Details"] = [
                        "customer_name",
                        "customer_type",
                        "customer_group",
                        "territory",
                        "mobile_no",
                        "email_id",
                    ]
                elif doctype == "Sales Invoice":
                    sections["💰 Invoice Details"] = [
                        "customer",
                        "posting_date",
                        "due_date",
                        "grand_total",
                        "outstanding_amount",
                        "status",
                    ]
                elif doctype == "Item":
                    sections["📦 Item Details"] = [
                        "item_name",
                        "item_group",
                        "stock_uom",
                        "is_stock_item",
                        "valuation_rate",
                    ]

                for section_name, section_fields in sections.items():
                    section_content = []
                    for field in section_fields:
                        if hasattr(doc, field):
                            value = getattr(doc, field)
                            if value is not None and value != "":
                                label = (
                                    meta.get_label(field)
                                    or field.replace("_", " ").title()
                                )
                                section_content.append(f"  • {label}: {value}")

                    if section_content:
                        result.append(f"\n{section_name}")
                        result.extend(section_content)

                # Add custom fields if any
                custom_fields = []
                for field in meta.fields:
                    if field.fieldname.startswith("custom_") and hasattr(
                        doc, field.fieldname
                    ):
                        value = getattr(doc, field.fieldname)
                        if value is not None and value != "":
                            custom_fields.append(f"  • {field.label}: {value}")

                if custom_fields:
                    result.append("\n🔧 Custom Fields")
                    result.extend(custom_fields)

            return "\n".join(result)

        except Exception as e:
            return f"❌ Error retrieving document: {str(e)}"

    async def search_documents(
        self,
        doctype: str,
        query: Optional[str] = None,
        filters: Dict[str, Any] = None,  # type: ignore
        limit: int = 20,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Search documents with filters."""
        try:
            # Security check
            if doctype not in self.safe_doctypes:
                return f"❌ Access denied: {doctype} is not accessible"

            search_filters = filters or {}

            # Add text search if query provided
            if query:
                meta = frappe.get_meta(doctype)
                title_field = meta.get_title_field()
                if title_field:
                    search_filters[title_field] = ["like", f"%{query}%"]
                else:
                    # Fallback to name field
                    search_filters["name"] = ["like", f"%{query}%"]

            # Default fields to show
            if not fields:
                meta = frappe.get_meta(doctype)
                fields = ["name"]
                if meta.get_title_field():
                    fields.append(meta.get_title_field())
                fields.extend(["creation", "modified", "owner"])

            # Search documents
            documents = frappe.get_all(
                doctype,
                filters=search_filters,
                fields=fields,
                limit=limit,
                order_by="modified desc",
            )

            if not documents:
                search_desc = f" matching '{query}'" if query else ""
                filter_desc = f" with filters {filters}" if filters else ""
                return f"🔍 No {doctype} documents found{search_desc}{filter_desc}"

            # Format results
            result = [f"🔍 Search Results: {doctype}", "=" * (len(doctype) + 18), ""]

            if query:
                result.append(f"📝 Query: {query}")
            if filters:
                result.append(f"🎯 Filters: {json.dumps(filters, indent=2)}")
            result.append(f"📊 Results: {len(documents)} (limit: {limit})")
            result.append("")

            for i, doc in enumerate(documents, 1):
                doc_info = [f"{i:2d}. {doc.get('name')}"]

                for field in fields:
                    if field != "name" and field in doc:
                        value = doc[field]
                        if value:
                            field_label = field.replace("_", " ").title()
                            doc_info.append(f"     {field_label}: {value}")

                result.extend(doc_info)
                result.append("")

            return "\n".join(result)

        except Exception as e:
            return f"❌ Error searching documents: {str(e)}"
