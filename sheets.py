import os
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS

# Google Sheets connection scope
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ─────────────────────────────────────────
# CONNECT TO GOOGLE SHEET
# ─────────────────────────────────────────

def get_sheet():
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        return sheet
    except Exception as e:
        log_action("Sheet Connection", f"Error: {str(e)}", "Error")
        return None

# ─────────────────────────────────────────
# PRODUCTS TAB
# ─────────────────────────────────────────

def get_all_products():
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Products")
        return tab.get_all_records()
    except Exception as e:
        log_action("Get Products", f"Error: {str(e)}", "Error")
        return []

def add_product(product_data):
    # product_data = dict with all columns
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Products")
        row = [
            product_data.get("product_id", ""),
            product_data.get("name", ""),
            product_data.get("category", ""),
            product_data.get("type", ""),
            product_data.get("score", ""),
            product_data.get("cj_video_url", ""),
            product_data.get("price_eur", ""),
            product_data.get("supplier", ""),
            product_data.get("signal_1", ""),
            product_data.get("signal_2", ""),
            product_data.get("signal_3", ""),
            product_data.get("signal_4", ""),
            product_data.get("signal_5", ""),
            product_data.get("days_in_pool", 0),
            product_data.get("status", "Active"),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            product_data.get("source", "")
        ]
        tab.append_row(row)
        log_action("Add Product", f"Added: {product_data.get('name')}", "Success")
        return True
    except Exception as e:
        log_action("Add Product", f"Error: {str(e)}", "Error")
        return False

def update_product_status(product_id, status):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Products")
        records = tab.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row["product_id"]) == str(product_id):
                # Status column is 15th column
                tab.update_cell(i, 15, status)
                log_action("Update Product", f"ID: {product_id} Status: {status}", "Success")
                return True
        return False
    except Exception as e:
        log_action("Update Product", f"Error: {str(e)}", "Error")
        return False

def delete_product(product_id):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Products")
        records = tab.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row["product_id"]) == str(product_id):
                tab.delete_rows(i)
                log_action("Delete Product", f"ID: {product_id}", "Success")
                return True
        return False
    except Exception as e:
        log_action("Delete Product", f"Error: {str(e)}", "Error")
        return False

def get_early_pool_count():
    try:
        products = get_all_products()
        active = [p for p in products if p["status"] == "Active"]
        viral = [p for p in active if p["type"] == "Viral"]
        medium = [p for p in active if p["type"] == "Medium"]
        evergreen = [p for p in active if p["type"] == "Evergreen"]
        return {
            "total": len(active),
            "viral": len(viral),
            "medium": len(medium),
            "evergreen": len(evergreen)
        }
    except Exception as e:
        log_action("Pool Count", f"Error: {str(e)}", "Error")
        return {"total": 0, "viral": 0, "medium": 0, "evergreen": 0}

# ─────────────────────────────────────────
# TEST SECTION TAB
# ─────────────────────────────────────────

def add_to_test_section(product_data):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Test Section")
        row = [
            product_data.get("product_id", ""),
            product_data.get("name", ""),
            product_data.get("category", ""),
            product_data.get("type", ""),
            product_data.get("score", ""),
            product_data.get("cj_video_url", ""),
            product_data.get("price_eur", ""),
            product_data.get("supplier", ""),
            product_data.get("signal_1", ""),
            product_data.get("signal_2", ""),
            product_data.get("signal_3", ""),
            product_data.get("signal_4", ""),
            product_data.get("signal_5", ""),
            product_data.get("days_in_pool", 0),
            product_data.get("status", "Testing"),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            product_data.get("source", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M"),  # Test Start Date
            "",  # Test End Date
            ""   # Performance
        ]
        tab.append_row(row)
        log_action("Test Section", f"Added: {product_data.get('name')}", "Success")
        return True
    except Exception as e:
        log_action("Test Section", f"Error: {str(e)}", "Error")
        return False

# ─────────────────────────────────────────
# SCHEDULE TAB
# ─────────────────────────────────────────

def add_to_schedule(product_id, video_file_id, product_name, platform, scheduled_time):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Schedule")
        row = [
            product_id,
            video_file_id,
            product_name,
            platform,
            scheduled_time,
            "Pending",
            ""  # Posted At — empty for now
        ]
        tab.append_row(row)
        log_action("Schedule", f"Added: {product_name} — {platform} — {scheduled_time}", "Success")
        return True
    except Exception as e:
        log_action("Schedule", f"Error: {str(e)}", "Error")
        return False

def get_pending_posts():
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Schedule")
        records = tab.get_all_records()
        return [r for r in records if r["status"] == "Pending"]
    except Exception as e:
        log_action("Get Pending Posts", f"Error: {str(e)}", "Error")
        return []

def mark_post_done(product_id, platform):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Schedule")
        records = tab.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row["product_id"]) == str(product_id) and row["platform"] == platform:
                tab.update_cell(i, 6, "Posted")
                tab.update_cell(i, 7, datetime.now().strftime("%Y-%m-%d %H:%M"))
                return True
        return False
    except Exception as e:
        log_action("Mark Post Done", f"Error: {str(e)}", "Error")
        return False

def check_already_posted(product_id, platform):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Schedule")
        records = tab.get_all_records()
        for row in records:
            if str(row["product_id"]) == str(product_id) and row["platform"] == platform and row["status"] == "Posted":
                return True
        return False
    except Exception as e:
        log_action("Check Posted", f"Error: {str(e)}", "Error")
        return False

# ─────────────────────────────────────────
# API TRACKER TAB
# ─────────────────────────────────────────

def update_api_usage(api_name, calls_used):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("API Tracker")
        records = tab.get_all_records()
        for i, row in enumerate(records, start=2):
            if row["api_name"] == api_name:
                tab.update_cell(i, 3, calls_used)
                return True
        return False
    except Exception as e:
        log_action("API Tracker", f"Error: {str(e)}", "Error")
        return False

def get_api_usage(api_name):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("API Tracker")
        records = tab.get_all_records()
        for row in records:
            if row["api_name"] == api_name:
                return row
        return None
    except Exception as e:
        log_action("Get API Usage", f"Error: {str(e)}", "Error")
        return None

# ─────────────────────────────────────────
# AUTOMATION FLAG TAB
# ─────────────────────────────────────────

def get_automation_flag(flag_name):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Automation Flag")
        records = tab.get_all_records()
        for row in records:
            if row["flag_name"] == flag_name:
                return row
        return None
    except Exception as e:
        log_action("Get Flag", f"Error: {str(e)}", "Error")
        return None

def set_automation_flag(flag_name, status, stop_until=""):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Automation Flag")
        records = tab.get_all_records()
        for i, row in enumerate(records, start=2):
            if row["flag_name"] == flag_name:
                tab.update_cell(i, 2, status)
                tab.update_cell(i, 3, datetime.now().strftime("%Y-%m-%d %H:%M"))
                tab.update_cell(i, 4, stop_until)
                return True
        # Agar flag nahi mila toh naya add karo
        tab.append_row([flag_name, status, datetime.now().strftime("%Y-%m-%d %H:%M"), stop_until])
        return True
    except Exception as e:
        log_action("Set Flag", f"Error: {str(e)}", "Error")
        return False

# ─────────────────────────────────────────
# LOGS TAB
# ─────────────────────────────────────────

def log_action(action, details, status):
    try:
        sheet = get_sheet()
        tab = sheet.worksheet("Logs")
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action,
            details,
            status
        ]
        tab.append_row(row)
    except Exception as e:
        # Agar log bhi fail ho toh console pe print
        print(f"[LOG ERROR] {datetime.now()} | {action} | {details} | {status} | Log Error: {str(e)}")
