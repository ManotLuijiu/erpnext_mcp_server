import subprocess
import sys
import time

import frappe


@frappe.whitelist()
def test_subprocess():
    """Test if subprocess execution works properly"""
    try:
        # Simple subprocess test
        result = subprocess.run(
            [sys.executable, "-c", 'import sys; print("Subprocess test success!")'],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_realtime():
    """Test if realtime events work properly"""
    try:
        # Get current timestamp
        timestamp = time.time()

        # Send a realtime event
        frappe.publish_realtime(
            "diagnostic_response",
            {
                "success": True,
                "message": "Realtime test success!",
                "timestamp": timestamp,
                "user": frappe.session.user,
            },
            user=frappe.session.user,
        )

        return {"success": True, "message": "Realtime test event sent"}
    except Exception as e:
        return {"success": False, "error": str(e)}
