# erpnext_mcp_server/debug_site_path.py
import frappe
import sys
import os
from frappe.utils.response import get_json


def debug_frappe_site_path(site_name):
    """Debug exactly where Frappe is looking for the site"""
    print(f"Debugging site path for: {site_name}")

    # Check the internal workings of get_site_config
    import frappe.utils
    from frappe import _

    # Show what frappe.get_site_path returns
    try:
        site_path = frappe.utils.get_site_path(site_name)
        print(f"frappe.utils.get_site_path returns: {site_path}")
        print(f"Site path exists: {os.path.exists(site_path)}")
    except Exception as e:
        print(f"Error getting site path: {e}")

    # Check the sites_path setting
    try:
        sites_path = frappe.utils.get_sites_path()
        print(f"frappe.utils.get_sites_path returns: {sites_path}")
        print(f"Sites path exists: {os.path.exists(sites_path)}")

        # List all sites in the sites directory
        if os.path.exists(sites_path):
            print(f"\nContents of sites directory:")
            for item in os.listdir(sites_path):
                item_path = os.path.join(sites_path, item)
                print(
                    f"  {item} - {'directory' if os.path.isdir(item_path) else 'file'}"
                )

                # Check if it's a valid site directory
                if os.path.isdir(item_path) and os.path.exists(
                    os.path.join(item_path, "site_config.json")
                ):
                    print(f"    ✓ Valid site directory with site_config.json")

        # Check the specific site
        full_site_path = os.path.join(sites_path, site_name)
        print(f"\nChecking site: {full_site_path}")
        print(f"Site directory exists: {os.path.exists(full_site_path)}")

        site_config = os.path.join(full_site_path, "site_config.json")
        print(f"site_config.json exists: {os.path.exists(site_config)}")

        if os.path.exists(site_config):
            print(f"site_config.json size: {os.path.getsize(site_config)} bytes")

            # Try to read it directly
            try:
                with open(site_config, "r") as f:
                    config_content = f.read()
                    print(f"Config content preview: {config_content[:100]}...")
            except Exception as e:
                print(f"Error reading config file: {e}")

    except Exception as e:
        print(f"Error checking sites path: {e}")

    # Try the init with debug
    print(f"\nAttempting to init site...")
    try:
        frappe.init(site=site_name)
        print("SUCCESS: Site initialized")
    except Exception as e:
        print(f"FAILED: {e}")

        # Let's check what's actually happening in get_site_config
        from frappe import local

        print(f"\nDebugging further:")
        print(f"frappe.local.site: {getattr(local, 'site', 'not set')}")
        print(f"frappe.local.sites_path: {getattr(local, 'sites_path', 'not set')}")


if __name__ == "__main__":
    site = sys.argv[1] if len(sys.argv) > 1 else "moo.localhost"
    debug_frappe_site_path(site)
