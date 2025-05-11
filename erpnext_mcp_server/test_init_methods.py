# erpnext_mcp_server/test_init_methods.py
import frappe
import sys
import os


def test_different_init_methods(site_name):
    """Test different ways to initialize Frappe"""

    print(f"Testing different init methods for: {site_name}")

    # Method 1: Standard init
    print("\n1. Standard frappe.init()")
    try:
        frappe.init(site=site_name)
        print("✓ SUCCESS - Standard init")
        frappe.destroy()
    except Exception as e:
        print(f"✗ FAILED - {e}")

    # Method 2: Init with absolute path
    print("\n2. Init with absolute site path")
    try:
        site_path = os.path.abspath(os.path.join("sites", site_name))
        frappe.init(site=site_path)
        print("✓ SUCCESS - Absolute path init")
        frappe.destroy()
    except Exception as e:
        print(f"✗ FAILED - {e}")

    # Method 3: Init with sites_path
    print("\n3. Init with sites_path specified")
    try:
        sites_path = os.path.abspath("sites")
        frappe.init(site=site_name, sites_path=sites_path)
        print("✓ SUCCESS - Sites path init")
        frappe.destroy()
    except Exception as e:
        print(f"✗ FAILED - {e}")

    # Method 4: Set sites_path before init
    print("\n4. Set sites_path globally before init")
    try:
        os.environ["FRAPPE_SITES_PATH"] = os.path.abspath("sites")
        frappe.init(site=site_name)
        print("✓ SUCCESS - Environment variable init")
        frappe.destroy()
    except Exception as e:
        print(f"✗ FAILED - {e}")

    # Method 5: Check if site is in the correct format
    print("\n5. Check various site name formats")
    formats_to_try = [
        site_name,
        f"sites/{site_name}",
        f"./sites/{site_name}",
        os.path.abspath(os.path.join("sites", site_name)),
    ]

    for site_format in formats_to_try:
        print(f"\nTrying format: {site_format}")
        try:
            frappe.init(site=site_format)
            print(f"✓ SUCCESS with format: {site_format}")
            frappe.destroy()
            break
        except Exception as e:
            print(f"✗ FAILED - {e}")


if __name__ == "__main__":
    site = sys.argv[1] if len(sys.argv) > 1 else "moo.localhost"
    test_different_init_methods(site)
