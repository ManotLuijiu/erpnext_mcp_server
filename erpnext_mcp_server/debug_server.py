# erpnext_mcp_server/debug_server.py (improved version)
import frappe
import sys
import os
from pathlib import Path


def debug_site(site_name):
    """Debug site configuration with more detailed checks"""
    print(f"Debugging site: {site_name}")

    # Check current directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")

    # Check if we're in the frappe-bench directory
    frappe_bench_dir = Path.home() / "frappe-bench"
    if current_dir != str(frappe_bench_dir):
        print(f"WARNING: Not in frappe-bench directory. Changing to {frappe_bench_dir}")
        os.chdir(frappe_bench_dir)
        print(f"New working directory: {os.getcwd()}")

    # Check site directory structure
    site_path = Path("sites") / site_name
    print(f"Site path: {site_path}, Exists: {site_path.exists()}")

    if site_path.exists():
        # Check important files
        site_config = site_path / "site_config.json"
        print(f"site_config.json exists: {site_config.exists()}")
        if site_config.exists():
            print(f"site_config.json size: {site_config.stat().st_size} bytes")

    # Check if sites directory exists
    sites_dir = Path("sites")
    print(f"Sites directory exists: {sites_dir.exists()}")
    if sites_dir.exists():
        print(f"Sites in directory: {list(sites_dir.iterdir())}")

    try:
        # Try to initialize with absolute path
        print("\nTrying frappe.init()...")
        frappe.init(site=site_name)
        print(f"✓ Frappe.init() successful")

        # Try to connect
        print("\nTrying frappe.connect()...")
        frappe.connect()
        print(f"✓ Frappe.connect() successful")

        # Show site info
        print(f"\nSite info:")
        print(f"  Site: {frappe.local.site}")
        print(f"  Database: {frappe.conf.db_name}")

        # Test a simple query
        result = frappe.db.sql("SELECT name FROM tabDocType LIMIT 1")
        print(f"✓ Database query successful: {result}")

        return True

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        try:
            frappe.destroy()
        except:
            pass


if __name__ == "__main__":
    site = sys.argv[1] if len(sys.argv) > 1 else "moo.localhost"
    debug_site(site)
