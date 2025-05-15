import json
import logging
from datetime import datetime

import frappe
import requests
from bs4 import BeautifulSoup


def update_tax_laws():
    """Daily update of Thai tax laws from official sources"""
    try:
        # Set up logging
        logger = frappe.logger("tax_law_updates", allow_site=True, file_count=50)
        logger.info(f"Starting scheduled tax law update: {datetime.now()}")

        # Define URLs to check for updates
        urls = {
            "personal_income_tax": "https://www.rd.go.th/thai/taxlaw/revenuecode/revenue_1.html",
            "corporate_income_tax": "https://www.rd.go.th/thai/taxlaw/revenuecode/revenue_2.html",
            "vat": "https://www.rd.go.th/thai/taxlaw/revenuecode/revenue_4.html",
            # Add more URLs as needed
        }

        # Track updates
        updates_made = 0
        errors = 0

        for category, url in urls.items():
            try:
                # Fetch the page
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.content, "html.parser")

                # Find relevant content - this will vary based on the site structure
                # For this example, let's assume relevant content is in specific div classes
                content_sections = soup.find_all("div", class_="law-content")

                # Process each section
                for section in content_sections:
                    # Extract section code or identifier
                    section_code = extract_section_code(section)
                    if not section_code:
                        continue

                    # Check if we already have this section
                    existing = frappe.db.exists(
                        "Thai Tax Law", {"section_code": section_code}
                    )

                    # Extract content details
                    title = extract_title(section)
                    content_th = extract_content(section)
                    last_modified = extract_last_modified(section)
                    legal_reference = extract_legal_reference(section)

                    if not existing:
                        # Create new record
                        doc = frappe.new_doc("Thai Tax Law")
                        doc.section_code = section_code
                        doc.title = title
                        doc.category = map_category(category)
                        doc.content_th = content_th
                        doc.legal_reference = legal_reference
                        doc.effective_date = last_modified or datetime.now().date()
                        doc.is_active = 1
                        doc.source_url = url
                        doc.insert()
                        updates_made += 1
                        logger.info(f"Created new tax law section: {section_code}")
                    else:
                        # Update existing record if changed
                        doc = frappe.get_doc("Thai Tax Law", existing)
                        if (
                            doc.content_th != content_th
                            or doc.title != title
                            or doc.legal_reference != legal_reference
                        ):
                            doc.title = title
                            doc.content_th = content_th
                            doc.legal_reference = legal_reference
                            doc.source_url = url
                            doc.save()
                            updates_made += 1
                            logger.info(f"Updated tax law section: {section_code}")

            except Exception as e:
                errors += 1
                logger.error(f"Error processing {category} from {url}: {str(e)}")

        # Commit database changes
        frappe.db.commit()

        # Log summary
        logger.info(
            f"Tax law update complete. Updates: {updates_made}, Errors: {errors}"
        )

        # Create a system notification for admins if significant updates were made
        if updates_made > 0:
            frappe.publish_realtime(
                event="eval_js",
                message=f"frappe.show_alert({{message: '{updates_made} tax laws updated', indicator: 'green'}});",
                user="Administrator",
            )

    except Exception as e:
        frappe.log_error(f"Tax law update failed: {str(e)}", "Tax Law Update Error")


# Helper functions for extraction
def extract_section_code(element):
    """Extract section code from HTML element"""
    # Implementation depends on page structure
    return "PIT-" + element.get("id", "unknown")


def extract_title(element):
    """Extract title from HTML element"""
    title_elem = element.find("h3") or element.find("h2")
    return title_elem.text.strip() if title_elem else "Untitled Section"


def extract_content(element):
    """Extract content from HTML element"""
    return element.get_text() if element else ""


def extract_last_modified(element):
    """Extract last modified date from HTML element"""
    # Implementation depends on page structure
    date_elem = element.find("span", class_="date")
    if date_elem and date_elem.text:
        try:
            return datetime.strptime(date_elem.text.strip(), "%d/%m/%Y").date()
        except:
            return None
    return None


def extract_legal_reference(element):
    """Extract legal reference from HTML element"""
    # Implementation depends on page structure
    ref_elem = element.find("span", class_="reference")
    return ref_elem.text.strip() if ref_elem else ""


def map_category(category_key):
    """Map category key to actual category name"""
    mapping = {
        "personal_income_tax": "Personal Income Tax",
        "corporate_income_tax": "Corporate Income Tax",
        "vat": "Value Added Tax",
    }
    return mapping.get(category_key, "General")
